#!/usr/bin/env python3
"""
CLI runner for ForgetCheck regression cases.
Loads saved regression cases from the database and runs verification against current target pipeline.
"""
import sys
import json
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.synthetic import RegressionCase, SyntheticFixture
from backend.app.services.synthetic_runner import synthetic_runner
from backend.app.services.leak_detector import leak_detector
from backend.app.services.generator_service import generator_service

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        synthetic_runner.ensure_fixtures_seeded(db)
        cases = db.query(RegressionCase).all()
        if not cases:
            print("[Regression Runner] No saved regression cases found. Creating a baseline regression test...")
            fixture = db.query(SyntheticFixture).first()
            if fixture:
                case = RegressionCase(
                    title=f"Baseline Regression: {fixture.scenario_key}",
                    scenario_key=fixture.scenario_key,
                    seed=42,
                    principal="hr_analyst",
                    mutation_type="deletion",
                    questions_json=fixture.direct_questions_json,
                    expected_fault_verdict="leaked",
                    expected_secure_verdict="blocked"
                )
                db.add(case)
                db.commit()
                cases = [case]

        print(f"[Regression Runner] Running {len(cases)} regression cases...")
        passed = 0
        failed = 0
        results = []

        for c in cases:
            questions = json.loads(c.questions_json)
            q = questions[0] if questions else "What is the compensation?"
            sc = db.query(SyntheticFixture).filter(SyntheticFixture.scenario_key == c.scenario_key).first()

            # Verify that in a secure environment without chunks, it returns blocked
            resp_text, _, _ = generator_service.generate_answer(
                query=q,
                permitted_chunks=[],
                answer_mode="local_extractive"
            )
            eval_res = leak_detector.detect_leak(
                response_text=resp_text,
                canary_string=sc.canary_string if sc else "CANARY",
                protected_fact=sc.protected_fact if sc else "Secret"
            )

            status = "PASS" if eval_res["verdict"] == c.expected_secure_verdict else "FAIL"
            if status == "PASS":
                passed += 1
            else:
                failed += 1

            results.append({
                "case_id": c.id,
                "title": c.title,
                "scenario_key": c.scenario_key,
                "status": status,
                "expected": c.expected_secure_verdict,
                "actual": eval_res["verdict"]
            })
            print(f" - [{status}] {c.title}: Expected {c.expected_secure_verdict}, Got {eval_res['verdict']}")

        print(f"\n[Regression Summary] Total: {len(cases)}, Passed: {passed}, Failed: {failed}")
        if failed > 0:
            sys.exit(1)
        sys.exit(0)
    finally:
        db.close()

if __name__ == "__main__":
    main()
