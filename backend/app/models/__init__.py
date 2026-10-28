from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, Float,
    ForeignKey, ARRAY, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


# --- ENUMS matching schema.sql ---

class UserRoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    SCRUTINY_OFFICER = "SCRUTINY_OFFICER"
    EVC_COORDINATOR = "EVC_COORDINATOR"
    REGIONAL_HEAD = "REGIONAL_HEAD"
    COMPETENT_AUTHORITY = "COMPETENT_AUTHORITY"
    INSTITUTION_USER = "INSTITUTION_USER"


class ApplicationStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class StageStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REVERTED = "REVERTED"
    SKIPPED = "SKIPPED"


class EvcStatusEnum(str, enum.Enum):
    PENDING_SCHEDULE = "PENDING_SCHEDULE"
    SCHEDULED = "SCHEDULED"
    VISIT_COMPLETED = "VISIT_COMPLETED"
    REPORT_SUBMITTED = "REPORT_SUBMITTED"
    CANCELLED = "CANCELLED"


class UndertakingStatusEnum(str, enum.Enum):
    PENDING_SUBMISSION = "PENDING_SUBMISSION"
    UNDER_VERIFICATION = "UNDER_VERIFICATION"
    COMPLIED = "COMPLIED"
    OVERDUE = "OVERDUE"
    DEFAULTED = "DEFAULTED"


class DocumentTypeEnum(str, enum.Enum):
    LAND_LEASE_DEED = "LAND_LEASE_DEED"
    BUILDING_PLAN_APPROVAL = "BUILDING_PLAN_APPROVAL"
    FIRE_SAFETY_NOC = "FIRE_SAFETY_NOC"
    OCCUPANCY_CERTIFICATE = "OCCUPANCY_CERTIFICATE"
    AICTE_FDR_GUARANTEE = "AICTE_FDR_GUARANTEE"
    AFFILIATING_UNIVERSITY_NOC = "AFFILIATING_UNIVERSITY_NOC"


class DocumentStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RENEWAL_SUBMITTED = "RENEWAL_SUBMITTED"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class AlertTypeEnum(str, enum.Enum):
    NEAR_BREACH = "NEAR_BREACH"
    OVERDUE = "OVERDUE"
    EVC_UNSCHEDULED = "EVC_UNSCHEDULED"
    UNDERTAKING_DUE = "UNDERTAKING_DUE"
    DOCUMENT_EXPIRING = "DOCUMENT_EXPIRING"
    DOCUMENT_EXPIRED = "DOCUMENT_EXPIRED"
    MULTIPLE_REVERTS = "MULTIPLE_REVERTS"


class AlertSeverityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class NotificationChannelEnum(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"


# --- MODELS ---

class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    headquarters = Column(String(100), nullable=False)
    states_covered = Column(ARRAY(Text), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    institutions = relationship("Institution", back_populates="region")
    users = relationship("User", back_populates="region")
    applications = relationship("Application", back_populates="region")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(SQLEnum(UserRoleEnum, name="user_role_enum"), unique=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    users = relationship("User", back_populates="role")


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    aicte_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    institution_type = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(20), nullable=False)
    primary_email = Column(String(150), nullable=False)
    primary_phone = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    region = relationship("Region", back_populates="institutions")
    users = relationship("User", back_populates="institution")
    applications = relationship("Application", back_populates="institution")
    documents = relationship("Document", back_populates="institution")
    undertakings = relationship("Undertaking", back_populates="institution")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    role = relationship("Role", back_populates="users")
    region = relationship("Region", back_populates="users")
    institution = relationship("Institution", back_populates="users")


class ApplicationCategory(Base):
    __tablename__ = "application_categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    title = Column(String(150), nullable=False)
    requires_evc = Column(Boolean, default=False)
    requires_sac_shc = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class StagePath(Base):
    __tablename__ = "stage_paths"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    stage_sequence = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Stage(Base):
    __tablename__ = "stages"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    default_sla_days = Column(Integer, nullable=False)
    responsible_role = Column(SQLEnum(UserRoleEnum, name="user_role_enum"), nullable=False)
    description = Column(Text, nullable=True)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    application_number = Column(String(50), unique=True, nullable=False, index=True)
    academic_year = Column(String(20), default="2026-2027", nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("application_categories.id"), nullable=False)
    stage_path_id = Column(Integer, ForeignKey("stage_paths.id"), nullable=False)
    current_stage_id = Column(Integer, ForeignKey("stages.id"), nullable=False, index=True)
    status = Column(SQLEnum(ApplicationStatusEnum, name="application_status_enum"), default=ApplicationStatusEnum.IN_PROGRESS, nullable=False, index=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    
    stage_entered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    stage_due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    revert_count = Column(Integer, default=0)
    delay_risk_score = Column(Float, default=0.0)
    risk_factors = Column(JSONB, default=list)

    # Phase 3 additions:
    approval_letter_ref = Column(String(100), nullable=True)
    approval_letter_data = Column(JSONB, nullable=True)
    escalation_required = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    institution = relationship("Institution", back_populates="applications")
    region = relationship("Region", back_populates="applications")
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
    category = relationship("ApplicationCategory")
    stage_path = relationship("StagePath")
    current_stage = relationship("Stage")
    stage_history = relationship("StageHistory", back_populates="application", cascade="all, delete-orphan", order_by="StageHistory.entered_at")
    communications = relationship("ApplicationCommunication", back_populates="application", cascade="all, delete-orphan", order_by="ApplicationCommunication.created_at.desc()")
    case_summary = relationship("CaseSummary", back_populates="application", uselist=False, cascade="all, delete-orphan")


class StageHistory(Base):
    __tablename__ = "stage_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    from_stage_id = Column(Integer, ForeignKey("stages.id"), nullable=True)
    to_stage_id = Column(Integer, ForeignKey("stages.id"), nullable=False)
    action_taken = Column(String(100), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SQLEnum(StageStatusEnum, name="stage_status_enum"), nullable=False)
    reason = Column(Text, nullable=True)
    deficiency_tags = Column(ARRAY(Text), nullable=True)
    entered_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    duration_hours = Column(Float, nullable=True)
    metadata_info = Column("metadata", JSONB, default=dict)

    application = relationship("Application", back_populates="stage_history")
    actor = relationship("User", foreign_keys=[actor_id])
    from_stage = relationship("Stage", foreign_keys=[from_stage_id])
    to_stage = relationship("Stage", foreign_keys=[to_stage_id])


class ApplicationCommunication(Base):
    __tablename__ = "application_communications"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    template_code = Column(String(50), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    recipient_email = Column(String(150), nullable=False)
    status = Column(String(20), default="DRAFT", nullable=False, index=True) # DRAFT, SENT
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    sent_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    application = relationship("Application", back_populates="communications")
    sender = relationship("User", foreign_keys=[sent_by])


class EvcVisit(Base):
    __tablename__ = "evc_visits"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    status = Column(SQLEnum(EvcStatusEnum, name="evc_status_enum"), default=EvcStatusEnum.PENDING_SCHEDULE, nullable=False)
    coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scheduled_date = Column(Date, nullable=True)
    visit_type = Column(String(50), default="PHYSICAL")
    committee_chair = Column(String(150), nullable=True)
    committee_experts = Column(JSONB, default=list)
    visit_completed_at = Column(DateTime(timezone=True), nullable=True)
    report_uploaded_at = Column(DateTime(timezone=True), nullable=True)
    report_file_url = Column(String(255), nullable=True)
    outcome_recommendation = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Undertaking(Base):
    __tablename__ = "undertakings"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    condition_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(SQLEnum(UndertakingStatusEnum, name="undertaking_status_enum"), default=UndertakingStatusEnum.PENDING_SUBMISSION, nullable=False, index=True)
    assigned_verifier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    institution = relationship("Institution", back_populates="undertakings")


class UndertakingEvidence(Base):
    __tablename__ = "undertaking_evidence"

    id = Column(Integer, primary_key=True, index=True)
    undertaking_id = Column(Integer, ForeignKey("undertakings.id"), nullable=False)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(255), nullable=False)
    comments = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    document_type = Column(SQLEnum(DocumentTypeEnum, name="document_type_enum"), nullable=False)
    document_number = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    issuing_authority = Column(String(200), nullable=False)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    status = Column(SQLEnum(DocumentStatusEnum, name="document_status_enum"), default=DocumentStatusEnum.ACTIVE, nullable=False, index=True)
    file_url = Column(String(255), nullable=True)
    renewal_application_ref = Column(String(100), nullable=True)
    renewal_notes = Column(Text, nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    institution = relationship("Institution", back_populates="documents")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    alert_type = Column(SQLEnum(AlertTypeEnum, name="alert_type_enum"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    condition_logic = Column(JSONB, nullable=False)
    severity = Column(SQLEnum(AlertSeverityEnum, name="alert_severity_enum"), nullable=False)
    aph_reference_clause = Column(String(100), nullable=True)
    template_message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class EscalationRule(Base):
    __tablename__ = "escalation_rules"

    id = Column(Integer, primary_key=True, index=True)
    alert_rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    tier_level = Column(Integer, nullable=False)
    target_role = Column(SQLEnum(UserRoleEnum, name="user_role_enum"), nullable=False)
    trigger_delay_days = Column(Integer, nullable=False)
    action_required = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    alert_type = Column(SQLEnum(AlertTypeEnum, name="alert_type_enum"), nullable=False)
    severity = Column(SQLEnum(AlertSeverityEnum, name="alert_severity_enum"), nullable=False)
    status = Column(SQLEnum(AlertStatusEnum, name="alert_status_enum"), default=AlertStatusEnum.ACTIVE, nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    undertaking_id = Column(Integer, ForeignKey("undertakings.id"), nullable=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    recipient_role = Column(SQLEnum(UserRoleEnum, name="user_role_enum"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    explanation_meta = Column(JSONB, nullable=False)
    escalation_tier = Column(Integer, default=1)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    channel = Column(SQLEnum(NotificationChannelEnum, name="notification_channel_enum"), default=NotificationChannelEnum.IN_APP, nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class CaseSummary(Base):
    __tablename__ = "case_summaries"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True, nullable=False)
    executive_summary = Column(Text, nullable=False)
    key_findings = Column(JSONB, default=list)
    compliance_flags = Column(JSONB, default=list)
    risk_assessment = Column(Text, nullable=True)
    generated_by = Column(String(50), default="AI_ASSISTANT")
    last_generated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    application = relationship("Application", back_populates="case_summary")


class CommunicationTemplate(Base):
    __tablename__ = "communication_templates"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    subject = Column(String(200), nullable=False)
    body_template = Column(Text, nullable=False)
    variables = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
