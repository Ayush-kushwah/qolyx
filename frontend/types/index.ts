// Trust Score types
export interface TrustScore {
  id: string;
  pipeline_run_id: string;
  table_name: string;
  contract_penalty: number;
  freshness_penalty: number;
  volume_penalty: number;
  anomaly_penalty: number;
  dbt_penalty: number;
  total_penalty: number;
  trust_score: number;
  trust_score_status: 'HEALTHY' | 'WARNING' | 'DEGRADED' | 'CRITICAL';
  created_at: string;
  updated_at: string;
}

export interface TrustScoreHistoryResponse {
  items: TrustScore[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// Incident types
export interface Incident {
  id: string;
  trust_score_id: string | null;
  pipeline_run_id: string;
  table_name: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  state: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'CLOSED' | 'REOPENED';
  assigned_to: string | null;
  assigned_team: string | null;
  title: string;
  created_at: string;
  updated_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  resolution_notes: string | null;
  escalated_at: string | null;
  escalation_level: number;
  muted_until: string | null;
  timeline?: IncidentTimeline[];
  comments?: IncidentComment[];
  rca?: IncidentRCA;
}

export interface IncidentTimeline {
  id: string;
  incident_id: string;
  event_type: string;
  event_data: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string;
}

export interface IncidentComment {
  id: string;
  incident_id: string;
  comment: string;
  created_by: string;
  created_at: string;
}

export interface IncidentRCA {
  id: string;
  incident_id: string;
  version: number;
  summary: string;
  root_cause: string;
  contributing_factors: string[] | null;
  recommendation: string | null;
  primary_penalty: string;
  confidence: number;
  generated_at: string;
}

export interface IncidentListResponse {
  items: Incident[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface IncidentStatsResponse {
  by_severity: Record<string, number>;
  by_state: Record<string, number>;
  total_open: number;
  total_acknowledged: number;
  total_resolved: number;
  total_closed: number;
}

// Anomaly types
export interface AnomalyDetection {
  id: string;
  pipeline_run_id: string;
  table_name: string;
  anomaly_type: string;
  anomaly_score: number;
  anomaly_penalty: number;
  feature_values: Record<string, unknown> | null;
  explanation: string | null;
  is_acknowledged: boolean;
  is_false_positive: boolean;
  created_at: string;
}

export interface AnomalyListResponse {
  detections: AnomalyDetection[];
  total: number;
  page: number;
  page_size: number;
}

// Contract types
export interface Contract {
  id: string;
  name: string;
  table_name: string;
  version: number;
  schema_definition: Record<string, ColumnExpectation>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ColumnExpectation {
  data_type: string;
  nullable: boolean;
  max_length?: number | null;
  is_required?: boolean;
}

// Alert Config types
export interface AlertConfig {
  id: string;
  name: string;
  channel_type: 'slack' | 'discord' | 'teams' | 'telegram' | 'email' | 'ntfy' | 'webhook';
  webhook_url?: string | null;
  email_config?: EmailConfig | null;
  telegram_bot_token?: string | null;
  telegram_chat_id?: string | null;
  severity_threshold: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailConfig {
  smtp_server?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  from_address?: string;
  to_addresses?: string[];
}

// Rotation types
export interface OncallRotation {
  id: string;
  name: string;
  team_name: string;
  members: string[];
  current_index: number;
  rotation_type: 'DAILY' | 'WEEKLY' | 'HOURLY';
  last_rotated_at: string | null;
  created_at: string;
  updated_at: string;
}

// Escalation Policy types
export interface EscalationPolicy {
  id: string;
  name: string;
  severity: string;
  timeout_minutes: number;
  target_type: string;
  target_identifier: string;
  created_at: string;
  updated_at: string;
}

// Settings types (for custom frequency feature - UI only, backend pending)
export interface PipelineFrequencySettings {
  pipeline_name: string;
  run_frequency_minutes: number;
  alert_frequency_minutes: number;
  anomaly_immediate_alert: boolean;
  sensitivity: 'LOW' | 'MEDIUM' | 'HIGH';
  severity_overrides?: Record<string, number>;
}

// Filter and Creation types (added to support API libraries and React Query)
export interface IncidentFilters {
  severity?: string | null;
  state?: string | null;
  table_name?: string | null;
  page?: number;
  page_size?: number;
}

export interface AnomalyFilters {
  table_name?: string | null;
  anomaly_type?: string | null;
  page?: number;
  page_size?: number;
}

export interface ContractCreate {
  name: string;
  table_name: string;
  schema_definition: Record<string, ColumnExpectation>;
  is_active?: boolean;
}

export interface ContractUpdate {
  name?: string;
  schema_definition?: Record<string, ColumnExpectation>;
  is_active?: boolean;
}

export interface AlertConfigCreate {
  name: string;
  channel_type: 'slack' | 'discord' | 'teams' | 'telegram' | 'email' | 'ntfy' | 'webhook';
  webhook_url?: string | null;
  email_config?: EmailConfig | null;
  telegram_bot_token?: string | null;
  telegram_chat_id?: string | null;
  severity_threshold: string;
  is_active?: boolean;
}

export interface AlertConfigUpdate {
  name?: string;
  channel_type?: 'slack' | 'discord' | 'teams' | 'telegram' | 'email' | 'ntfy' | 'webhook';
  webhook_url?: string | null;
  email_config?: EmailConfig | null;
  telegram_bot_token?: string | null;
  telegram_chat_id?: string | null;
  severity_threshold?: string;
  is_active?: boolean;
}

export interface OncallRotationCreate {
  name: string;
  team_name: string;
  members: string[];
  rotation_type: 'DAILY' | 'WEEKLY' | 'HOURLY';
}

export interface EscalationPolicyCreate {
  name: string;
  severity: string;
  timeout_minutes: number;
  target_type: string;
  target_identifier: string;
}

export interface BaselineProgress {
  runs_completed: number;
  runs_needed: number;
  is_ready: boolean;
  estimated_minutes_remaining: number | null;
}

export interface BaselineProgressResponse {
  bronze_financial_candles: BaselineProgress;
  bronze_fda_events: BaselineProgress;
  bronze_github_events: BaselineProgress;
}


// User Profile & Settings Hub types
export interface UserProfile {
  id: string;
  name: string;
  email: string;
  username: string;
  avatar_url?: string | null;
  job_title?: string | null;
  department?: string | null;
  timezone: string;
  theme: string;
  date_format: string;
  notification_preferences?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface UserProfileUpdate {
  name?: string;
  username?: string;
  job_title?: string | null;
  department?: string | null;
  timezone?: string;
  theme?: string;
  date_format?: string;
  notification_preferences?: Record<string, any> | null;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export interface ActiveSession {
  id: string;
  device?: string | null;
  browser?: string | null;
  ip_address?: string | null;
  location?: string | null;
  last_active_at: string;
  is_active: boolean;
}

export interface LoginHistoryEntry {
  id: string;
  timestamp: string;
  ip_address?: string | null;
  location?: string | null;
  device?: string | null;
  browser?: string | null;
  success: boolean;
}

export interface AppSettings {
  cors_origins: string[];
  data_retention_days: number;
  incident_threshold: number;
  global_webhook_url?: string | null;
}

export interface AppSettingsUpdate {
  cors_origins?: string[];
  data_retention_days?: number;
  incident_threshold?: number;
  global_webhook_url?: string | null;
}

export interface ApiKeyCreateRequest {
  name: string;
  expires_in_days?: number | null;
}

export interface ApiKeyCreatedResponse {
  id: string;
  name: string;
  key: string;
  key_preview: string;
  permissions?: string[] | null;
  created_at: string;
  expires_at?: string | null;
}

export interface ApiKey {
  id: string;
  name: string;
  key_preview: string;
  permissions?: string[] | null;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
}

export interface IntegrationConnectionRequest {
  name: string;
  provider: string; // SNOWFLAKE, BIGQUERY, POSTGRESQL, AIRFLOW
  config: Record<string, any>;
  is_active?: boolean;
}

export interface IntegrationConnection {
  id: string;
  name: string;
  provider: string;
  is_active: boolean;
  config_preview: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface SyncedAsset {
  name: string;
  type: string;
  records?: number | null;
  schedule?: string | null;
  reliability_enabled: boolean;
}

export interface IntegrationTestResponse {
  success: boolean;
  message: string;
}


