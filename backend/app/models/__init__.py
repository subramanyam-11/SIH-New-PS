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
    BUREAU_OFFICER = "BUREAU_OFFICER"
    COMMITTEE_MEMBER = "COMMITTEE_MEMBER"


class ApplicationStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    CLOSED = "CLOSED"


class CaseHolderEnum(str, enum.Enum):
    WITH_AICTE = "WITH_AICTE"
    WITH_INSTITUTION = "WITH_INSTITUTION"


class CommitteeTypeEnum(str, enum.Enum):
    EVC = "EVC"
    SAC = "SAC"
    SHC = "SHC"


class CommitteeRecommendationEnum(str, enum.Enum):
    RECOMMEND_APPROVAL = "RECOMMEND_APPROVAL"
    RECOMMEND_REJECTION = "RECOMMEND_REJECTION"
    RECOMMEND_RE_INSPECTION = "RECOMMEND_RE_INSPECTION"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class DayBasisEnum(str, enum.Enum):
    WORKING = "WORKING"
    CALENDAR = "CALENDAR"


class ClosureReasonEnum(str, enum.Enum):
    ALL_CONDITIONS_MET = "ALL_CONDITIONS_MET"
    REJECTED_FINAL = "REJECTED_FINAL"
    WITHDRAWN_BY_INSTITUTION = "WITHDRAWN_BY_INSTITUTION"
    SUPERSEDED = "SUPERSEDED"
    OTHER = "OTHER"


class StageStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REVERTED = "REVERTED"
    SKIPPED = "SKIPPED"


class EvcStatusEnum(str, enum.Enum):
    PENDING_SCHEDULE = "PENDING_SCHEDULE"
    PENDING_ASSIGNMENT = "PENDING_ASSIGNMENT"
    ASSIGNED = "ASSIGNED"
    SCHEDULED = "SCHEDULED"
    VISIT_COMPLETED = "VISIT_COMPLETED"
    VISIT_DONE = "VISIT_DONE"
    REPORT_SUBMITTED = "REPORT_SUBMITTED"
    REPORT_RECEIVED = "REPORT_RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class UndertakingStatusEnum(str, enum.Enum):
    PENDING_SUBMISSION = "PENDING_SUBMISSION"
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    UNDER_VERIFICATION = "UNDER_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    COMPLIED = "COMPLIED"
    OVERDUE = "OVERDUE"
    ESCALATED = "ESCALATED"
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
    VALID = "VALID"
    EXPIRING = "EXPIRING"
    RENEWAL_SUBMITTED = "RENEWAL_SUBMITTED"
    RENEWED = "RENEWED"
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
    EVC_VISIT_OVERDUE = "EVC_VISIT_OVERDUE"
    UNDERTAKING_OVERDUE = "UNDERTAKING_OVERDUE"
    DOCUMENT_RENEWAL_OVERDUE = "DOCUMENT_RENEWAL_OVERDUE"
    RISK_HIGH = "RISK_HIGH"


class AlertSeverityEnum(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    SNOOZED = "SNOOZED"
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

    # Phase 6 (v2 Alignment) additions:
    case_holder = Column(String(30), default="WITH_AICTE", nullable=False, index=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closure_reason = Column(String(50), nullable=True)
    closure_remarks = Column(Text, nullable=True)

    # Phase 7 (Innovation) additions:
    risk_band = Column(String(20), default="LOW", nullable=True)

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
    clock_segments = relationship("ClockSegment", back_populates="application", cascade="all, delete-orphan", order_by="ClockSegment.started_at")
    committee_assignments = relationship("CommitteeAssignment", back_populates="application", cascade="all, delete-orphan")
    committee_observations = relationship("CommitteeObservation", back_populates="application", cascade="all, delete-orphan", order_by="CommitteeObservation.created_at")


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


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    entity_type = Column(String(50), nullable=True) # 'UNDERTAKING_EVIDENCE', 'DOCUMENT_RENEWAL', 'EVC_REPORT'
    entity_id = Column(Integer, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    uploader = relationship("User", foreign_keys=[uploaded_by])


class EvcExpert(Base):
    __tablename__ = "evc_experts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    designation = Column(String(150), nullable=False)
    discipline = Column(String(100), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    home_institution = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    region = relationship("Region")


class EvcVisit(Base):
    __tablename__ = "evc_visits"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    status = Column(SQLEnum(EvcStatusEnum, name="evc_status_enum"), default=EvcStatusEnum.PENDING_ASSIGNMENT, nullable=False)
    coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    scheduled_date = Column(Date, nullable=True)
    scheduled_time = Column(String(50), nullable=True)
    visit_type = Column(String(50), default="PHYSICAL")
    committee_chair = Column(String(150), nullable=True)
    committee_experts = Column(JSONB, default=list)
    assigned_experts = Column(JSONB, default=list) # 3 expert objects with conflict check details
    
    visit_completed_at = Column(DateTime(timezone=True), nullable=True)
    visit_summary = Column(Text, nullable=True)
    report_uploaded_at = Column(DateTime(timezone=True), nullable=True)
    report_file_url = Column(String(255), nullable=True)
    report_file_id = Column(Integer, ForeignKey("uploaded_files.id", ondelete="SET NULL"), nullable=True)
    outcome_recommendation = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    application = relationship("Application")
    coordinator = relationship("User", foreign_keys=[coordinator_id])
    report_file = relationship("UploadedFile", foreign_keys=[report_file_id])
    closer = relationship("User", foreign_keys=[closed_by])


class Undertaking(Base):
    __tablename__ = "undertakings"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    condition_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(SQLEnum(UndertakingStatusEnum, name="undertaking_status_enum"), default=UndertakingStatusEnum.PENDING, nullable=False, index=True)
    
    rejection_count = Column(Integer, default=0, nullable=False)
    escalated_to_tier = Column(Integer, default=1, nullable=False)
    escalation_reason = Column(Text, nullable=True)
    
    assigned_verifier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    institution = relationship("Institution", back_populates="undertakings")
    application = relationship("Application")
    assigned_verifier = relationship("User", foreign_keys=[assigned_verifier_id])
    evidence_items = relationship("UndertakingEvidence", back_populates="undertaking", cascade="all, delete-orphan", order_by="UndertakingEvidence.submitted_at.desc()")
    history = relationship("UndertakingHistory", back_populates="undertaking", cascade="all, delete-orphan", order_by="UndertakingHistory.created_at.desc()")


class UndertakingHistory(Base):
    __tablename__ = "undertaking_history"

    id = Column(Integer, primary_key=True, index=True)
    undertaking_id = Column(Integer, ForeignKey("undertakings.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    action_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action_role = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    undertaking = relationship("Undertaking", back_populates="history")
    actor = relationship("User", foreign_keys=[action_by])


class UndertakingEvidence(Base):
    __tablename__ = "undertaking_evidence"

    id = Column(Integer, primary_key=True, index=True)
    undertaking_id = Column(Integer, ForeignKey("undertakings.id"), nullable=False)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(255), nullable=False)
    file_id = Column(Integer, ForeignKey("uploaded_files.id", ondelete="SET NULL"), nullable=True)
    comments = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    undertaking = relationship("Undertaking", back_populates="evidence_items")
    submitter = relationship("User", foreign_keys=[submitted_by])
    file_artifact = relationship("UploadedFile", foreign_keys=[file_id])


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
    
    version_number = Column(Integer, default=1, nullable=False)
    previous_version_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    renewal_file_id = Column(Integer, ForeignKey("uploaded_files.id", ondelete="SET NULL"), nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verification_remarks = Column(Text, nullable=True)
    
    file_url = Column(String(255), nullable=True)
    renewal_application_ref = Column(String(100), nullable=True)
    renewal_notes = Column(Text, nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    institution = relationship("Institution", back_populates="documents")
    application = relationship("Application")
    renewal_file = relationship("UploadedFile", foreign_keys=[renewal_file_id])
    verifier = relationship("User", foreign_keys=[verified_by])


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
    day_basis = Column(String(20), default="WORKING", nullable=False)
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

    snoozed_until = Column(DateTime(timezone=True), nullable=True)
    snooze_count = Column(Integer, default=0, nullable=False)
    snooze_reason = Column(Text, nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledgement_remarks = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_remarks = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    rule = relationship("AlertRule", backref="alerts")
    application = relationship("Application", backref="alerts")
    institution = relationship("Institution", backref="alerts")
    document = relationship("Document", backref="alerts")
    undertaking = relationship("Undertaking", backref="alerts")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id], backref="assigned_alerts")
    acknowledged_user = relationship("User", foreign_keys=[acknowledged_by])
    resolved_user = relationship("User", foreign_keys=[resolved_by])
    escalation_history = relationship("EscalationHistory", back_populates="alert", cascade="all, delete-orphan", order_by="desc(EscalationHistory.created_at)")
    notifications = relationship("Notification", back_populates="alert", cascade="all, delete-orphan")
    priority_score = relationship("AlertPriorityScore", uselist=False, back_populates="alert", cascade="all, delete-orphan")


class EscalationHistory(Base):
    __tablename__ = "escalation_history"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    from_tier = Column(Integer, nullable=False)
    to_tier = Column(Integer, nullable=False)
    target_role = Column(String(50), nullable=False)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=False)
    escalated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    alert = relationship("Alert", back_populates="escalation_history")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    escalated_by_user = relationship("User", foreign_keys=[escalated_by])


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

    alert = relationship("Alert", back_populates="notifications")
    recipient = relationship("User", backref="notifications")


class EmailOutbox(Base):
    __tablename__ = "email_outbox"

    id = Column(Integer, primary_key=True, index=True)
    recipient_email = Column(String(150), nullable=False)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(20), default="QUEUED", nullable=False, index=True)  # QUEUED, SENT, FAILED, SUPPRESSED
    template_code = Column(String(50), nullable=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    recipient = relationship("User", foreign_keys=[recipient_user_id])


class SchedulerRun(Base):
    __tablename__ = "scheduler_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    rules_evaluated = Column(Integer, default=0, nullable=False)
    alerts_created = Column(Integer, default=0, nullable=False)
    alerts_upgraded = Column(Integer, default=0, nullable=False)
    alerts_resolved = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="SUCCESS", nullable=False)
    triggered_by = Column(String(50), default="SCHEDULER", nullable=False)
    details = Column(JSONB, default=dict, nullable=False)


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

    # Phase 7 structured summary fields
    source_label = Column(String(50), default="template", nullable=True)
    input_hash = Column(String(64), nullable=True)
    timeline_highlights = Column(JSONB, default=list)
    pending_items = Column(JSONB, default=list)
    upcoming_deadlines = Column(JSONB, default=list)
    suggested_next_steps = Column(JSONB, default=list)
    risk_score_at_generation = Column(Float, nullable=True)
    top_risk_factors = Column(JSONB, default=list)

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
    action = Column(String(100), nullable=False)
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


class ClockSegment(Base):
    __tablename__ = "clock_segments"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_id = Column(Integer, ForeignKey("stages.id"), nullable=False)
    holder = Column(String(30), nullable=False, index=True)  # WITH_AICTE, WITH_INSTITUTION
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    application = relationship("Application", back_populates="clock_segments")
    stage = relationship("Stage")


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True, index=True)
    holiday_type = Column(String(50), default="NATIONAL", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    region = relationship("Region")


class CommitteeAssignment(Base):
    __tablename__ = "committee_assignments"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    committee_type = Column(String(20), nullable=False, index=True) # EVC, SAC, SHC
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status = Column(String(20), default="ASSIGNED", nullable=False)
    notes = Column(Text, nullable=True)

    application = relationship("Application", back_populates="committee_assignments")
    user = relationship("User")


class CommitteeObservation(Base):
    __tablename__ = "committee_observations"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    committee_type = Column(String(20), nullable=False, index=True) # EVC, SAC, SHC
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    member_name = Column(String(150), nullable=False)
    observation_text = Column(Text, nullable=False)
    recommendation = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    application = relationship("Application", back_populates="committee_observations")
    user = relationship("User")


class RiskScoreSnapshot(Base):
    __tablename__ = "risk_score_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    band = Column(String(20), nullable=False)
    factor_age = Column(Float, default=0.0, nullable=False)
    factor_returns = Column(Float, default=0.0, nullable=False)
    factor_workload = Column(Float, default=0.0, nullable=False)
    factor_stage = Column(Float, default=0.0, nullable=False)
    raw_age = Column(Float, nullable=True)
    raw_returns = Column(Float, nullable=True)
    raw_workload = Column(Float, nullable=True)
    raw_stage = Column(Float, nullable=True)
    weights = Column(JSONB, default=dict, nullable=False)
    config_version = Column(String(50), nullable=True)
    computed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    application = relationship("Application")


class AlertPriorityScore(Base):
    __tablename__ = "alert_priority_scores"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    priority_score = Column(Float, nullable=False)
    factor_severity = Column(Float, default=0.0, nullable=False)
    factor_overdue_days = Column(Float, default=0.0, nullable=False)
    factor_escalation = Column(Float, default=0.0, nullable=False)
    factor_risk_impact = Column(Float, default=0.0, nullable=False)
    explanation = Column(Text, nullable=True)
    computed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    alert = relationship("Alert", back_populates="priority_score")
