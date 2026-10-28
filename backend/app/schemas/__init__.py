from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
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
    approval_letter_ref: Optional[str] = None


class ApplicationDetailOut(ApplicationOut):
    institution: InstitutionOut
    category: ApplicationCategoryOut
    stage_path: StagePathOut
    current_stage: StageOut
    approval_letter_data: Optional[Dict[str, Any]] = None
    communications: List[CommunicationOut] = []
    case_summary: Optional[CaseSummaryOut] = None

