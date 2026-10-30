import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach JWT token from localStorage
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('aicte_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Typed interfaces
export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  user_id: number;
  full_name: string;
  region_id?: number | null;
  institution_id?: number | null;
}

export interface UserScope {
  user_id: number;
  full_name: string;
  role: string;
  region_id?: number | null;
  region_name?: string | null;
  institution_id?: number | null;
  institution_name?: string | null;
  is_national: boolean;
  is_regional: boolean;
  is_institution: boolean;
  allowed_screens: string[];
}

export interface Institution {
  id: number;
  aicte_id: string;
  name: string;
  institution_type: string;
  category: string;
  region_id: number;
  city: string;
  state: string;
  pincode: string;
  primary_email: string;
  primary_phone: string;
}

export interface Region {
  id: number;
  code: string;
  name: string;
  headquarters: string;
  states_covered: string[];
}

export interface StagePath {
  id: number;
  code: string;
  name: string;
  description?: string;
  stage_sequence: string[];
  is_active: boolean;
}

export interface Stage {
  id: number;
  code: string;
  name: string;
  default_sla_days: number;
  responsible_role: string;
  description?: string;
}

export interface AlertRule {
  id: number;
  code: string;
  name: string;
  alert_type: string;
  entity_type: string;
  condition_logic: Record<string, any>;
  severity: string;
  aph_reference_clause?: string;
  template_message: string;
  is_active: boolean;
}

// API helper functions
export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>('/auth/login', { email, password });
    return res.data;
  },
  demoLogin: async (role: string, email?: string): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>('/auth/demo-login', { role, email });
    return res.data;
  },
  getMe: async () => {
    const res = await apiClient.get('/auth/me');
    return res.data;
  },
  logout: async () => {
    return apiClient.post('/auth/logout');
  },
};

export const lookupApi = {
  getScope: async (): Promise<UserScope> => {
    const res = await apiClient.get<UserScope>('/users/me/scope');
    return res.data;
  },
  getInstitutions: async (): Promise<Institution[]> => {
    const res = await apiClient.get<Institution[]>('/institutions');
    return res.data;
  },
  getRegions: async (): Promise<Region[]> => {
    const res = await apiClient.get<Region[]>('/regions');
    return res.data;
  },
};

export const configApi = {
  getStagePaths: async (): Promise<StagePath[]> => {
    const res = await apiClient.get<StagePath[]>('/config/stage-paths');
    return res.data;
  },
  getStages: async (): Promise<Stage[]> => {
    const res = await apiClient.get<Stage[]>('/config/stages');
    return res.data;
  },
  getRules: async (): Promise<{ alert_rules: AlertRule[]; system_configs: any[] }> => {
    const res = await apiClient.get('/config/rules');
    return res.data;
  },
  getDeficiencyTags: async (): Promise<DeficiencyTag[]> => {
    const res = await apiClient.get<DeficiencyTag[]>('/config/deficiency-tags');
    return res.data;
  },
};

// Phase 3 Application Interfaces
export interface ApplicationItem {
  id: number;
  application_number: string;
  academic_year: string;
  institution_id: number;
  institution_name: string;
  category_id: number;
  category_title: string;
  stage_path_id: number;
  stage_path_name: string;
  current_stage_id: number;
  current_stage_code: string;
  current_stage_name: string;
  status: string;
  assigned_officer_id?: number | null;
  assigned_officer_name?: string | null;
  region_id: number;
  region_name: string;
  stage_entered_at: string;
  stage_due_date: string;
  revert_count: number;
  delay_risk_score: number;
  risk_band?: 'LOW' | 'MEDIUM' | 'HIGH' | null;
  risk_factors: string[];
  days_in_stage: number;
  days_remaining: number;
  percentage_elapsed: number;
  ageing_bucket: 'ON_TIME' | 'NEAR_DUE' | 'OVERDUE' | 'COMPLETED';
  escalation_required: boolean;
  escalation_reason?: string | null;
  approval_letter_ref?: string | null;
  case_holder?: 'WITH_AICTE' | 'WITH_INSTITUTION' | 'CLOSED';
  closed_at?: string | null;
  closure_reason?: string | null;
  closure_remarks?: string | null;
  time_with_aicte_hours?: number;
  time_with_institution_hours?: number;
  created_at: string;
}

export interface ClockSegment {
  id: number;
  application_id: number;
  stage_id?: number | null;
  holder: 'WITH_AICTE' | 'WITH_INSTITUTION';
  started_at: string;
  ended_at?: string | null;
  duration_hours?: number | null;
  remarks?: string | null;
}

export interface StageHistoryItem {
  id: number;
  application_id: number;
  from_stage_id?: number | null;
  from_stage_code?: string | null;
  from_stage_name?: string | null;
  to_stage_id: number;
  to_stage_code: string;
  to_stage_name: string;
  status: string;
  actor_id?: number | null;
  actor_name?: string | null;
  actor_role?: string | null;
  revert_reason?: string | null;
  deficiency_tags?: string[] | null;
  entered_at: string;
  due_date: string;
  completed_at?: string | null;
  duration_hours: number;
}

export interface CommunicationItem {
  id: number;
  application_id: number;
  template_code: string;
  subject: string;
  body: string;
  recipient_email: string;
  status: 'DRAFT' | 'SENT';
  created_at: string;
  sent_at?: string | null;
}

export interface CaseSummaryItem {
  id?: number;
  executive_summary: string;
  key_findings: string[];
  compliance_flags: string[];
  risk_assessment?: string | null;
  source_label?: string;
  input_hash?: string;
  timeline_highlights?: Array<{ stage_name: string; entered_at: string; duration_days: number }>;
  pending_items?: Array<{ type: string; title: string; status: string; due_date?: string }>;
  upcoming_deadlines?: Array<{ item: string; due_date: string; days_left: number }>;
  suggested_next_steps?: string[];
  top_risk_factors?: Array<{ factor: string; points: number }>;
  risk_score_at_generation?: number;
  generated_by: string;
  last_generated_at: string;
}

export interface RiskFactorItem {
  name: string;
  weight: number;
  raw_value: any;
  raw_denominator: any;
  ratio: number;
  points: number;
  explanation: string;
}

export interface RiskBreakdownDetail {
  application_id: number;
  application_number: string;
  score: number;
  band: string;
  is_paused: boolean;
  is_closed: boolean;
  factors: RiskFactorItem[];
  weights: Record<string, number>;
  raw_values: Record<string, any>;
  weighted_points: Record<string, number>;
  computed_at: string;
  disclaimer: string;
}

export interface ApplicationRiskListItem {
  id: number;
  application_number: string;
  institution_id: number;
  institution_name: string;
  region_id: number;
  region_name: string;
  stage_id: number;
  stage_name: string;
  stage_code: string;
  status: string;
  case_holder: string;
  delay_risk_score: number;
  risk_band: 'LOW' | 'MEDIUM' | 'HIGH';
  is_paused: boolean;
}

export interface RiskWeightsConfig {
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  officer_capacity?: number;
  stage_baselines?: Record<string, number>;
  disclaimer?: string;
}

export interface NeedsAttentionAlert {
  alert_id: number;
  title: string;
  rule_code: string;
  rule_name: string;
  severity: string;
  status: string;
  escalation_tier: number;
  priority_score: number;
  priority_explanation: string;
  application_id?: number | null;
  application_number?: string | null;
  institution_name?: string | null;
  created_at?: string | null;
}

export interface ApplicationDetail extends ApplicationItem {
  institution: Institution;
  category: { id: number; code: string; title: string; requires_evc: boolean; requires_sac_shc: boolean };
  stage_path: StagePath;
  current_stage: Stage;
  approval_letter_data?: Record<string, any> | null;
  communications: CommunicationItem[];
  case_summary?: CaseSummaryItem | null;
  clock_segments?: ClockSegment[];
  total_aicte_hours?: number;
  total_institution_hours?: number;
}

export interface DeficiencyTag {
  code: string;
  label: string;
  description: string;
  is_active: boolean;
}

export interface ApplicationCategory {
  id: number;
  code: string;
  title: string;
  requires_evc: boolean;
  requires_sac_shc: boolean;
  description?: string;
}

export const applicationsApi = {
  list: async (params?: Record<string, any>): Promise<{ total: number; skip: number; limit: number; applications: ApplicationItem[] }> => {
    const res = await apiClient.get('/applications', { params });
    return res.data;
  },
  get: async (id: number): Promise<ApplicationDetail> => {
    const res = await apiClient.get<ApplicationDetail>(`/applications/${id}`);
    return res.data;
  },
  getTimeline: async (id: number): Promise<StageHistoryItem[]> => {
    const res = await apiClient.get<StageHistoryItem[]>(`/applications/${id}/timeline`);
    return res.data;
  },
  completeStage: async (id: number, remarks?: string): Promise<{ status: string; message: string; current_stage: string }> => {
    const res = await apiClient.post(`/applications/${id}/complete-stage`, { remarks });
    return res.data;
  },
  returnApplication: async (id: number, deficiency_tags: string[], reason: string): Promise<{ status: string; message: string; current_stage: string }> => {
    const res = await apiClient.post(`/applications/${id}/return`, { deficiency_tags, reason });
    return res.data;
  },
  recordDecision: async (id: number, decision: 'APPROVE' | 'REJECT', remarks: string): Promise<ApplicationDetail> => {
    const res = await apiClient.post(`/applications/${id}/decision`, { decision, remarks });
    return res.data;
  },
  getCommunications: async (id: number): Promise<CommunicationItem[]> => {
    const res = await apiClient.get(`/applications/${id}/communications`);
    return res.data;
  },
  markCommunicationSent: async (id: number, cid: number): Promise<CommunicationItem> => {
    const res = await apiClient.post(`/applications/${id}/communications/${cid}/mark-sent`);
    return res.data;
  },
  getCategories: async (): Promise<ApplicationCategory[]> => {
    const res = await apiClient.get('/application-categories');
    return res.data;
  },
  create: async (data: { institution_id: number; category_id: number; stage_path_id?: number }): Promise<ApplicationDetail> => {
    const res = await apiClient.post('/applications', data);
    return res.data;
  },
  advanceClock: async (hours: number): Promise<{ status: string; advanced_hours: number; simulated_time: string }> => {
    const res = await apiClient.post('/demo/advance-clock', { hours });
    return res.data;
  },
  resetClock: async (): Promise<{ status: string; simulated_time: string }> => {
    const res = await apiClient.post('/demo/reset-clock');
    return res.data;
  },
  respond: async (id: number, data: { remarks: string; document_url?: string; file_name?: string }): Promise<ApplicationDetail> => {
    const res = await apiClient.post(`/applications/${id}/institution-response`, data);
    return res.data;
  },
  close: async (id: number, data: { closure_reason: string; closure_remarks?: string }): Promise<ApplicationDetail> => {
    const res = await apiClient.post(`/applications/${id}/close`, data);
    return res.data;
  },
  getClockSegments: async (id: number): Promise<{ segments: ClockSegment[]; total_aicte_hours: number; total_institution_hours: number; current_holder: string }> => {
    const res = await apiClient.get(`/applications/${id}/clock-segments`);
    return res.data;
  },
  getSummary: async (id: number): Promise<CaseSummaryItem> => {
    const res = await apiClient.get<CaseSummaryItem>(`/applications/${id}/summary`);
    return res.data;
  },
  regenerateSummary: async (id: number): Promise<CaseSummaryItem> => {
    const res = await apiClient.post<CaseSummaryItem>(`/applications/${id}/summary/regenerate`);
    return res.data;
  },
};

export const riskApi = {
  getDetail: async (id: number): Promise<RiskBreakdownDetail> => {
    const res = await apiClient.get<RiskBreakdownDetail>(`/risk/applications/${id}`);
    return res.data;
  },
  getWeights: async (): Promise<RiskWeightsConfig> => {
    const res = await apiClient.get<RiskWeightsConfig>('/config/risk-weights');
    return res.data;
  },
  updateWeights: async (payload: { weights: Record<string, number>; thresholds?: Record<string, number>; officer_capacity?: number }): Promise<RiskWeightsConfig> => {
    const res = await apiClient.put<RiskWeightsConfig>('/config/risk-weights', payload);
    return res.data;
  },
  listApplications: async (params?: Record<string, any>): Promise<ApplicationRiskListItem[]> => {
    const res = await apiClient.get<ApplicationRiskListItem[]>('/risk/applications', { params });
    return res.data;
  },
};

// Phase 4 Alert & Escalation Interfaces
export interface ExplanationMeta {
  rule_code: string;
  entity_type: string;
  entity_id: number;
  actual_value: any;
  threshold_value: any;
  why_fired: string;
  reference_label: string;
  is_verified_clause?: boolean;
}

export interface EscalationHistoryItem {
  id: number;
  alert_id: number;
  from_tier: number;
  to_tier: number;
  target_role: string;
  recipient_user_id?: number | null;
  recipient_name?: string | null;
  reason: string;
  created_at: string;
}

export interface AlertItem {
  id: number;
  alert_rule_id: number;
  rule_code: string;
  rule_name: string;
  alert_type: string;
  severity: 'INFO' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'ACTIVE' | 'ACKNOWLEDGED' | 'SNOOZED' | 'ESCALATED' | 'RESOLVED';
  application_id?: number | null;
  application_number?: string | null;
  institution_id?: number | null;
  institution_name?: string | null;
  document_id?: number | null;
  undertaking_id?: number | null;
  recipient_user_id?: number | null;
  recipient_user_name?: string | null;
  recipient_role: string;
  title: string;
  message: string;
  explanation_meta: ExplanationMeta;
  escalation_tier: number;
  escalated_at?: string | null;
  resolved_at?: string | null;
  snoozed_until?: string | null;
  snooze_count: number;
  snooze_reason?: string | null;
  acknowledged_at?: string | null;
  acknowledged_by?: number | null;
  acknowledged_by_name?: string | null;
  acknowledgement_remarks?: string | null;
  resolved_by?: number | null;
  resolved_by_name?: string | null;
  resolution_remarks?: string | null;
  created_at: string;
  age_hours?: number | null;
  priority_score?: number | null;
  priority_explanation?: string | null;
}

export interface AlertDetail extends AlertItem {
  escalation_history: EscalationHistoryItem[];
  rule?: AlertRule | null;
}

export interface AlertSummary {
  total_open: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_level: Record<string, number>;
  by_region: Record<string, number>;
}

export interface NotificationItem {
  id: number;
  alert_id?: number | null;
  title: string;
  body: string;
  is_read: boolean;
  read_at?: string | null;
  sent_at: string;
  alert?: AlertItem | null;
}

export interface NotificationSummary {
  unread_count: number;
  notifications: NotificationItem[];
}

export interface EmailOutboxItem {
  id: number;
  recipient_email: string;
  recipient_user_id?: number | null;
  recipient_name?: string | null;
  subject: string;
  body: string;
  status: 'QUEUED' | 'SENT' | 'FAILED' | 'SUPPRESSED';
  template_code?: string | null;
  entity_type?: string | null;
  entity_id?: number | null;
  attempts: number;
  error_message?: string | null;
  created_at: string;
  sent_at?: string | null;
}

export interface EscalationRuleItem {
  id: number;
  alert_rule_id: number;
  rule_code?: string | null;
  rule_name?: string | null;
  tier_level: number;
  target_role: string;
  trigger_delay_days: number;
  action_required: string;
  created_at: string;
}

export interface RegionEscalationItem {
  region_id: number;
  region_name: string;
  l1_role: string;
  l1_officer?: string | null;
  l1_alerts_count: number;
  l2_role: string;
  l2_officer?: string | null;
  l2_alerts_count: number;
  l3_role: string;
  l3_officer?: string | null;
  l3_alerts_count: number;
}

export interface EscalationMatrix {
  regions: RegionEscalationItem[];
}

export interface SchedulerRunItem {
  id: number;
  started_at: string;
  finished_at?: string | null;
  status: string;
  rules_evaluated: number;
  alerts_created: number;
  alerts_upgraded: number;
  alerts_resolved: number;
  error_message?: string | null;
  triggered_by: string;
}

export const alertsApi = {
  list: async (params?: Record<string, any>): Promise<AlertItem[]> => {
    const res = await apiClient.get<AlertItem[]>('/alerts', { params });
    return res.data;
  },
  getSummary: async (): Promise<AlertSummary> => {
    const res = await apiClient.get<AlertSummary>('/alerts/summary');
    return res.data;
  },
  getNeedsAttentionToday: async (): Promise<NeedsAttentionAlert[]> => {
    const res = await apiClient.get<NeedsAttentionAlert[]>('/alerts/needs-attention-today');
    return res.data;
  },
  get: async (id: number): Promise<AlertDetail> => {
    const res = await apiClient.get<AlertDetail>(`/alerts/${id}`);
    return res.data;
  },
  acknowledge: async (id: number, remarks?: string): Promise<AlertItem> => {
    const res = await apiClient.post<AlertItem>(`/alerts/${id}/acknowledge`, { remarks });
    return res.data;
  },
  snooze: async (id: number, hours: number, reason: string): Promise<AlertItem> => {
    const res = await apiClient.post<AlertItem>(`/alerts/${id}/snooze`, { hours, reason });
    return res.data;
  },
  resolve: async (id: number, remarks: string): Promise<AlertItem> => {
    const res = await apiClient.post<AlertItem>(`/alerts/${id}/resolve`, { remarks });
    return res.data;
  },
  runChecksNow: async (): Promise<SchedulerRunItem> => {
    const res = await apiClient.post<SchedulerRunItem>('/alerts/run-now');
    return res.data;
  },
  getEscalationMatrix: async (): Promise<EscalationMatrix> => {
    const res = await apiClient.get<EscalationMatrix>('/escalation/matrix');
    return res.data;
  },
  generateDailyDigests: async (): Promise<{ status: string; digests_created: number }> => {
    const res = await apiClient.post<{ status: string; digests_created: number }>('/alerts/daily-digest/generate');
    return res.data;
  },
};

export const notificationsApi = {
  list: async (unreadOnly = false): Promise<NotificationSummary> => {
    const res = await apiClient.get<NotificationSummary>('/notifications', {
      params: { unread_only: unreadOnly },
    });
    return res.data;
  },
  markRead: async (id: number): Promise<{ status: string }> => {
    const res = await apiClient.post<{ status: string }>(`/notifications/${id}/read`);
    return res.data;
  },
  markAllRead: async (): Promise<{ status: string }> => {
    const res = await apiClient.post<{ status: string }>('/notifications/read-all');
    return res.data;
  },
};

export const adminApi = {
  getOutbox: async (params?: { status?: string; limit?: number }): Promise<EmailOutboxItem[]> => {
    const res = await apiClient.get<EmailOutboxItem[]>('/outbox', { params });
    return res.data;
  },
  getAlertRules: async (): Promise<AlertRule[]> => {
    const res = await apiClient.get<AlertRule[]>('/config/alert-rules');
    return res.data;
  },
  updateAlertRule: async (id: number, payload: Partial<AlertRule>): Promise<AlertRule> => {
    const res = await apiClient.put<AlertRule>(`/config/alert-rules/${id}`, payload);
    return res.data;
  },
  getEscalationRules: async (): Promise<EscalationRuleItem[]> => {
    const res = await apiClient.get<EscalationRuleItem[]>('/config/escalation-rules');
    return res.data;
  },
  updateEscalationRule: async (id: number, payload: { trigger_delay_days: number; action_required?: string }): Promise<EscalationRuleItem> => {
    const res = await apiClient.put<EscalationRuleItem>(`/config/escalation-rules/${id}`, payload);
    return res.data;
  },
};

// ============================================================================
// PHASE 5 INTERFACES & APIS: EVC, UNDERTAKINGS, DOCUMENTS, REPORTS, PORTAL
// ============================================================================

export interface UploadedFileItem {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  created_at: string;
  download_url: string;
}

export interface EvcExpert {
  id: number;
  name: string;
  designation: string;
  discipline: string;
  home_institution: string;
  city: string;
  state: string;
  region_id: number;
  is_available: boolean;
  active_visit_count: number;
}

export interface SuggestedExpert {
  expert: EvcExpert;
  rank_score: number;
  has_conflict: boolean;
  conflict_reasons: string[];
}

export interface EvcVisit {
  id: number;
  application_id: number;
  application_number: string;
  academic_year: string;
  institution_id: number;
  institution_name: string;
  institution_city?: string;
  is_new_institution: boolean;
  region_id: number;
  region_name: string;
  stage_name: string;
  status: string;
  scheduled_date?: string | null;
  scheduled_time?: string | null;
  visit_completed_at?: string | null;
  report_file_id?: number | null;
  report_file_name?: string | null;
  remarks?: string | null;
  days_waiting: number;
  panel_size: number;
  panel: EvcExpert[];
  created_at: string;
}

export const evcApi = {
  listVisits: async (params?: Record<string, any>): Promise<EvcVisit[]> => {
    const res = await apiClient.get<EvcVisit[]>('/evc/visits', { params });
    return res.data;
  },
  getVisit: async (id: number): Promise<EvcVisit> => {
    const res = await apiClient.get<EvcVisit>(`/evc/visits/${id}`);
    return res.data;
  },
  listExperts: async (params?: Record<string, any>): Promise<EvcExpert[]> => {
    const res = await apiClient.get<EvcExpert[]>('/evc/experts', { params });
    return res.data;
  },
  getSuggestedExperts: async (visitId: number): Promise<SuggestedExpert[]> => {
    const res = await apiClient.get<SuggestedExpert[]>(`/evc/visits/${visitId}/suggested-experts`);
    return res.data;
  },
  assignPanel: async (visitId: number, expertIds: number[]): Promise<EvcVisit> => {
    const res = await apiClient.post<EvcVisit>(`/evc/visits/${visitId}/assign-panel`, { expert_ids: expertIds });
    return res.data;
  },
  scheduleVisit: async (visitId: number, payload: { scheduled_date: string; scheduled_time?: string; instructions?: string }): Promise<EvcVisit> => {
    const res = await apiClient.post<EvcVisit>(`/evc/visits/${visitId}/schedule`, payload);
    return res.data;
  },
  completeVisit: async (visitId: number, visitSummary?: string): Promise<EvcVisit> => {
    const res = await apiClient.post<EvcVisit>(`/evc/visits/${visitId}/complete-visit`, { visit_summary: visitSummary });
    return res.data;
  },
  uploadReport: async (visitId: number, formData: FormData): Promise<EvcVisit> => {
    const res = await apiClient.post<EvcVisit>(`/evc/visits/${visitId}/upload-report`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  closeVisit: async (visitId: number, remarks?: string): Promise<EvcVisit> => {
    const res = await apiClient.post<EvcVisit>(`/evc/visits/${visitId}/close`, { remarks });
    return res.data;
  },
};

export interface UndertakingHistoryItem {
  id: number;
  action: string;
  from_status?: string | null;
  to_status: string;
  actor_name: string;
  actor_role: string;
  remarks?: string | null;
  created_at: string;
}

export interface UndertakingItem {
  id: number;
  application_id: number;
  application_number: string;
  institution_id: number;
  institution_name: string;
  region_id: number;
  region_name: string;
  title: string;
  description: string;
  condition_clause?: string | null;
  due_date: string;
  status: string;
  rejection_count: number;
  latest_rejection_remark?: string | null;
  is_escalated: boolean;
  escalation_reason?: string | null;
  verified_at?: string | null;
  verified_by_name?: string | null;
  days_remaining: number;
  is_overdue: boolean;
  evidence_files: UploadedFileItem[];
  history: UndertakingHistoryItem[];
  created_at: string;
}

export const undertakingsApi = {
  list: async (params?: Record<string, any>): Promise<UndertakingItem[]> => {
    const res = await apiClient.get<UndertakingItem[]>('/undertakings', { params });
    return res.data;
  },
  get: async (id: number): Promise<UndertakingItem> => {
    const res = await apiClient.get<UndertakingItem>(`/undertakings/${id}`);
    return res.data;
  },
  uploadEvidence: async (id: number, formData: FormData): Promise<UndertakingItem> => {
    const res = await apiClient.post<UndertakingItem>(`/undertakings/${id}/upload-evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  verify: async (id: number, payload: { action: 'VERIFIED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE'; remarks: string }): Promise<UndertakingItem> => {
    const res = await apiClient.post<UndertakingItem>(`/undertakings/${id}/verify`, payload);
    return res.data;
  },
};

export interface DocumentVersionItem {
  id: number;
  version: number;
  status: string;
  expiry_date: string;
  file_id?: number | null;
  file_name?: string | null;
  file_size?: number | null;
  download_url?: string | null;
  remarks?: string | null;
  created_at: string;
  verified_at?: string | null;
  verified_by_name?: string | null;
}

export interface DocumentItem {
  id: number;
  application_id: number;
  application_number: string;
  institution_id: number;
  institution_name: string;
  region_id: number;
  region_name: string;
  document_type: string;
  title: string;
  version: number;
  status: string;
  issue_date?: string | null;
  expiry_date: string;
  days_to_expiry: number;
  urgency: 'EXPIRED' | 'CRITICAL' | 'EXPIRING_SOON' | 'VALID' | 'PENDING_VERIFICATION';
  file_id?: number | null;
  file_name?: string | null;
  file_size?: number | null;
  download_url?: string | null;
  remarks?: string | null;
  superseded_by_id?: number | null;
  versions: DocumentVersionItem[];
  created_at: string;
}

export const documentsApi = {
  list: async (params?: Record<string, any>): Promise<DocumentItem[]> => {
    const res = await apiClient.get<DocumentItem[]>('/documents', { params });
    return res.data;
  },
  get: async (id: number): Promise<DocumentItem> => {
    const res = await apiClient.get<DocumentItem>(`/documents/${id}`);
    return res.data;
  },
  uploadRenewal: async (id: number, formData: FormData): Promise<DocumentItem> => {
    const res = await apiClient.post<DocumentItem>(`/documents/${id}/upload-renewal`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  verifyRenewal: async (id: number, payload: { action: 'APPROVE' | 'REJECT'; remarks: string; approved_expiry_date?: string }): Promise<DocumentItem> => {
    const res = await apiClient.post<DocumentItem>(`/documents/${id}/verify-renewal`, payload);
    return res.data;
  },
};

export interface PendencyReportData {
  total_pending: number;
  total_overdue: number;
  with_aicte_count: number;
  with_institution_count: number;
  by_stage: Array<{ stage: string; count: number; with_aicte: number; with_institution: number; avg_days: number; overdue_count: number }>;
  by_region: Array<{ region: string; count: number; with_aicte: number; with_institution: number; avg_days: number; overdue_count: number }>;
  by_officer: Array<{ officer: string; role: string; count: number; overdue_count: number }>;
}

export interface EvcReportData {
  total_visits: number;
  average_turnaround_days: number;
  by_status: Array<{ status: string; count: number }>;
  by_region: Array<{ region: string; count: number; completed: number }>;
}

export interface UndertakingReportData {
  total_undertakings: number;
  verified_count: number;
  overdue_count: number;
  escalated_count: number;
  compliance_rate_pct: number;
  by_status: Array<{ status: string; count: number }>;
  by_region: Array<{ region: string; total: number; compliant: number; overdue: number }>;
}

export interface DocumentReportData {
  total_documents: number;
  valid_count: number;
  expired_count: number;
  expiring_soon_count: number;
  renewal_submitted_count: number;
  superseded_count: number;
  by_status: Array<{ status: string; count: number }>;
  by_type: Array<{ type: string; total: number; valid: number; expiring: number; expired: number }>;
}

export interface RegionalPerformanceData {
  regions: Array<{
    region_id: number;
    region_code: string;
    region_name: string;
    headquarters: string;
    total_applications: number;
    with_aicte_count: number;
    with_institution_count: number;
    closed_count: number;
    avg_days_per_stage: number;
    sla_breach_rate_pct: number;
    alerts_raised: number;
    alerts_resolved: number;
  }>;
}

export interface OverdueItem {
  id: string;
  type: 'APPLICATION' | 'EVC_VISIT' | 'UNDERTAKING' | 'DOCUMENT';
  reference_number: string;
  title: string;
  institution_id: number;
  institution_name: string;
  region_id?: number | null;
  region_name: string;
  officer_name: string;
  case_holder: string;
  due_date: string;
  days_overdue: number;
  escalation_level: number;
  linked_alert_id?: number | null;
  linked_alert_severity?: string | null;
}

export interface OverdueCasesReportData {
  summary: {
    total_overdue: number;
    applications_overdue: number;
    evc_visits_overdue: number;
    undertakings_overdue: number;
    documents_overdue: number;
    with_aicte_count: number;
    with_institution_count: number;
  };
  items: OverdueItem[];
}

export interface InstitutionHealthDossier {
  institution: Institution;
  health_score: number;
  health_rating: string;
  stats: {
    total_applications: number;
    open_undertakings: number;
    overdue_undertakings: number;
    expired_documents: number;
    expiring_soon_documents: number;
    open_alerts: number;
    critical_alerts: number;
    complaint_free_status: boolean;
  };
  applications: ApplicationItem[];
  undertakings: UndertakingItem[];
  documents: DocumentItem[];
  open_alerts: AlertItem[];
}

export interface CommitteeAssignment {
  id: number;
  application_id: number;
  application_number: string;
  institution_name: string;
  category_title: string;
  committee_type: 'EVC' | 'SAC' | 'SHC';
  user_id: number;
  meeting_date?: string | null;
  venue?: string | null;
  status: string;
}

export interface CommitteeObservation {
  id: number;
  application_id: number;
  user_id: number;
  member_name: string;
  committee_type: string;
  observations: string;
  recommendation: 'RECOMMEND_APPROVAL' | 'RECOMMEND_REJECTION' | 'RECOMMEND_RE_INSPECTION' | 'NEEDS_CLARIFICATION';
  created_at: string;
}

export const committeeApi = {
  getMyCases: async (): Promise<CommitteeAssignment[]> => {
    const res = await apiClient.get<CommitteeAssignment[]>('/committee/my-cases');
    return res.data;
  },
  getObservations: async (applicationId: number): Promise<CommitteeObservation[]> => {
    const res = await apiClient.get<CommitteeObservation[]>(`/committee/cases/${applicationId}/observations`);
    return res.data;
  },
  addObservation: async (applicationId: number, data: { committee_type: string; observations: string; recommendation: string }): Promise<CommitteeObservation> => {
    const res = await apiClient.post<CommitteeObservation>(`/committee/cases/${applicationId}/observations`, data);
    return res.data;
  },
};

export interface HolidayItem {
  id: number;
  holiday_date: string;
  name: string;
  holiday_type: string;
  region_id?: number | null;
  region_name?: string | null;
  created_at: string;
}

export const holidaysApi = {
  getHolidays: async (year?: number): Promise<HolidayItem[]> => {
    const res = await apiClient.get<HolidayItem[]>('/holidays', { params: { year } });
    return res.data;
  },
  addHoliday: async (data: { holiday_date: string; name: string; holiday_type?: string; region_id?: number }): Promise<HolidayItem> => {
    const res = await apiClient.post<HolidayItem>('/holidays', data);
    return res.data;
  },
  deleteHoliday: async (id: number): Promise<void> => {
    await apiClient.delete(`/holidays/${id}`);
  },
  getWeekendConfig: async (): Promise<{ weekend_days: number[]; weekend_names: string[] }> => {
    const res = await apiClient.get('/holidays/config/weekends');
    return res.data;
  },
  updateWeekendConfig: async (weekend_days: number[]): Promise<any> => {
    const res = await apiClient.post('/holidays/config/weekends', { weekend_days });
    return res.data;
  },
};

export const reportsApi = {
  getPendency: async (regionId?: number): Promise<PendencyReportData> => {
    const res = await apiClient.get<PendencyReportData>('/reports/pendency', { params: { region_id: regionId } });
    return res.data;
  },
  getEvc: async (regionId?: number): Promise<EvcReportData> => {
    const res = await apiClient.get<EvcReportData>('/reports/evc', { params: { region_id: regionId } });
    return res.data;
  },
  getUndertakings: async (regionId?: number): Promise<UndertakingReportData> => {
    const res = await apiClient.get<UndertakingReportData>('/reports/undertakings', { params: { region_id: regionId } });
    return res.data;
  },
  getDocuments: async (regionId?: number): Promise<DocumentReportData> => {
    const res = await apiClient.get<DocumentReportData>('/reports/documents', { params: { region_id: regionId } });
    return res.data;
  },
  getRegionalPerformance: async (): Promise<RegionalPerformanceData> => {
    const res = await apiClient.get<RegionalPerformanceData>('/reports/regional-performance');
    return res.data;
  },
  getOverdue: async (params?: Record<string, any>): Promise<OverdueCasesReportData> => {
    const res = await apiClient.get<OverdueCasesReportData>('/reports/overdue', { params });
    return res.data;
  },
  getInstitutionHealth: async (institutionId: number): Promise<InstitutionHealthDossier> => {
    const res = await apiClient.get<InstitutionHealthDossier>(`/reports/institutions/${institutionId}/health`);
    return res.data;
  },
  getCsvExportUrl: (reportType: string, regionId?: number): string => {
    const regParam = regionId ? `&region_id=${regionId}` : '';
    return `${API_BASE_URL}/reports/export/csv?report_type=${reportType}${regParam}`;
  },
  getPdfExportUrl: (reportType: string, regionId?: number): string => {
    const regParam = regionId ? `&region_id=${regionId}` : '';
    return `${API_BASE_URL}/reports/export/pdf?report_type=${reportType}${regParam}`;
  },
};

export const filesApi = {
  getDownloadUrl: (fileId: number): string => {
    return `${API_BASE_URL}/files/${fileId}/download`;
  },
  downloadFile: async (fileId: number, filename?: string) => {
    const res = await apiClient.get(`/files/${fileId}/download`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || `file_${fileId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  },
};

export const auditApi = {
  search: async (params?: Record<string, any>) => {
    const res = await apiClient.get('/audit', { params });
    return res.data;
  },
  verifyIntegrity: async () => {
    const res = await apiClient.get('/audit/verify-integrity');
    return res.data;
  },
  exportCsvUrl: (params?: Record<string, any>) => {
    const query = new URLSearchParams(params as any).toString();
    return `${API_BASE_URL}/audit/export-csv?${query}`;
  },
};

export const retentionApi = {
  getPolicy: async () => {
    const res = await apiClient.get('/retention/policy');
    return res.data;
  },
  updatePolicy: async (policy: Record<string, number>) => {
    const res = await apiClient.put('/retention/policy', policy);
    return res.data;
  },
  getPreview: async () => {
    const res = await apiClient.get('/retention/preview');
    return res.data;
  },
  exportPreviewCsvUrl: () => {
    return `${API_BASE_URL}/retention/preview/csv`;
  },
};

export const integrationApi = {
  getStatus: async () => {
    const res = await apiClient.get('/integration/status');
    return res.data;
  },
  lookupInstitution: async (aicteId: string) => {
    const res = await apiClient.get(`/integration/institution/${aicteId}`);
    return res.data;
  },
  pushStatus: async (payload: { application_number: string; new_status: string; remarks?: string }) => {
    const res = await apiClient.post('/integration/sync/status', payload);
    return res.data;
  },
  getLogs: async (limit = 50) => {
    const res = await apiClient.get('/integration/logs', { params: { limit } });
    return res.data;
  },
};


