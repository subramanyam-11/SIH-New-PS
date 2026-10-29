from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime, date
from app.models import UserRoleEnum


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    full_name: str
    region_id: Optional[int] = None
    institution_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DemoLoginRequest(BaseModel):
    role: UserRoleEnum
    email: Optional[str] = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    description: Optional[str] = None


class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    headquarters: str
    states_covered: List[str]


class InstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aicte_id: str
    name: str
    institution_type: str
    category: str
    region_id: int
    city: str
    state: str
    pincode: str
    primary_email: str
    primary_phone: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: RoleOut
    region_id: Optional[int] = None
    institution_id: Optional[int] = None
    is_active: bool
    last_login: Optional[datetime] = None


class UserScopeOut(BaseModel):
    user_id: int
    full_name: str
    role: str
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    is_national: bool
    is_regional: bool
    is_institution: bool
    allowed_screens: List[str]


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    default_sla_days: int
    responsible_role: str
    description: Optional[str] = None


class StagePathOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str] = None
    stage_sequence: List[str]
    is_active: bool


class AlertRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    alert_type: str
    entity_type: str
    condition_logic: Dict[str, Any]
    severity: str
    aph_reference_clause: Optional[str] = None
    template_message: str
    is_active: bool


class SystemConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_key: str
    config_value: Any
    description: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str
    database: str
    environment: str
    demo_mode: bool
    timestamp: datetime


# --- PHASE 3 SCHEMAS ---

class ApplicationCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    requires_evc: bool
    requires_sac_shc: bool
    description: Optional[str] = None


class ApplicationCreate(BaseModel):
    institution_id: int
    category_id: int
    stage_path_id: Optional[int] = None
    academic_year: Optional[str] = "2026-2027"


class StageTransitionRequest(BaseModel):
    remarks: Optional[str] = None


class ApplicationReturnRequest(BaseModel):
    deficiency_tags: List[str]
    reason: str


class ApplicationDecisionRequest(BaseModel):
    decision: str  # 'APPROVE' or 'REJECT'
    remarks: str


class AdvanceClockRequest(BaseModel):
    hours: float


class CommunicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    template_code: str
    subject: str
    body: str
    recipient_email: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime] = None


class StageHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    from_stage_id: Optional[int] = None
    to_stage_id: int
    from_stage_name: Optional[str] = None
    to_stage_name: Optional[str] = None
    action_taken: str
    actor_id: int
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    status: str
    reason: Optional[str] = None
    deficiency_tags: Optional[List[str]] = None
    entered_at: datetime
    completed_at: Optional[datetime] = None
    duration_hours: Optional[float] = None


class CaseSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    executive_summary: str
    key_findings: List[str]
    compliance_flags: List[str]
    risk_assessment: Optional[str] = None
    source_label: Optional[str] = "Template summary"
    input_hash: Optional[str] = None
    timeline_highlights: Optional[List[Dict[str, Any]]] = []
    pending_items: Optional[List[Dict[str, Any]]] = []
    upcoming_deadlines: Optional[List[Dict[str, Any]]] = []
    suggested_next_steps: Optional[List[str]] = []
    top_risk_factors: Optional[List[Dict[str, Any]]] = []
    risk_score_at_generation: Optional[float] = None
    generated_by: str
    last_generated_at: datetime


class DeficiencyTagOut(BaseModel):
    code: str
    label: str
    description: str
    requires_remark: Optional[bool] = False


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_number: str
    academic_year: str
    institution_id: int
    institution_name: Optional[str] = None
    institution_aicte_id: Optional[str] = None
    category_id: int
    category_title: Optional[str] = None
    stage_path_id: int
    stage_path_name: Optional[str] = None
    stage_path_code: Optional[str] = None
    current_stage_id: int
    current_stage_code: Optional[str] = None
    current_stage_name: Optional[str] = None
    responsible_role: Optional[str] = None
    status: str
    region_id: int
    region_name: Optional[str] = None
    assigned_officer_id: Optional[int] = None
    assigned_officer_name: Optional[str] = None

    stage_entered_at: datetime
    stage_due_date: datetime
    days_in_stage: Optional[float] = None
    days_remaining: Optional[float] = None
    ageing_bucket: Optional[str] = "ON_TIME"  # 'ON_TIME', 'NEAR_DUE', 'OVERDUE'
    revert_count: int = 0
    escalation_required: bool = False
    escalation_reason: Optional[str] = None

    delay_risk_score: float = 0.0
    risk_band: Optional[str] = "LOW"
    approval_letter_ref: Optional[str] = None

    # Phase 6 Fair Pendency Clock & Closed State fields
    case_holder: str = "WITH_AICTE"
    closed_at: Optional[datetime] = None
    closure_reason: Optional[str] = None
    closure_remarks: Optional[str] = None
    is_paused: Optional[bool] = False
    total_aicte_days: Optional[float] = None
    total_institution_days: Optional[float] = None


class ClockSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    stage_id: int
    stage_name: Optional[str] = None
    holder: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_hours: Optional[float] = None
    reason: Optional[str] = None


class CommitteeObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    committee_type: str
    user_id: int
    member_name: str
    observation_text: str
    recommendation: str
    created_at: datetime


class ApplicationDetailOut(ApplicationOut):
    institution: InstitutionOut
    category: ApplicationCategoryOut
    stage_path: StagePathOut
    current_stage: StageOut
    approval_letter_data: Optional[Dict[str, Any]] = None
    communications: List[CommunicationOut] = []
    case_summary: Optional[CaseSummaryOut] = None
    clock_segments: List[ClockSegmentOut] = []
    committee_observations: List[CommitteeObservationOut] = []


# --- PHASE 4 SCHEMAS ---

class EscalationHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: int
    from_tier: int
    to_tier: int
    target_role: str
    recipient_user_id: Optional[int] = None
    recipient_name: Optional[str] = None
    reason: str
    escalated_by: Optional[int] = None
    escalated_by_name: Optional[str] = None
    created_at: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_rule_id: int
    rule_code: str
    rule_name: str
    alert_type: str
    severity: str
    status: str
    application_id: Optional[int] = None
    application_number: Optional[str] = None
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    document_id: Optional[int] = None
    undertaking_id: Optional[int] = None
    recipient_user_id: Optional[int] = None
    recipient_user_name: Optional[str] = None
    recipient_role: str
    title: str
    message: str
    explanation_meta: Dict[str, Any]
    escalation_tier: int
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    snooze_count: int = 0
    snooze_reason: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    acknowledged_by_name: Optional[str] = None
    acknowledgement_remarks: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_by_name: Optional[str] = None
    resolution_remarks: Optional[str] = None
    created_at: datetime
    age_hours: Optional[float] = None
    priority_score: Optional[float] = 0.0
    priority_explanation: Optional[str] = None


class AlertDetailOut(AlertOut):
    escalation_history: List[EscalationHistoryOut] = []
    rule: Optional[AlertRuleOut] = None


class AlertAcknowledgeRequest(BaseModel):
    remarks: Optional[str] = None


class AlertSnoozeRequest(BaseModel):
    hours: float  # e.g. 24 or 48
    reason: str   # mandatory


class AlertResolveRequest(BaseModel):
    remarks: str  # mandatory


class AlertSummaryOut(BaseModel):
    total_open: int
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    by_level: Dict[str, int]
    by_region: Dict[str, int]


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: Optional[int] = None
    title: str
    body: str
    is_read: bool
    read_at: Optional[datetime] = None
    sent_at: datetime
    alert: Optional[AlertOut] = None


class NotificationSummaryOut(BaseModel):
    unread_count: int
    notifications: List[NotificationOut]


class EmailOutboxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_email: str
    recipient_user_id: Optional[int] = None
    recipient_name: Optional[str] = None
    subject: str
    body: str
    status: str
    template_code: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    attempts: int
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None


class EscalationRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_rule_id: int
    rule_code: Optional[str] = None
    rule_name: Optional[str] = None
    tier_level: int
    target_role: str
    trigger_delay_days: int
    action_required: str
    created_at: datetime


class EscalationRuleUpdate(BaseModel):
    trigger_delay_days: int
    action_required: Optional[str] = None


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    condition_logic: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None
    template_message: Optional[str] = None
    aph_reference_clause: Optional[str] = None


class RegionEscalationItem(BaseModel):
    region_id: int
    region_name: str
    l1_role: str
    l1_officer: Optional[str] = None
    l1_alerts_count: int = 0
    l2_role: str
    l2_officer: Optional[str] = None
    l2_alerts_count: int = 0
    l3_role: str
    l3_officer: Optional[str] = None
    l3_alerts_count: int = 0


class EscalationMatrixOut(BaseModel):
    regions: List[RegionEscalationItem]


class SchedulerRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    rules_evaluated: int
    alerts_created: int
    alerts_upgraded: int
    alerts_resolved: int
    status: str
    triggered_by: str
    details: Dict[str, Any]


# --- PHASE 5 SCHEMAS ---

class UploadedFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_filename: str
    file_size_bytes: int
    mime_type: str
    checksum_sha256: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    uploaded_by: Optional[int] = None
    created_at: datetime


class EvcExpertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    designation: str
    discipline: str
    region: str
    home_institution: str
    home_city: str
    max_concurrent_visits: int
    active_visits_count: int
    is_available: bool


class EvcExpertConflictInfo(BaseModel):
    has_conflict: bool
    reasons: List[str]


class SuggestedExpertOut(BaseModel):
    expert: EvcExpertOut
    score: float
    rank: int
    conflict_info: EvcExpertConflictInfo


class EvcVisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    application_number: Optional[str] = None
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    institution_city: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    is_new_institution: bool = False
    stage_id: int
    status: str
    assigned_experts: Optional[List[Dict[str, Any]]] = None
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[str] = None
    completed_at: Optional[datetime] = None
    visit_summary: Optional[str] = None
    report_file_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    days_waiting: float = 0.0
    created_at: datetime


class EvcPanelAssignRequest(BaseModel):
    expert_ids: List[int]


class EvcScheduleRequest(BaseModel):
    scheduled_date: date
    scheduled_time: Optional[str] = "10:00 AM"


class EvcVisitDoneRequest(BaseModel):
    visit_summary: str


class EvcCloseRequest(BaseModel):
    remarks: Optional[str] = None


class UndertakingEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    undertaking_id: int
    file_id: Optional[int] = None
    file_name: Optional[str] = None
    file_url: Optional[str] = None
    comments: Optional[str] = None
    uploaded_by: int
    uploaded_by_name: Optional[str] = None
    uploaded_at: datetime


class UndertakingHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    undertaking_id: int
    from_status: Optional[str] = None
    to_status: str
    action: str
    remarks: Optional[str] = None
    actor_id: int
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    created_at: datetime


class UndertakingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    application_number: Optional[str] = None
    institution_id: int
    institution_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    clause_number: Optional[str] = None
    title: str
    description: str
    due_date: date
    status: str
    is_overdue: bool = False
    days_until_due: Optional[int] = None
    compliance_evidence_url: Optional[str] = None
    remarks: Optional[str] = None
    rejection_count: int = 0
    escalated_to_tier: Optional[int] = None
    escalation_reason: Optional[str] = None
    created_at: datetime
    evidences: List[UndertakingEvidenceOut] = []
    history: List[UndertakingHistoryOut] = []


class UndertakingVerifyRequest(BaseModel):
    action: str  # 'VERIFIED', 'REJECTED', 'NEEDS_MORE_EVIDENCE'
    remarks: Optional[str] = None


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type: str
    title: str
    document_number: Optional[str] = None
    file_id: Optional[int] = None
    file_name: Optional[str] = None
    version_number: int = 1
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    verified_by_name: Optional[str] = None
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    institution_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    application_id: Optional[int] = None
    document_type: str
    title: str
    document_number: Optional[str] = None
    file_id: Optional[int] = None
    file_name: Optional[str] = None
    version_number: int = 1
    previous_version_id: Optional[int] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    verified_by: Optional[int] = None
    verified_by_name: Optional[str] = None
    verification_remarks: Optional[str] = None
    verified_at: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    urgency_bucket: str = "VALID"
    history: List[DocumentVersionOut] = []


class DocumentVerifyRenewalRequest(BaseModel):
    approved: Optional[bool] = None
    action: Optional[str] = None
    remarks: Optional[str] = None
    approved_expiry_date: Optional[date] = None

    @property
    def is_approved(self) -> bool:
        if self.approved is not None:
            return self.approved
        if self.action:
            return self.action.upper() in ["APPROVE", "APPROVED", "VERIFIED"]
        return False


# --- PHASE 6 (v2 ALIGNMENT) SCHEMAS ---

class InstitutionResponseRequest(BaseModel):
    remarks: str
    file_id: Optional[int] = None


class CloseApplicationRequest(BaseModel):
    closure_reason: str
    closure_remarks: Optional[str] = None


class HolidayCreate(BaseModel):
    date: date
    name: str
    region_id: Optional[int] = None
    holiday_type: Optional[str] = "NATIONAL"


class HolidayUpdate(BaseModel):
    date: Optional[date] = None
    name: Optional[str] = None
    region_id: Optional[int] = None
    holiday_type: Optional[str] = None


class HolidayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    name: str
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    holiday_type: str
    created_at: datetime


class CommitteeObservationCreate(BaseModel):
    committee_type: str
    observation_text: str
    recommendation: str  # RECOMMEND_APPROVAL, RECOMMEND_REJECTION, RECOMMEND_RE_INSPECTION, NEEDS_CLARIFICATION


class CommitteeAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    application_number: Optional[str] = None
    institution_name: Optional[str] = None
    committee_type: str
    user_id: int
    assigned_at: datetime
    status: str
    notes: Optional[str] = None
    observations: List[CommitteeObservationOut] = []


class OverdueCasesReportOut(BaseModel):
    summary: Dict[str, Any]
    items: List[Dict[str, Any]]


# --- PHASE 7 SCHEMAS ---

class RiskWeightsUpdate(BaseModel):
    weights: Dict[str, int]
    thresholds: Optional[Dict[str, int]] = None
    officer_capacity: Optional[int] = None


class RiskWeightsOut(BaseModel):
    weights: Dict[str, int]
    thresholds: Dict[str, int]
    officer_capacity: int
    stage_baselines: Dict[str, float]
    disclaimer: str


class RiskFactorOut(BaseModel):
    name: str
    weight: int
    raw_value: Any
    raw_denominator: Any
    ratio: float
    points: float
    explanation: str


class ApplicationRiskDetailOut(BaseModel):
    application_id: int
    application_number: str
    score: float
    band: str
    is_paused: bool
    is_closed: bool
    factors: List[RiskFactorOut]
    weights: Dict[str, int]
    raw_values: Dict[str, Any]
    weighted_points: Dict[str, float]
    computed_at: datetime
    disclaimer: str


class ApplicationRiskListItemOut(BaseModel):
    id: int
    application_number: str
    institution_id: int
    institution_name: str
    region_id: int
    region_name: str
    stage_id: int
    stage_name: str
    stage_code: str
    status: str
    case_holder: str
    delay_risk_score: float
    risk_band: str
    is_paused: bool


class WhatIfSimulateRequest(BaseModel):
    region_id: Optional[int] = None
    extra_visits_per_week: int = 0
    extra_staffing_capacity: int = 0
    horizon_weeks: int = 4


class NeedsAttentionAlertOut(BaseModel):
    alert_id: int
    title: str
    rule_code: str
    rule_name: str
    severity: str
    status: str
    escalation_tier: int
    priority_score: float
    priority_explanation: str
    application_id: Optional[int] = None
    application_number: Optional[str] = None
    institution_name: Optional[str] = None
    created_at: Optional[str] = None




