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
from backend.app.core.security import hash_password, verify_csrf
from backend.app.services.worker import worker
from backend.app.services.synthetic_runner import synthetic_runner

from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.documents import router as documents_router
from backend.app.api.chat import router as chat_router
from backend.app.api.synthetic import router as synthetic_router
from backend.app.api.reports import router as reports_router
from backend.app.api.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize tables and seed initial admin
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed initial admin if not existing
        admin = db.query(User).filter(User.username == settings.INITIAL_ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=settings.INITIAL_ADMIN_USERNAME,
                email="admin@forgetcheck.local",
                hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                role="admin",
                is_active=True
            )
            db.add(admin)
            db.commit()

        # Seed synthetic fixtures
        synthetic_runner.ensure_fixtures_seeded(db)
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
    ],
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
