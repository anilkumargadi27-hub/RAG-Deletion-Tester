import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.config import settings, BASE_DIR
from backend.app.database import engine, SessionLocal, Base
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.synthetic import TestRun
from backend.app.core.security import hash_password, verify_csrf
from backend.app.services.worker import worker
from backend.app.services.synthetic_runner import synthetic_runner
from backend.app.services.document_service import document_service

from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.documents import router as documents_router
from backend.app.api.chat import router as chat_router
from backend.app.api.synthetic import router as synthetic_router
from backend.app.api.reports import router as reports_router
from backend.app.api.admin import router as admin_router

def ensure_startup_data(db):
    # 1. Seed or synchronize all 3 demo accounts
    accounts = [
        ("admin", "admin@forgetcheck.local", settings.INITIAL_ADMIN_PASSWORD, "admin"),
        ("auditor", "auditor@forgetcheck.local", "Auditor@ForgetCheck2026!", "auditor"),
        ("member", "member@forgetcheck.local", "Member@ForgetCheck2026!", "member")
    ]
    for uname, email, pwd, role in accounts:
        u = db.query(User).filter(User.username == uname).first()
        if not u:
            u = User(
                username=uname,
                email=email,
                hashed_password=hash_password(pwd),
                role=role,
                is_active=True
            )
            db.add(u)
        else:
            u.hashed_password = hash_password(pwd)
            u.is_active = True
    db.commit()

    # 2. Seed synthetic scenario fixtures
    synthetic_runner.ensure_fixtures_seeded(db)

    # 3. Seed demo documents if empty
    if db.query(Document).count() == 0:
        admin_user = db.query(User).filter(User.username == "admin").first()
        admin_id = admin_user.id if admin_user else None
        sample_docs = [
            (
                "Employee Handbook & Wellness Benefits 2026",
                "HR",
                (
                    "All full-time employees are provided CarePlus Platinum health insurance coverage. "
                    "Annual wellness stipends of $600 are available for fitness memberships and mental health apps. "
                    "Flexible working hours operate between 8:00 AM and 7:00 PM local time. "
                    "Parental leave provides 16 weeks of fully paid leave for all eligible caregivers."
                ),
                ["general_employee", "hr_manager", "admin"]
            ),
            (
                "Corporate Travel and Expense Reimbursement Guidelines",
                "Finance",
                (
                    "Business travel expenses must be pre-approved by your department manager. "
                    "Domestic daily meal per diem is capped at $85 per day. "
                    "Expense reports must be filed within 30 days of trip conclusion via the finance portal. "
                    "First-class air travel is strictly restricted to flights exceeding 8 continuous hours."
                ),
                ["general_employee", "finance_team", "admin"]
            ),
            (
                "Engineering Architecture & API Security Standards",
                "Engineering",
                (
                    "All production services must authenticate using mTLS with short-lived certificates. "
                    "Database access must use connection pooling with TLS 1.3 encryption in transit. "
                    "API rate limiting defaults to 100 requests per minute per IP for unauthenticated traffic "
                    "and 1,000 requests per minute for authenticated API tokens."
                ),
                ["engineering_lead", "devops_team", "admin"]
            )
        ]
        for title, dept, text, principals in sample_docs:
            try:
                document_service.ingest_document(
                    db=db,
                    title=title,
                    department=dept,
                    raw_text=text,
                    permitted_principals=principals,
                    uploader_id=admin_id
                )
            except Exception:
                pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize tables and seed all default accounts & fixtures
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_startup_data(db)
    finally:
        db.close()

    # Start background experiment queue worker
    worker.start()

    yield

    # Shutdown
    worker.stop()

app = FastAPI(
    title="ForgetCheck API",
    description="RAG Deletion & Access-Revocation Tester — Check what your AI can still reveal after access changes.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://forgetcheck.onrender.com",
    ],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State-changing CSRF verification middleware
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    # Verify CSRF on state changes unless exempt (auth login, health checks)
    try:
        if request.url.path.startswith("/api/"):
            verify_csrf(request)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    return await call_next(request)

# Include API Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(synthetic_router)
app.include_router(reports_router)
app.include_router(admin_router)

# Mount Frontend static files for production / single-service deployment
frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react_app(full_path: str):
        # Allow API routes to be handled by routers; serve index.html for client-side deep links
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        target_file = frontend_dist / full_path
        if full_path and target_file.exists() and target_file.is_file():
            return FileResponse(str(target_file))
        return FileResponse(str(frontend_dist / "index.html"))
