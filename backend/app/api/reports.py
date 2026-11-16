from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.core.security import get_current_user, require_roles
from backend.app.services.pdf_exporter import report_exporter

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/{run_id}/json")
def download_json_report(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    try:
        data = report_exporter.export_json(db, run_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{run_id}/csv")
def download_csv_report(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    try:
        csv_content = report_exporter.export_csv(db, run_id)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=forgetcheck_report_{run_id[:8]}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{run_id}/pdf")
def download_pdf_report(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    try:
        pdf_bytes = report_exporter.export_pdf(db, run_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=forgetcheck_report_{run_id[:8]}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
