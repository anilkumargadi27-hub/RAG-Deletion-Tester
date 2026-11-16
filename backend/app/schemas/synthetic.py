from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ScenarioResponse(BaseModel):
    id: str
    scenario_key: str
    department: str
    title: str
    mutation_type: str
    canary_string: str
    protected_fact: str
    positive_control_question: str
    baseline_question: str
    category: str

    class Config:
        from_attributes = True

class TestRunCreateRequest(BaseModel):
    name: Optional[str] = "Synthetic RAG Deletion Test"
    scenario_keys: Optional[List[str]] = None # Empty means all scenarios
    fault_mode: str = "secure_baseline" # secure_baseline, stale_index, stale_cache, stale_memory, combined_stale
    answer_mode: str = "local_extractive" # local_extractive, live_gemini
    retrieval_mode: str = "semantic_vector" # semantic_vector, tfidf_lexical
    is_guided_demo: bool = False

class TraceEntryResponse(BaseModel):
    id: str
    step_name: str
    layer: str
    status: str
    details: Dict[str, Any] = {}
    created_at: datetime

class ProbeResultResponse(BaseModel):
    id: str
    scenario_key: str
    probe_index: int
    query: str
    probe_type: str
    target_principal: str
    pre_or_post: str
    response_text: str
    detected_fact: Optional[str] = None
    verdict: str
    confidence: float
    evidence_span: Optional[str] = None
    reason: Optional[str] = None
    storage_consulted: List[str] = []
    storage_contributed: List[str] = []
    latency_ms: float
    error: Optional[str] = None
    created_at: datetime
    traces: List[TraceEntryResponse] = []

class TestRunResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    fault_mode: str
    answer_mode: str
    retrieval_mode: str
    total_scenarios: int
    completed_scenarios: int
    total_probes: int
    completed_probes: int
    leaked_count: int
    blocked_count: int
    authorized_success_count: int
    inconclusive_count: int
    error_count: int
    detector_precision: Optional[float] = None
    detector_recall: Optional[float] = None
    detector_fpr: Optional[float] = None
    latency_avg_ms: float
    cancellation_requested: bool
    is_guided_demo: bool
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    probes: List[ProbeResultResponse] = []

    class Config:
        from_attributes = True

class ReplaySourceRequest(BaseModel):
    probe_id: str
    suppress_layer: str # cache, vector_store, conversation_memory

class ReplaySourceResponse(BaseModel):
    original_verdict: str
    replayed_verdict: str
    suppressed_layer: str
    attribution_conclusion: str
    replayed_response: str
    traces: List[Dict[str, Any]] = []

class SaveRegressionRequest(BaseModel):
    probe_id: str
    title: Optional[str] = None
