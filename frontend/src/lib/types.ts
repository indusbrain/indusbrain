/**
 * Type definitions mirroring the IndusBrain backend response contracts.
 *
 * These are kept deliberately close to what the API actually returns so that a
 * backend schema change surfaces as a TypeScript error rather than a blank
 * screen at runtime.
 */

// ---------------------------------------------------------------------------
// Telemetry / dashboard
// ---------------------------------------------------------------------------
export type ServiceStatus = 'ONLINE' | 'OFFLINE' | 'NO_MODELS';

export interface Infrastructure {
  postgresql: ServiceStatus;
  neo4j: ServiceStatus;
  chromadb: ServiceStatus;
  ollama_qwen: ServiceStatus;
  ollama_models: string[];
}

export interface DashboardMetrics {
  total_documents: number;
  total_chunks: number;
  total_assets: number;
  documented_assets: number;
  knowledge_score: number;
  asset_completeness: number;
  maintenance_coverage: number;
  safety_coverage: number;
  procedure_coverage: number;
  inspection_coverage: number;
  documentation_gaps: number;
  duplicate_documents: number;
  failed_documents: number;
  open_conflicts: number;
}

export interface ScoreBreakdown {
  base_asset_completeness: number;
  conflict_penalty: number;
  failure_penalty: number;
  formula: string;
  explanation: string;
}

export type DocumentStatus = 'PENDING' | 'PARSED' | 'EMBEDDED' | 'FAILED';

export interface InventoryDocument {
  id: number;
  filename: string;
  status: DocumentStatus;
  chunk_count: number;
  file_size: number;
  mime_type: string;
  uploaded_at: string | null;
}

export type CoverageCategory = 'maintenance' | 'safety' | 'procedure' | 'inspection';

export interface AssetRecord {
  tag: string;
  category: string;
  mentions: number;
  document_count: number;
  documents: string[];
  coverage: Record<CoverageCategory, boolean>;
  missing_coverage: CoverageCategory[];
  status: 'Documented' | 'Gaps';
}

export interface ConflictFinding {
  asset_tag: string;
  parameter: string;
  unit: string;
  severity: 'CRITICAL' | 'WARNING';
  variance: number;
  low_value: number;
  low_source: string;
  low_context: string;
  high_value: number;
  high_source: string;
  high_context: string;
  conflict_statement: string;
  recommended_action: string;
}

export interface KnowledgeGap {
  id: string;
  asset: string;
  category: CoverageCategory;
  severity: 'HIGH' | 'MEDIUM';
  statement: string;
}

export interface DashboardPayload {
  generated_at: number;
  cached?: boolean;
  infrastructure: Infrastructure;
  metrics: DashboardMetrics;
  score_breakdown: ScoreBreakdown;
  inventory: InventoryDocument[];
  assets: AssetRecord[];
  conflicts: ConflictFinding[];
  knowledge_gaps: KnowledgeGap[];
  empty_states: {
    no_documents: boolean;
    no_assets: boolean;
    no_conflicts: boolean;
    conflicts_reason: string | null;
  };
}

// ---------------------------------------------------------------------------
// Query / chat
// ---------------------------------------------------------------------------
export type RetrievalOrigin =
  | 'VECTOR_PROXIMITY_MATRIX'
  | 'GRAPH_TOPOLOGY_WALK'
  | 'HYBRID_GRAPH_VECTOR_VERIFIED'
  | 'UNKNOWN';

export interface Citation {
  filename: string;
  excerpt: string;
  relevance: number;
  origin: RetrievalOrigin;
  document_id: number | string | null;
  chunk_index: number | null;
}

export type ConfidenceBand = 'HIGH' | 'MODERATE' | 'LOW' | 'NO_EVIDENCE' | 'NOT_APPLICABLE';

export interface ConfidenceMetadata {
  score: number;
  band: ConfidenceBand;
  explanation: string;
  sources: string[];
  top_relevance: number;
  mean_relevance: number;
  graph_verified: boolean;
  distinct_sources: number;
  candidates_considered: number;
  vector_candidates: number;
  graph_candidates: number;
}

export interface MaintenanceEvent {
  date: string | null;
  date_known: boolean;
  asset: string | null;
  work_order: string | null;
  action: string;
  source: string;
  verbatim: boolean;
}

export interface OrganizationalMemory {
  repair_history_found: boolean;
  past_actions: MaintenanceEvent[];
  empty_reason: string | null;
}

export interface TraceStep {
  step: number;
  node: string;
  title: string;
  status: 'COMPLETED' | 'SKIPPED' | 'NO_RESULTS' | 'REFUSED';
  detail: string;
  metrics?: Record<string, unknown>;
}

export interface QueryResponse {
  response: string;
  confidence_score: number;
  confidence_band: ConfidenceBand;
  confidence_explanation: string;
  reasoning_path: string[];
  current_agent: string;
  session_id: string;
  engine: string;
  grounded: boolean;
  notice: string | null;
  citations: Citation[];
  confidence_metadata: ConfidenceMetadata;
  organizational_memory: OrganizationalMemory;
  decision_replay_path: TraceStep[];
}

// ---------------------------------------------------------------------------
// Other endpoints
// ---------------------------------------------------------------------------
export interface ConflictScanResult {
  conflict_detected: boolean;
  severity: 'CRITICAL' | 'WARNING' | 'OK';
  detected_anomalies: ConflictFinding[];
  chunks_scanned: number;
  empty_reason?: string;
}

export interface SimulationResult {
  scenario: string;
  target_asset: string;
  metrics: {
    production_impact_pct: number;
    risk_multiplier_factor: number;
    compliance_vulnerability_index: number;
    reliability_degradation_pct: number;
  };
  mitigation_directive: string;
}

export interface UploadQueueItem {
  id: number;
  filename: string;
  status: string;
}

export interface UploadResponse {
  message: string;
  queue_manifest: UploadQueueItem[];
}

export interface IngestionStatus {
  id: number;
  filename: string;
  current_pipeline_stage: string;
}

export interface ChatHistoryMessage {
  id: number;
  sender: 'operator' | 'agent';
  content: string;
  created_at: string | null;
}

export interface ChatHistory {
  session_id: string;
  message_count: number;
  messages: ChatHistoryMessage[];
}

// ---------------------------------------------------------------------------
// Roles and permissions
// ---------------------------------------------------------------------------
export type RoleId = 'engineer' | 'manager';

export type PermissionId =
  | 'view_dashboard'
  | 'view_knowledge'
  | 'view_conflicts'
  | 'view_analytics'
  | 'ask_questions'
  | 'run_simulation'
  | 'scan_conflicts'
  | 'upload_documents'
  | 'delete_documents'
  | 'rebuild_index';

export interface RoleDefinition {
  id: RoleId;
  name: string;
  description: string;
  permissions: PermissionId[];
}

export interface RolesResponse {
  authentication_implemented: boolean;
  notice: string;
  roles: RoleDefinition[];
}
