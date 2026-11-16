import pytest
from backend.app.models.synthetic import TestRun
from backend.app.services.synthetic_runner import synthetic_runner
from backend.app.services.pdf_exporter import report_exporter

def test_json_and_csv_and_pdf_reports(db, admin_user):
    run = TestRun(
        name="Report Export Test",
        user_id=admin_user.id,
        status="queued",
        fault_mode="secure_baseline",
        answer_mode="local_extractive",
        is_guided_demo=True
    )
    db.add(run)
    db.commit()
    synthetic_runner.run_suite(db, run.id)

    # 1. JSON Report
    json_data = report_exporter.export_json(db, run.id)
    assert json_data["run_metadata"]["run_id"] == run.id
    assert "honesty_boundary" in json_data
    assert len(json_data["probes"]) > 0

    # 2. CSV Report
    csv_data = report_exporter.export_csv(db, run.id)
    assert "Probe Index,Scenario Key" in csv_data

    # 3. PDF Report
    pdf_bytes = report_exporter.export_pdf(db, run.id)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
