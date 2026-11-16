export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'auditor' | 'member';
  is_active: boolean;
  created_at: string;
}

export interface DocumentACL {
  id: string;
  principal_id: string;
  permission_level: string;
  is_active: boolean;
  granted_at: string;
  revoked_at?: string | null;
}

export interface DocumentItem {
  id: string;
  title: string;
  department: string;
  content_version: number;
  indexing_status: 'pending' | 'indexing' | 'ready' | 'failed' | 'deleted';
  is_tombstoned: boolean;
  tombstoned_at?: string | null;
  file_size: number;
  mime_type: string;
  acl_epoch: number;
  created_at: string;
  updated_at: string;
  permitted_principals: string[];
  raw_text?: string;
  chunks_count?: number;
  acls?: DocumentACL[];
}

export interface Citation {
  document_id: string;
  document_title: string;
  chunk_id: string;
  snippet: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations: Citation[];
  answer_mode?: string;
  is_cache_hit?: boolean;
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  principal_id: string;
  is_invalidated: boolean;
  invalidated_reason?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Scenario {
  id: string;
  scenario_key: string;
  department: string;
  title: string;
  mutation_type: string;
  canary_string: string;
  protected_fact: string;
  positive_control_question: string;
  baseline_question: string;
  category: string;
}

export interface TraceEntry {
  id: string;
  step_name: string;
  layer: string;
  status: 'consulted' | 'contributed' | 'blocked' | 'bypassed' | 'unknown';
  details: Record<string, any>;
  created_at: string;
}

export interface ProbeResult {
  id: string;
  scenario_key: string;
  probe_index: number;
  query: string;
  probe_type: string;
  target_principal: string;
  pre_or_post: string;
  response_text: string;
  detected_fact?: string | null;
  verdict: 'leaked' | 'blocked' | 'authorized_success' | 'inconclusive' | 'error';
  confidence: number;
  evidence_span?: string | null;
  reason?: string | null;
  storage_consulted: string[];
  storage_contributed: string[];
  latency_ms: number;
  error?: string | null;
  created_at: string;
  traces: TraceEntry[];
}

export interface TestRun {
  id: string;
  name: string;
  description?: string | null;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';
  fault_mode: string;
  answer_mode: string;
  retrieval_mode: string;
  total_scenarios: number;
  completed_scenarios: number;
  total_probes: number;
  completed_probes: number;
  leaked_count: number;
  blocked_count: number;
  authorized_success_count: number;
  inconclusive_count: number;
  error_count: number;
  detector_precision?: number | null;
  detector_recall?: number | null;
  detector_fpr?: number | null;
  latency_avg_ms: number;
  cancellation_requested: boolean;
  is_guided_demo: boolean;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  probes?: ProbeResult[];
}

export interface Diagnostics {
  environment: string;
  database: {
    path: string;
    total_documents: number;
    tombstoned_documents: number;
    total_chunks: number;
    total_runs: number;
    pending_cleanup_jobs: number;
  };
  vector_store: {
    type: string;
    directory: string;
    production_chunks_count: number;
  };
  embedding_service: {
    active_mode: string;
    model_cache_dir: string;
  };
  ai_provider: {
    gemini_configured: boolean;
    gemini_model: string;
    active_default_mode: string;
  };
  worker: {
    status: string;
  };
}
