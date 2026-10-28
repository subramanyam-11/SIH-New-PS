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
  risk_factors: string[];
  days_in_stage: number;
  days_remaining: number;
  percentage_elapsed: number;
  ageing_bucket: 'ON_TIME' | 'NEAR_DUE' | 'OVERDUE' | 'COMPLETED';
  escalation_required: boolean;
  escalation_reason?: string | null;
  approval_letter_ref?: string | null;
  created_at: string;
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
  generated_by: string;
  last_generated_at: string;
}

export interface ApplicationDetail extends ApplicationItem {
  institution: Institution;
  category: { id: number; code: string; title: string; requires_evc: boolean; requires_sac_shc: boolean };
  stage_path: StagePath;
  current_stage: Stage;
  approval_letter_data?: Record<string, any> | null;
  communications: CommunicationItem[];
  case_summary?: CaseSummaryItem | null;
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

