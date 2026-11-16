import threading
import time
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models.synthetic import TestRun, CleanupJob
from backend.app.models.document import Document
from backend.app.services.synthetic_runner import synthetic_runner
from backend.app.services.vector_store import vector_store_service

logger = logging.getLogger("forgetcheck.worker")

class BackgroundWorker:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._reconcile_interrupted_jobs()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="ForgetCheckWorker")
        self._thread.start()
        logger.info("Background experiment worker started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
            logger.info("Background experiment worker stopped.")

    def _reconcile_interrupted_jobs(self):
        """Reconciles interrupted jobs and incomplete indexing states on restart."""
        db = SessionLocal()
        try:
            # Reconcile interrupted test runs
            interrupted_runs = db.query(TestRun).filter(TestRun.status == "running").all()
            for r in interrupted_runs:
                r.status = "interrupted"
                r.error_message = "Job interrupted by server restart or shutdown."
                r.completed_at = datetime.utcnow()

            # Reconcile stuck document indexing
            stuck_docs = db.query(Document).filter(Document.indexing_status == "indexing").all()
            for d in stuck_docs:
                d.indexing_status = "failed"
                d.error_message = "Indexing interrupted by server restart."

            db.commit()
        except Exception as e:
            logger.error(f"Error reconciling interrupted jobs: {e}")
        finally:
            db.close()

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                self._process_next_job()
                self._process_cleanup_jobs()
            except Exception as e:
                logger.error(f"Worker iteration error: {e}")
            time.sleep(1.0)

    def _process_next_job(self):
        db = SessionLocal()
        try:
            # Transactionally claim next queued run
            next_run = db.query(TestRun).filter(TestRun.status == "queued").order_by(TestRun.created_at.asc()).first()
            if next_run:
                run_id = next_run.id
                db.close() # Close session before runner opens its own
                
                # Execute run in fresh session
                runner_db = SessionLocal()
                try:
                    synthetic_runner.run_suite(runner_db, run_id)
                finally:
                    runner_db.close()
        except Exception as e:
            logger.error(f"Error processing job: {e}")
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _process_cleanup_jobs(self):
        db = SessionLocal()
        try:
            pending_jobs = db.query(CleanupJob).filter(
                CleanupJob.status.in_(["pending", "failed"]),
                CleanupJob.retry_count < 3
            ).all()

            for job in pending_jobs:
                job.status = "running"
                job.retry_count += 1
                try:
                    if job.target_store == "chroma":
                        vector_store_service.delete_document_chunks("production_documents", job.document_id)
                    job.status = "completed"
                    job.error_message = None
                except Exception as e:
                    job.status = "failed"
                    job.error_message = str(e)
                job.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Error in cleanup job processor: {e}")
        finally:
            db.close()

worker = BackgroundWorker()
