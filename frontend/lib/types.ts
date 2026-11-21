export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'manager' | 'analyst' | 'viewer';
  is_active: boolean;
  is_superuser: boolean;
  mfa_enabled: boolean;
  organization_id: string;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  slug: string;
  plan: 'free' | 'pro' | 'enterprise';
  is_single_tenant: boolean;
  settings: Record<string, any>;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
  user_count?: number;
  contract_count?: number;
  analysis_count?: number;
  storage_used_mb?: number;
}

export interface ContractResponse {
  id: string;
  organization_id: string;
  owner_id: string;
  title: string;
  description: string | null;
  source: 'upload' | 'google_drive' | 'onedrive' | 'api';
  source_id: string | null;
  source_url: string | null;
  file_path: string | null;
  file_size: number | null;
  mime_type: string | null;
  status: 'uploaded' | 'parsing' | 'parsed' | 'analyzing' | 'analyzed' | 'error';
  content_hash: string | null;
  page_count: number | null;
  language: string;
  meta: Record<string, any>;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  analysis_count?: number;
  latest_analysis_status?: string | null;
}

export interface ContractCreate {
  title: string;
  description?: string;
  source?: 'upload' | 'google_drive' | 'onedrive' | 'api';
  source_id?: string;
  source_url?: string;
  language?: string;
  file_content?: string;
  file_name?: string;
  mime_type?: string;
}

export interface ContractUploadResponse {
  contract: ContractResponse;
  upload_id: string;
}

export interface AnalysisResponse {
  id: string;
  organization_id: string;
  contract_id: string;
  created_by_id: string;
  type: 'full' | 'clause_extraction' | 'risk_assessment' | 'comparison' | 'entity_extraction';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  llm_provider: string;
  llm_model: string;
  prompt_version: string;
  input_tokens: number | null;
  output_tokens: number | null;
  total_cost_usd: number | null;
  processing_time_ms: number | null;
  result: Record<string, any>;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
  contract_title?: string;
  clause_count?: number;
  high_risk_clause_count?: number;
}

export interface AnalysisCreate {
  contract_id: string;
  type?: 'full' | 'clause_extraction' | 'risk_assessment' | 'comparison' | 'entity_extraction';
  llm_provider?: string;
  llm_model?: string;
  prompt_version?: string;
}

export interface ClauseResponse {
  id: string;
  analysis_id: string;
  contract_id: string;
  organization_id: string;
  clause_number: string | null;
  title: string | null;
  type: 'parties' | 'definitions' | 'scope' | 'obligations' | 'payment' | 'term' | 'termination' | 'liability' | 'indemnification' | 'confidentiality' | 'intellectual_property' | 'dispute_resolution' | 'force_majeure' | 'governing_law' | 'amendment' | 'assignment' | 'notices' | 'general' | 'other';
  content: string;
  content_hash: string;
  page_start: number | null;
  page_end: number | null;
  char_start: number | null;
  char_end: number | null;
  language: string;
  meta: Record<string, any>;
  embedding: number[] | null;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  risk_factors: string[];
  risk_explanation: string | null;
  entities: Record<string, any>;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
}

export interface ConnectorResponse {
  id: string;
  organization_id: string;
  name: string;
  type: 'google_drive' | 'onedrive';
  config: Record<string, any>;
  credentials: Record<string, any>;
  is_active: boolean;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
}

export interface ConnectorCreate {
  name: string;
  type: 'google_drive' | 'onedrive';
  config?: Record<string, any>;
  credentials?: Record<string, any>;
  is_active?: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details: Array<{ code: string; message: string; field?: string; context?: Record<string, any> }>;
  request_id: string | null;
  timestamp: string;
}

export interface SuccessResponse {
  success: boolean;
  message: string;
  data?: Record<string, any>;
  request_id: string | null;
  timestamp: string;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  checks?: Record<string, string>;
}