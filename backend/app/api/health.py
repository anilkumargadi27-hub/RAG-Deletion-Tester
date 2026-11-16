from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database import get_db
from backend.app.config import settings

router = APIRouter(tags=["Health & Readiness"])

@router.get("/health")
@router.get("/api/health")
def health_check():
    """Lightweight liveness check for Render and monitoring."""
    return {"status": "ok", "service": "forgetcheck-api"}

@router.get("/ready")
@router.get("/api/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Verifies database connectivity and storage readiness."""
    try:
        # Check SQLite connectivity
        db.execute(text("SELECT 1"))
        # Check data directory exists
        db_ready = settings.database_path.exists()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "database_ready": db_ready,
                "environment": settings.ENVIRONMENT
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": str(e)
            }
        )
