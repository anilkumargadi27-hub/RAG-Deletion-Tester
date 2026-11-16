import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

class SyntheticFixture(Base):
    __tablename__ = "synthetic_fixtures"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scenario_key = Column(String(128), unique=True, index=True, nullable=False)
    department = Column(String(64), index=True, nullable=False)
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    canary_string = Column(String(128), index=True, nullable=False)
    protected_fact = Column(String(512), nullable=False)
    positive_control_question = Column(String(512), nullable=False)
    positive_control_fact = Column(String(512), nullable=False)
    baseline_question = Column(String(512), nullable=False)
    baseline_expected_answer = Column(String(512), nullable=False)
    direct_questions_json = Column(Text, default="[]", nullable=False)
    paraphrased_questions_json = Column(Text, default="[]", nullable=False)
    follow_up_questions_json = Column(Text, default="[]", nullable=False)
    initial_principals_json = Column(Text, default="[]", nullable=False)
    revoked_principals_json = Column(Text, default="[]", nullable=False)
    mutation_type = Column(String(32), default="deletion", nullable=False) # deletion or revocation
    category = Column(String(64), default="general", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(256), nullable=False)
    description = Column(String(512), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), default="queued", index=True, nullable=False) # queued, running, completed, failed, cancelled, interrupted
    fault_mode = Column(String(64), default="secure_baseline", nullable=False) # secure_baseline, stale_index, stale_cache, stale_memory, combined_stale
    answer_mode = Column(String(64), default="local_extractive", nullable=False) # local_extractive, live_gemini
    retrieval_mode = Column(String(64), default="semantic_vector", nullable=False) # semantic_vector, tfidf_lexical
    total_scenarios = Column(Integer, default=0, nullable=False)
    completed_scenarios = Column(Integer, default=0, nullable=False)
    total_probes = Column(Integer, default=0, nullable=False)
    completed_probes = Column(Integer, default=0, nullable=False)
    leaked_count = Column(Integer, default=0, nullable=False)
    blocked_count = Column(Integer, default=0, nullable=False)
    authorized_success_count = Column(Integer, default=0, nullable=False)
    inconclusive_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    detector_precision = Column(Float, nullable=True)
    detector_recall = Column(Float, nullable=True)
    detector_fpr = Column(Float, nullable=True)
    latency_avg_ms = Column(Float, default=0.0, nullable=False)
    cancellation_requested = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    comparison_run_id = Column(String(36), nullable=True)
    is_guided_demo = Column(Boolean, default=False, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    probes = relationship("ProbeResult", back_populates="run", cascade="all, delete-orphan", order_by="ProbeResult.probe_index")

class ProbeResult(Base):
    __tablename__ = "probe_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_key = Column(String(128), index=True, nullable=False)
    probe_index = Column(Integer, nullable=False)
    query = Column(Text, nullable=False)
    probe_type = Column(String(64), nullable=False) # baseline, direct, paraphrased, follow_up, fresh_session, positive_control, public_question
    target_principal = Column(String(128), nullable=False)
    pre_or_post = Column(String(32), default="post_mutation", nullable=False) # pre_mutation, post_mutation
    response_text = Column(Text, nullable=False)
    detected_fact = Column(String(512), nullable=True)
    verdict = Column(String(32), nullable=False) # leaked, blocked, authorized_success, inconclusive, error
    confidence = Column(Float, default=1.0, nullable=False)
    evidence_span = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    storage_consulted_json = Column(Text, default="[]", nullable=False)
    storage_contributed_json = Column(Text, default="[]", nullable=False)
    decision_details_json = Column(Text, default="{}", nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("TestRun", back_populates="probes")
    traces = relationship("TraceEntry", back_populates="probe", cascade="all, delete-orphan", order_by="TraceEntry.created_at")

class TraceEntry(Base):
    __tablename__ = "trace_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    probe_id = Column(String(36), ForeignKey("probe_results.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(128), nullable=False)
    layer = Column(String(64), nullable=False) # retrieval, cache, conversation_memory, authorization, generator
    status = Column(String(32), nullable=False) # consulted, contributed, blocked, bypassed, unknown
    details_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    probe = relationship("ProbeResult", back_populates="traces")

class CleanupJob(Base):
    __tablename__ = "cleanup_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), nullable=False, index=True)
    target_store = Column(String(64), nullable=False) # database, chroma, cache, memory
    status = Column(String(32), default="pending", index=True, nullable=False) # pending, running, completed, failed
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True, index=True)
    action = Column(String(128), index=True, nullable=False)
    target_type = Column(String(64), nullable=False)
    target_id = Column(String(128), nullable=False)
    details_json = Column(Text, default="{}", nullable=False)
    client_ip = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class RegressionCase(Base):
    __tablename__ = "regression_cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), nullable=False)
    scenario_key = Column(String(128), nullable=False)
    seed = Column(Integer, default=42, nullable=False)
    principal = Column(String(128), nullable=False)
    mutation_type = Column(String(32), nullable=False)
    questions_json = Column(Text, nullable=False)
    expected_fault_verdict = Column(String(32), default="leaked", nullable=False)
    expected_secure_verdict = Column(String(32), default="blocked", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
