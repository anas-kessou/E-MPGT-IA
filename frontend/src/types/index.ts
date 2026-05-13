/**
 * E-MPGT-IA TypeScript Types
 */

// ── Chat Types ────────────────────────────────────────────────────

export interface SourceReference {
  document_name: string;
  page_number?: number;
  chunk_text?: string;
  relevance_score: number;
  document_type?: string;
}

export interface ConformityCheck {
  norm_reference: string;
  status: 'conforme' | 'non-conforme' | 'à vérifier';
  detail: string;
  severity: 'info' | 'warning' | 'critical';
}

export interface ChatResponse {
  reply: string;
  sources: SourceReference[];
  conformity: ConformityCheck[];
  agent_used: string;
  processing_time_ms: number;
  conversation_id: string;
  timestamp?: string;
}

export interface Message {
  role: 'bot' | 'user';
  content: string;
  sources?: SourceReference[];
  conformity?: ConformityCheck[];
  agent_used?: string;
  processing_time_ms?: number;
  timestamp?: string;
}

// ── Document Types ────────────────────────────────────────────────

export interface DocumentItem {
  id: string;
  filename: string;
  document_type: string;
  project_name?: string;
  lot?: string;
  status: string;
  date_indexed: string;
  num_chunks: number;
  criticite: string;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
}

// ── Resource Files Types ──────────────────────────────────────────

export interface ResourceFile {
  filename: string;
  size_bytes: number;
  size_display: string;
  extension: string;
  ingested: boolean;
}

export interface ResourceListResponse {
  resources: ResourceFile[];
  total: number;
  directory: string;
}

// ── Dashboard Types ───────────────────────────────────────────────

export interface SystemHealth {
  status: string;
  qdrant: string;
  neo4j: string;
  postgres: string;
  minio: string;
  llm: string;
  documents_indexed: number;
  vectors_count: number;
  knowledge_nodes: number;
  uptime_seconds: number;
}

export interface DashboardStats {
  total_documents: number;
  total_projects: number;
  total_vectors: number;
  total_queries_today: number;
  avg_conformity_score: number;
  documents_by_type: Record<string, number>;
  recent_activity: ActivityItem[];
  data_sources_status: DataSourceStatus[];
}

export interface ActivityItem {
  type: string;
  filename: string;
  document_type: string;
  timestamp: string;
  chunks: number;
}

export interface DataSourceStatus {
  name: string;
  status: string;
  count: number;
}

// ── Knowledge Graph Types ─────────────────────────────────────────

export interface GraphOverview {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
}

// ── Navigation ────────────────────────────────────────────────────

export type PageName = 'dashboard' | 'chat' | 'documents' | 'knowledge' | 'settings';

// ── App State Types ───────────────────────────────────────────────

export interface AppSettings {
  llmModel: string;
  temperature: number;
  embeddingModel: string;
  chunkSize: number;
  chunkOverlap: number;
  topK: number;
}

export interface DocumentFilters {
  query: string;
  type: string;
  projectId?: string;
  status?: string;
}

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}
