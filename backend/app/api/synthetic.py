import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.synthetic import (
    SyntheticFixture, TestRun, ProbeResult, TraceEntry, RegressionCase
)
from backend.app.schemas.synthetic import (
    ScenarioResponse, TestRunCreateRequest, TestRunResponse,
    ProbeResultResponse, TraceEntryResponse, ReplaySourceRequest,
    ReplaySourceResponse, SaveRegressionRequest
)
from backend.app.core.security import get_current_user, require_roles
from backend.app.services.synthetic_runner import synthetic_runner

router = APIRouter(prefix="/api/synthetic", tags=["Synthetic Laboratory"])

def _format_probe_response(p: ProbeResult) -> ProbeResultResponse:
    traces = [
        TraceEntryResponse(
            id=t.id,
            step_name=t.step_name,
            layer=t.layer,
            status=t.status,
            details=json.loads(t.details_json),
            created_at=t.created_at
        )
        for t in p.traces
    ]
    return ProbeResultResponse(
        id=p.id,
        scenario_key=p.scenario_key,
        probe_index=p.probe_index,
        query=p.query,
        probe_type=p.probe_type,
        target_principal=p.target_principal,
        pre_or_post=p.pre_or_post,
        response_text=p.response_text,
        detected_fact=p.detected_fact,
        verdict=p.verdict,
        confidence=p.confidence,
        evidence_span=p.evidence_span,
        reason=p.reason,
        storage_consulted=json.loads(p.storage_consulted_json),
        storage_contributed=json.loads(p.storage_contributed_json),
        latency_ms=p.latency_ms,
        error=p.error,
        created_at=p.created_at,
        traces=traces
    )

def _format_run_response(run: TestRun, include_probes: bool = True) -> TestRunResponse:
    probes_list = [_format_probe_response(p) for p in run.probes] if include_probes else []
    return TestRunResponse(
        id=run.id,
        name=run.name,
        description=run.description,
        status=run.status,
        fault_mode=run.fault_mode,
        answer_mode=run.answer_mode,
        retrieval_mode=run.retrieval_mode,
        total_scenarios=run.total_scenarios,
        completed_scenarios=run.completed_scenarios,
        total_probes=run.total_probes,
        completed_probes=run.completed_probes,
        leaked_count=run.leaked_count,
        blocked_count=run.blocked_count,
        authorized_success_count=run.authorized_success_count,
        inconclusive_count=run.inconclusive_count,
        error_count=run.error_count,
        detector_precision=run.detector_precision,
        detector_recall=run.detector_recall,
        detector_fpr=run.detector_fpr,
        latency_avg_ms=run.latency_avg_ms,
        cancellation_requested=run.cancellation_requested,
        is_guided_demo=run.is_guided_demo,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        probes=probes_list
    )

@router.get("/scenarios", response_model=List[ScenarioResponse])
def list_scenarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    synthetic_runner.ensure_fixtures_seeded(db)
    fixtures = db.query(SyntheticFixture).all()
    return [ScenarioResponse.model_validate(f) for f in fixtures]

@router.get("/runs", response_model=List[TestRunResponse])
def list_runs(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    query = db.query(TestRun)
    if status_filter:
        query = query.filter(TestRun.status == status_filter)
    runs = query.order_by(TestRun.created_at.desc()).limit(limit).all()
    return [_format_run_response(r, include_probes=False) for r in runs]

@router.post("/runs", response_model=TestRunResponse)
def create_test_run(
    payload: TestRunCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    synthetic_runner.ensure_fixtures_seeded(db)

    # Idempotency / active queue check: prevent duplicate spam clicks
    active_run = db.query(TestRun).filter(
        TestRun.user_id == current_user.id,
        TestRun.status.in_(["queued", "running"])
    ).first()
    if active_run:
        # Return existing active run if started within last 10 seconds
        return _format_run_response(active_run, include_probes=True)

    new_run = TestRun(
        name=payload.name or f"Synthetic Run ({payload.fault_mode})",
        user_id=current_user.id,
        status="queued",
        fault_mode=payload.fault_mode,
        answer_mode=payload.answer_mode,
        retrieval_mode=payload.retrieval_mode,
        is_guided_demo=payload.is_guided_demo
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    return _format_run_response(new_run, include_probes=False)

@router.get("/runs/{run_id}", response_model=TestRunResponse)
def get_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found.")
    return _format_run_response(run, include_probes=True)

@router.post("/runs/{run_id}/cancel")
def cancel_test_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found.")

    if run.status in ["queued", "running"]:
        run.cancellation_requested = True
        if run.status == "queued":
            run.status = "cancelled"
            run.completed_at = datetime.utcnow()
        db.commit()
        return {"message": "Cancellation request submitted."}
    return {"message": f"Run is already {run.status}."}

@router.post("/replay", response_model=ReplaySourceResponse)
def replay_source(
    payload: ReplaySourceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    try:
        res = synthetic_runner.replay_suspected_source(
            db=db,
            probe_id=payload.probe_id,
            suppress_layer=payload.suppress_layer
        )
        return ReplaySourceResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/regression")
def save_regression_case(
    payload: SaveRegressionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    probe = db.query(ProbeResult).filter(ProbeResult.id == payload.probe_id).first()
    if not probe:
        raise HTTPException(status_code=404, detail="Probe not found.")

    sc = db.query(SyntheticFixture).filter(SyntheticFixture.scenario_key == probe.scenario_key).first()
    title = payload.title or f"Regression: {probe.scenario_key} ({probe.probe_type})"

    case = RegressionCase(
        title=title,
        scenario_key=probe.scenario_key,
        seed=42,
        principal=probe.target_principal,
        mutation_type=sc.mutation_type if sc else "deletion",
        questions_json=json.dumps([probe.query]),
        expected_fault_verdict=probe.verdict,
        expected_secure_verdict="blocked"
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"message": "Regression case saved successfully.", "id": case.id}

@router.get("/regression")
def list_regression_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    cases = db.query(RegressionCase).order_by(RegressionCase.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "scenario_key": c.scenario_key,
            "principal": c.principal,
            "mutation_type": c.mutation_type,
            "expected_fault_verdict": c.expected_fault_verdict,
            "expected_secure_verdict": c.expected_secure_verdict,
            "created_at": c.created_at
        }
        for c in cases
    ]
