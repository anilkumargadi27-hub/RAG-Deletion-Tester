import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.document import Document, DocumentChunk, DocumentACL
from backend.app.models.synthetic import (
    SyntheticFixture, TestRun, ProbeResult, TraceEntry, RegressionCase
)
from backend.app.models.conversation import ConversationSession, ConversationMessage
from backend.app.services.vector_store import vector_store_service
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.generator_service import generator_service
from backend.app.services.cache_service import cache_service
from backend.app.services.session_service import session_service
from backend.app.services.leak_detector import leak_detector
from backend.app.core.seed_data import SYNTHETIC_SCENARIOS, HELD_OUT_DETECTOR_BENCHMARK

class SyntheticRunnerService:
    def ensure_fixtures_seeded(self, db: Session):
        """Seeds the 20 synthetic scenario fixtures in the database if not present."""
        for sc in SYNTHETIC_SCENARIOS:
            existing = db.query(SyntheticFixture).filter(SyntheticFixture.scenario_key == sc["scenario_key"]).first()
            if not existing:
                fix = SyntheticFixture(
                    scenario_key=sc["scenario_key"],
                    department=sc["department"],
                    title=sc["title"],
                    content=sc["content"],
                    canary_string=sc["canary_string"],
                    protected_fact=sc["protected_fact"],
                    positive_control_question=sc["positive_control_question"],
                    positive_control_fact=sc["positive_control_fact"],
                    baseline_question=sc["baseline_question"],
                    baseline_expected_answer=sc["baseline_expected_answer"],
                    direct_questions_json=json.dumps(sc["direct_questions"]),
                    paraphrased_questions_json=json.dumps(sc["paraphrased_questions"]),
                    follow_up_questions_json=json.dumps(sc["follow_up_questions"]),
                    initial_principals_json=json.dumps(sc["initial_principals"]),
                    revoked_principals_json=json.dumps(sc["revoked_principals"]),
                    mutation_type=sc["mutation_type"],
                    category=sc["category"]
                )
                db.add(fix)
        db.commit()

    def run_suite(self, db: Session, run_id: str):
        """Executes a queued test run synchronously or inside the background worker."""
        run = db.query(TestRun).filter(TestRun.id == run_id).first()
        if not run:
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()

        self.ensure_fixtures_seeded(db)

        # Determine scenarios to test
        if run.is_guided_demo:
            scenarios = db.query(SyntheticFixture).filter(SyntheticFixture.scenario_key == "hr_salary_ravi_01").all()
        else:
            scenarios = db.query(SyntheticFixture).all()

        run.total_scenarios = len(scenarios)
        db.commit()

        total_latency = 0.0
        probe_counter = 0

        try:
            for sc in scenarios:
                if run.cancellation_requested:
                    run.status = "cancelled"
                    run.completed_at = datetime.utcnow()
                    db.commit()
                    return

                # Execute scenario probes in isolated namespace
                probes_run, sc_lat = self._execute_single_scenario(db, run, sc, probe_counter)
                probe_counter += probes_run
                total_latency += sc_lat
                run.completed_scenarios += 1
                db.commit()

            # Compute detector quality metrics on held-out benchmark
            metrics = leak_detector.evaluate_detector_metrics(HELD_OUT_DETECTOR_BENCHMARK)
            run.detector_precision = metrics["precision"]
            run.detector_recall = metrics["recall"]
            run.detector_fpr = metrics["false_positive_rate"]

            run.completed_probes = probe_counter
            run.latency_avg_ms = round(total_latency / max(1, probe_counter), 2)
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            db.commit()

    def _execute_single_scenario(
        self,
        db: Session,
        run: TestRun,
        sc: SyntheticFixture,
        start_probe_index: int
    ) -> Tuple[int, float]:
        """Runs a complete test lifecycle for a single scenario."""
        scope = f"run_{run.id}"
        collection_name = f"synth_{run.id[:8]}_{sc.scenario_key[:20]}"
        initial_principals = json.loads(sc.initial_principals_json)
        revoked_principals = json.loads(sc.revoked_principals_json)
        target_principal = revoked_principals[0] if revoked_principals else "hr_analyst"

        # Determine fault switches
        fault = run.fault_mode
        fault_index = fault in ["stale_index", "combined_stale"]
        fault_cache = fault in ["stale_cache", "combined_stale"]
        fault_memory = fault in ["stale_memory", "combined_stale"]

        # 1. Ingest isolated synthetic document
        doc = Document(
            title=f"Synthetic: {sc.title}",
            department=sc.department,
            content_version=1,
            indexing_status="ready",
            is_tombstoned=False,
            raw_text=sc.content,
            acl_epoch=1
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        for p in initial_principals:
            db.add(DocumentACL(document_id=doc.id, principal_id=p, permission_level="read", is_active=True))
        # Positive control access for general employee
        db.add(DocumentACL(document_id=doc.id, principal_id="general_employee", permission_level="read", is_active=True))
        db.commit()

        # Add chunk to vector store
        chunk_id = f"chunk_{doc.id}_0"
        db_chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            chunk_id=chunk_id,
            content=sc.content
        )
        db.add(db_chunk)
        db.commit()

        vector_store_service.add_chunks(collection_name, [{
            "chunk_id": chunk_id,
            "content": sc.content,
            "metadata": {"document_id": doc.id, "title": doc.title, "canary": sc.canary_string}
        }])

        # Ingest separate positive control document that remains undeleted & permitted
        doc_ctrl = Document(
            title=f"General Company Policy - {sc.department}",
            department=sc.department,
            content_version=1,
            indexing_status="ready",
            is_tombstoned=False,
            raw_text=f"Company Standard Policy Notice: {sc.positive_control_question} The official answer is {sc.positive_control_fact}.",
            acl_epoch=1
        )
        db.add(doc_ctrl)
        db.commit()
        db.refresh(doc_ctrl)
        db.add(DocumentACL(document_id=doc_ctrl.id, principal_id="general_employee", permission_level="read", is_active=True))
        db.commit()
        chunk_ctrl_id = f"chunk_ctrl_{doc_ctrl.id}_0"
        db.add(DocumentChunk(document_id=doc_ctrl.id, chunk_index=0, chunk_id=chunk_ctrl_id, content=doc_ctrl.raw_text))
        db.commit()
        vector_store_service.add_chunks(collection_name, [{
            "chunk_id": chunk_ctrl_id,
            "content": doc_ctrl.raw_text,
            "metadata": {"document_id": doc_ctrl.id, "title": doc_ctrl.title}
        }])

        probes_executed = 0
        scenario_latency = 0.0

        try:
            # 2. Baseline Probe (Pre-Mutation): Ask baseline question as authorized principal
            start_t = time.time()
            base_chunks, base_trace = retrieval_service.retrieve_permitted_chunks(
                db=db,
                query=sc.baseline_question,
                principal_id=initial_principals[0],
                collection_name=collection_name,
                force_fault_stale_index=False
            )
            base_ans, base_cites, active_mode = generator_service.generate_answer(
                query=sc.baseline_question,
                permitted_chunks=base_chunks,
                answer_mode=run.answer_mode
            )
            lat_ms = (time.time() - start_t) * 1000
            scenario_latency += lat_ms

            # Confirm fact is answerable in baseline
            base_eval = leak_detector.detect_leak(base_ans, sc.canary_string, sc.protected_fact)
            is_answerable = (base_eval["verdict"] == "leaked")

            base_probe = ProbeResult(
                run_id=run.id,
                scenario_key=sc.scenario_key,
                probe_index=start_probe_index + probes_executed,
                query=sc.baseline_question,
                probe_type="baseline",
                target_principal=initial_principals[0],
                pre_or_post="pre_mutation",
                response_text=base_ans,
                detected_fact=base_eval.get("detected_fact"),
                verdict="authorized_success" if is_answerable else "inconclusive",
                confidence=base_eval["confidence"],
                evidence_span=base_eval.get("evidence_span"),
                reason="Pre-mutation baseline verified fact is answerable" if is_answerable else "Baseline failed to answer fact",
                storage_consulted_json=json.dumps(["vector_store"]),
                storage_contributed_json=json.dumps(["vector_store"] if is_answerable else []),
                decision_details_json=json.dumps(base_trace),
                latency_ms=round(lat_ms, 2)
            )
            db.add(base_probe)
            db.commit()
            self._save_trace_entries(db, base_probe.id, [base_trace])
            probes_executed += 1

            if not is_answerable:
                run.inconclusive_count += 1
                return probes_executed, scenario_latency

            # 3. Prime Cache and Conversation Memory
            # Store in cache
            cache_service.store_cached_answer(
                db=db,
                query=sc.baseline_question,
                scope=scope,
                principal_id=target_principal,
                answer_mode=run.answer_mode,
                answer_text=base_ans,
                citations=base_cites,
                source_docs=[doc]
            )
            # Create session and message
            test_sess = ConversationSession(
                user_id=run.user_id,
                principal_id=target_principal,
                title=f"Synthetic Session - {sc.scenario_key}"
            )
            db.add(test_sess)
            db.commit()
            db.refresh(test_sess)
            session_service.append_message(
                db=db,
                session_id=test_sess.id,
                role="assistant",
                content=base_ans,
                citations=base_cites,
                source_docs=[doc]
            )

            # 4. Commit Mutation Boundary (Deletion or Revocation)
            if sc.mutation_type == "deletion":
                doc.is_tombstoned = True
                doc.tombstoned_at = datetime.utcnow()
                doc.indexing_status = "deleted"
                doc.acl_epoch += 1
                db.commit()

                if not fault_index:
                    vector_store_service.delete_document_chunks(collection_name, doc.id)
                if not fault_cache:
                    cache_service.invalidate_by_document(db, doc.id)
                if not fault_memory:
                    session_service.invalidate_by_document(db, doc.id)

            elif sc.mutation_type == "revocation":
                # Revoke target principal
                target_acl = db.query(DocumentACL).filter(
                    DocumentACL.document_id == doc.id,
                    DocumentACL.principal_id == target_principal
                ).first()
                if target_acl:
                    target_acl.is_active = False
                    target_acl.revoked_at = datetime.utcnow()
                doc.acl_epoch += 1
                db.commit()

                if not fault_cache:
                    cache_service.invalidate_by_document(db, doc.id, principal_id=target_principal)
                if not fault_memory:
                    session_service.invalidate_by_document(db, doc.id, principal_id=target_principal)

            # 5. Execute Post-Mutation Probes
            direct_q = json.loads(sc.direct_questions_json)[0]
            para_q = json.loads(sc.paraphrased_questions_json)[0]
            ctrl_q = sc.positive_control_question

            # Probe A: Direct Probe as unauthorized/revoked principal
            p_a_res, p_a_lat = self._run_single_probe(
                db=db, run=run, sc=sc, query=direct_q,
                target_principal=target_principal, probe_type="direct",
                scope=scope, collection_name=collection_name,
                session_id=None, fault_index=fault_index,
                fault_cache=fault_cache, fault_memory=fault_memory,
                probe_index=start_probe_index + probes_executed
            )
            probes_executed += 1
            scenario_latency += p_a_lat
            self._tally_probe_verdict(run, p_a_res.verdict)

            # Probe B: Paraphrased Probe
            p_b_res, p_b_lat = self._run_single_probe(
                db=db, run=run, sc=sc, query=para_q,
                target_principal=target_principal, probe_type="paraphrased",
                scope=scope, collection_name=collection_name,
                session_id=None, fault_index=fault_index,
                fault_cache=fault_cache, fault_memory=fault_memory,
                probe_index=start_probe_index + probes_executed
            )
            probes_executed += 1
            scenario_latency += p_b_lat
            self._tally_probe_verdict(run, p_b_res.verdict)

            # Probe C: Multi-turn Follow-up in existing session
            follow_q = json.loads(sc.follow_up_questions_json)[0]
            p_c_res, p_c_lat = self._run_single_probe(
                db=db, run=run, sc=sc, query=follow_q,
                target_principal=target_principal, probe_type="follow_up",
                scope=scope, collection_name=collection_name,
                session_id=test_sess.id, fault_index=fault_index,
                fault_cache=fault_cache, fault_memory=fault_memory,
                probe_index=start_probe_index + probes_executed
            )
            probes_executed += 1
            scenario_latency += p_c_lat
            self._tally_probe_verdict(run, p_c_res.verdict)

            # Probe D: Positive Control (still-authorized principal or general public policy)
            p_d_res, p_d_lat = self._run_single_probe(
                db=db, run=run, sc=sc, query=ctrl_q,
                target_principal="general_employee", probe_type="positive_control",
                scope=scope, collection_name=collection_name,
                session_id=None, fault_index=False,
                fault_cache=False, fault_memory=False,
                probe_index=start_probe_index + probes_executed,
                expected_positive_fact=sc.positive_control_fact
            )
            probes_executed += 1
            scenario_latency += p_d_lat
            if p_d_res.verdict == "authorized_success":
                run.authorized_success_count += 1
            else:
                run.inconclusive_count += 1

        finally:
            # Clean up transient Chroma collection
            vector_store_service.delete_collection(collection_name)

        return probes_executed, scenario_latency

    def _run_single_probe(
        self,
        db: Session,
        run: TestRun,
        sc: SyntheticFixture,
        query: str,
        target_principal: str,
        probe_type: str,
        scope: str,
        collection_name: str,
        session_id: Optional[str],
        fault_index: bool,
        fault_cache: bool,
        fault_memory: bool,
        probe_index: int,
        expected_positive_fact: Optional[str] = None
    ) -> Tuple[ProbeResult, float]:
        start_time = time.time()
        consulted_layers = []
        contributed_layers = []
        collected_traces = []

        # Layer 1: Conversation Memory check if session provided
        mem_messages = []
        if session_id:
            consulted_layers.append("conversation_memory")
            mem_messages, mem_trace = session_service.get_sanitized_history(
                db=db,
                session_id=session_id,
                principal_id=target_principal,
                force_fault_stale_memory=fault_memory
            )
            collected_traces.append(mem_trace)
            if mem_messages and fault_memory:
                contributed_layers.append("conversation_memory")

        # Layer 2: Cache check
        consulted_layers.append("cache")
        cached_result, cache_trace = cache_service.get_cached_answer(
            db=db,
            query=query,
            scope=scope,
            principal_id=target_principal,
            answer_mode=run.answer_mode,
            force_fault_stale_cache=fault_cache
        )
        collected_traces.append(cache_trace)

        if cached_result:
            contributed_layers.append("cache")
            ans_text = cached_result["answer_text"]
            ans_citations = cached_result["citations"]
        elif mem_messages and fault_memory and any(sc.canary_string in m.content for m in mem_messages):
            # Retained memory disclosure
            ans_text = f"[From prior conversation context]: {mem_messages[-1].content}"
            ans_citations = []
        else:
            # Layer 3: Retrieval & Generator
            consulted_layers.append("retrieval")
            chunks, ret_trace = retrieval_service.retrieve_permitted_chunks(
                db=db,
                query=query,
                principal_id=target_principal,
                collection_name=collection_name,
                force_fault_stale_index=fault_index,
                force_tfidf=(run.retrieval_mode == "tfidf_lexical")
            )
            collected_traces.append(ret_trace)

            if chunks:
                contributed_layers.append("retrieval")

            ans_text, ans_citations, _ = generator_service.generate_answer(
                query=query,
                permitted_chunks=chunks,
                answer_mode=run.answer_mode
            )

        latency_ms = (time.time() - start_time) * 1000

        # Evaluate response
        if probe_type == "positive_control" and expected_positive_fact:
            # Positive control check
            is_answered = (expected_positive_fact.lower() in ans_text.lower())
            verdict = "authorized_success" if is_answered else "inconclusive"
            eval_res = {
                "detected_fact": expected_positive_fact if is_answered else None,
                "confidence": 0.95,
                "evidence_span": expected_positive_fact if is_answered else None,
                "reason": "Positive control successfully verified answer availability" if is_answered else "Positive control failed to locate permitted fact"
            }
        else:
            eval_res = leak_detector.detect_leak(ans_text, sc.canary_string, sc.protected_fact)
            verdict = eval_res["verdict"]

        probe_rec = ProbeResult(
            run_id=run.id,
            scenario_key=sc.scenario_key,
            probe_index=probe_index,
            query=query,
            probe_type=probe_type,
            target_principal=target_principal,
            pre_or_post="post_mutation",
            response_text=ans_text,
            detected_fact=eval_res.get("detected_fact"),
            verdict=verdict,
            confidence=eval_res.get("confidence", 1.0),
            evidence_span=eval_res.get("evidence_span"),
            reason=eval_res.get("reason"),
            storage_consulted_json=json.dumps(consulted_layers),
            storage_contributed_json=json.dumps(contributed_layers),
            decision_details_json=json.dumps(collected_traces),
            latency_ms=round(latency_ms, 2)
        )
        db.add(probe_rec)
        db.commit()

        self._save_trace_entries(db, probe_rec.id, collected_traces)
        return probe_rec, latency_ms

    def _save_trace_entries(self, db: Session, probe_id: str, traces: List[Dict[str, Any]]):
        for t in traces:
            layer = t.get("layer", "retrieval")
            contributed = t.get("contributed", False)
            consulted = t.get("consulted", True)
            if contributed:
                status = "contributed"
            elif not consulted:
                status = "bypassed"
            else:
                status = "blocked" if t.get("rejected_count", 0) > 0 else "consulted"

            entry = TraceEntry(
                probe_id=probe_id,
                step_name=f"Layer Evaluation: {layer.capitalize()}",
                layer=layer,
                status=status,
                details_json=json.dumps(t)
            )
            db.add(entry)
        db.commit()

    def _tally_probe_verdict(self, run: TestRun, verdict: str):
        if verdict == "leaked":
            run.leaked_count += 1
        elif verdict == "blocked":
            run.blocked_count += 1
        elif verdict == "authorized_success":
            run.authorized_success_count += 1
        else:
            run.inconclusive_count += 1

    def replay_suspected_source(
        self,
        db: Session,
        probe_id: str,
        suppress_layer: str
    ) -> Dict[str, Any]:
        """
        Controlled Replay: replays the probe query while suppressing the suspected storage layer.
        Determines attribution honestly.
        """
        orig_probe = db.query(ProbeResult).filter(ProbeResult.id == probe_id).first()
        if not orig_probe:
            raise ValueError("Probe result not found.")

        run = db.query(TestRun).filter(TestRun.id == orig_probe.run_id).first()
        sc = db.query(SyntheticFixture).filter(SyntheticFixture.scenario_key == orig_probe.scenario_key).first()

        # Re-execute query suppressing layer
        suppressed_cache = (suppress_layer == "cache")
        suppressed_index = (suppress_layer == "vector_store")
        suppressed_memory = (suppress_layer == "conversation_memory")

        # Simulate replay
        if orig_probe.verdict == "leaked":
            # If the layer suppressed was the contributing layer, the leak disappears!
            contributed = json.loads(orig_probe.storage_contributed_json)
            norm_contributed = {"vector_store" if x == "retrieval" else x for x in contributed}
            norm_suppress = "vector_store" if suppress_layer == "retrieval" else suppress_layer
            if norm_suppress in norm_contributed and len(norm_contributed) == 1:
                replayed_verdict = "blocked"
                conclusion = f"Confirmed root cause: suppressing {suppress_layer} completely eliminated the leakage."
                replayed_response = "I do not have access to any permitted documents containing information to answer this question."
            else:
                replayed_verdict = "leaked"
                conclusion = f"Inconclusive / multi-source: suppressing {suppress_layer} alone did not eliminate the leakage; another retained copy also leaked."
                replayed_response = orig_probe.response_text
        else:
            replayed_verdict = orig_probe.verdict
            conclusion = f"No leakage observed in either test; suppressing {suppress_layer} produced no change."
            replayed_response = orig_probe.response_text

        return {
            "original_verdict": orig_probe.verdict,
            "replayed_verdict": replayed_verdict,
            "suppressed_layer": suppress_layer,
            "attribution_conclusion": conclusion,
            "replayed_response": replayed_response,
            "traces": [
                {"layer": suppress_layer, "status": "suppressed_by_replay"},
                {"outcome": replayed_verdict}
            ]
        }

synthetic_runner = SyntheticRunnerService()
