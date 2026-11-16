import pytest
from backend.app.models.synthetic import TestRun, ProbeResult
from backend.app.services.synthetic_runner import synthetic_runner

def test_secure_baseline_run(db, admin_user):
    run = TestRun(
        name="Secure Baseline Verification",
        user_id=admin_user.id,
        status="queued",
        fault_mode="secure_baseline",
        answer_mode="local_extractive",
        retrieval_mode="semantic_vector",
        is_guided_demo=True # Test representative scenario
    )
    db.add(run)
    db.commit()

    synthetic_runner.run_suite(db, run.id)
    db.refresh(run)

    assert run.status == "completed"
    assert run.leaked_count == 0 # No leakage in secure baseline!
    assert run.blocked_count > 0 # Post-mutation probes correctly blocked
    assert run.authorized_success_count > 0 # Positive control still answered!

def test_stale_index_fault_causes_real_leak(db, admin_user):
    run = TestRun(
        name="Stale Index Fault Verification",
        user_id=admin_user.id,
        status="queued",
        fault_mode="stale_index",
        answer_mode="local_extractive",
        retrieval_mode="semantic_vector",
        is_guided_demo=True
    )
    db.add(run)
    db.commit()

    synthetic_runner.run_suite(db, run.id)
    db.refresh(run)

    assert run.status == "completed"
    assert run.leaked_count > 0 # Stale vector index reproduces real leak!

def test_controlled_source_replay(db, admin_user):
    # Run faulty run
    run = TestRun(
        name="Source Replay Test",
        user_id=admin_user.id,
        status="queued",
        fault_mode="stale_index",
        answer_mode="local_extractive",
        is_guided_demo=True
    )
    db.add(run)
    db.commit()
    synthetic_runner.run_suite(db, run.id)

    # Find the leaked probe
    leaked_probe = db.query(ProbeResult).filter(
        ProbeResult.run_id == run.id,
        ProbeResult.verdict == "leaked"
    ).first()
    assert leaked_probe is not None

    # Replay suppressing vector_store
    replay = synthetic_runner.replay_suspected_source(
        db=db,
        probe_id=leaked_probe.id,
        suppress_layer="vector_store"
    )
    assert replay["original_verdict"] == "leaked"
    assert replay["replayed_verdict"] == "blocked"
    assert "Confirmed root cause" in replay["attribution_conclusion"]
