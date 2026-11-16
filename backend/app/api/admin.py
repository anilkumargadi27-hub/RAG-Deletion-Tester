import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.synthetic import TestRun, CleanupJob, SyntheticFixture, ProbeResult
from backend.app.core.security import require_roles
from backend.app.services.vector_store import vector_store_service
from backend.app.services.generator_service import generator_service

router = APIRouter(prefix="/api/admin", tags=["Admin & Diagnostics"])

@router.get("/diagnostics")
def get_admin_diagnostics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    total_docs = db.query(Document).count()
    tombstoned_docs = db.query(Document).filter(Document.is_tombstoned == True).count()
    total_chunks = db.query(DocumentChunk).count()
    total_runs = db.query(TestRun).count()
    pending_cleanups = db.query(CleanupJob).filter(CleanupJob.status.in_(["pending", "failed"])).count()

    # Chroma collection info
    try:
        col = vector_store_service.get_or_create_collection("production_documents")
        chroma_count = col.count()
    except Exception:
        chroma_count = 0

    return {
        "environment": settings.ENVIRONMENT,
        "database": {
            "path": str(settings.database_path),
            "total_documents": total_docs,
            "tombstoned_documents": tombstoned_docs,
            "total_chunks": total_chunks,
            "total_runs": total_runs,
            "pending_cleanup_jobs": pending_cleanups
        },
        "vector_store": {
            "type": "Chroma Persistent",
            "directory": str(settings.chroma_dir),
            "production_chunks_count": chroma_count
        },
        "embedding_service": {
            "active_mode": vector_store_service.embedding_service.mode,
            "model_cache_dir": str(settings.model_cache_dir)
        },
        "ai_provider": {
            "gemini_configured": bool(settings.GEMINI_API_KEY),
            "gemini_model": settings.GEMINI_MODEL,
            "active_default_mode": "local_extractive"
        },
        "worker": {
            "status": "active_managed_thread"
        }
    }

@router.post("/test-gemini")
def test_gemini(
    current_user: User = Depends(require_roles(["admin"]))
):
    return generator_service.test_gemini_connection()

@router.post("/reset-synthetic")
def reset_synthetic_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """Scoped reset for synthetic laboratory runs and transient data only."""
    db.query(ProbeResult).delete()
    db.query(TestRun).delete()
    db.commit()
    return {"message": "Synthetic test runs and probe evidence reset successfully."}
