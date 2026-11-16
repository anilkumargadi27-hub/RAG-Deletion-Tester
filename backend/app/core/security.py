import secrets
from datetime import datetime, timedelta
from typing import List, Optional
import bcrypt
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User, UserSession

# Rate limiting storage (in-memory per process for login attempts)
_login_attempts = {}

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def generate_session_token() -> str:
    return secrets.token_urlsafe(48)

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def check_login_rate_limit(client_ip: str) -> bool:
    now = datetime.utcnow()
    # Clean old attempts
    cutoff = now - timedelta(minutes=5)
    attempts = [t for t in _login_attempts.get(client_ip, []) if t > cutoff]
    _login_attempts[client_ip] = attempts
    if len(attempts) >= 10:
        return False
    return True

def record_login_attempt(client_ip: str):
    now = datetime.utcnow()
    _login_attempts.setdefault(client_ip, []).append(now)

def clear_login_attempts(client_ip: str):
    if client_ip in _login_attempts:
        del _login_attempts[client_ip]

def create_user_session(db: Session, user: User, client_ip: Optional[str] = None, user_agent: Optional[str] = None) -> UserSession:
    token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)
    session = UserSession(
        session_token=token,
        user_id=user.id,
        client_ip=client_ip,
        user_agent=user_agent,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        # Check Authorization Bearer header as fallback for tests or CLI
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            
    if not token:
        return None

    session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > datetime.utcnow()
    ).first()

    if not session:
        return None

    user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
    return user

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required or session expired"
        )
    return user

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

def verify_csrf(request: Request):
    """CSRF check for state-changing requests (POST, PUT, DELETE, PATCH)."""
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        # Exclude login and logout from strict CSRF requirement if session not yet established
        if request.url.path.endswith("/api/auth/login"):
            return
        csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
        csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
        
        # If request came with Bearer token (CLI / tests), CSRF is not required
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return

        if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed"
            )
