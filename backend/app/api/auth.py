from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User, UserSession
from backend.app.schemas.auth import LoginRequest, UserResponse, SessionResponse, CreateUserRequest
from backend.app.core.security import (
    verify_password, hash_password, create_user_session,
    generate_csrf_token, get_current_user, require_roles,
    check_login_rate_limit, record_login_attempt, clear_login_attempts
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=SessionResponse)
def login(login_req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "127.0.0.1"

    if not check_login_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 5 minutes before retrying."
        )

    user = db.query(User).filter(User.username == login_req.username.strip()).first()
    if not user or not verify_password(login_req.password, user.hashed_password):
        record_login_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive."
        )

    clear_login_attempts(client_ip)
    user_agent = request.headers.get("User-Agent", "Unknown")
    session = create_user_session(db, user, client_ip=client_ip, user_agent=user_agent)
    csrf_token = generate_csrf_token()

    # Set HttpOnly Session Cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session.session_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.SECURE_COOKIES,
        path="/"
    )

    # Set CSRF Token Cookie (readable by JS to include in header)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=False,
        samesite="lax",
        secure=settings.SECURE_COOKIES,
        path="/"
    )

    return SessionResponse(
        user=UserResponse.model_validate(user),
        csrf_token=csrf_token,
        token=session.session_token # For programmatic/API test convenience
    )

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        sess = db.query(UserSession).filter(UserSession.session_token == token).first()
        if sess:
            sess.revoked_at = db.query(UserSession).filter(UserSession.session_token == token).first().expires_at
            db.commit()

    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_roles(["admin"]))):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserResponse.model_validate(u) for u in users]

@router.post("/users", response_model=UserResponse)
def create_user(
    create_req: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    existing = db.query(User).filter(
        (User.username == create_req.username) | (User.email == create_req.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists.")

    new_user = User(
        username=create_req.username.strip(),
        email=create_req.email.strip().lower(),
        hashed_password=hash_password(create_req.password),
        role=create_req.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)
