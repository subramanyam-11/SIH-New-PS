-- ==============================================================================
-- SIH26262: AICTE Approval Workflow Automation & Compliance Monitoring System
-- Database Schema (PostgreSQL 15+)
-- ==============================================================================

-- Drop existing tables and types if re-running
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS scheduler_runs CASCADE;
DROP TABLE IF EXISTS email_outbox CASCADE;
DROP TABLE IF EXISTS escalation_history CASCADE;
DROP TABLE IF EXISTS case_summaries CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS application_communications CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS escalation_rules CASCADE;
DROP TABLE IF EXISTS alert_rules CASCADE;
DROP TABLE IF EXISTS undertaking_evidence CASCADE;
DROP TABLE IF EXISTS undertakings CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS evc_visits CASCADE;
DROP TABLE IF EXISTS stage_history CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS stage_paths CASCADE;
DROP TABLE IF EXISTS stages CASCADE;
DROP TABLE IF EXISTS application_categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS institutions CASCADE;
DROP TABLE IF EXISTS regions CASCADE;
DROP TABLE IF EXISTS communication_templates CASCADE;
DROP TABLE IF EXISTS system_config CASCADE;

-- Drop Enums
DROP TYPE IF EXISTS user_role_enum CASCADE;
DROP TYPE IF EXISTS application_status_enum CASCADE;
DROP TYPE IF EXISTS stage_status_enum CASCADE;
DROP TYPE IF EXISTS evc_status_enum CASCADE;
DROP TYPE IF EXISTS undertaking_status_enum CASCADE;
DROP TYPE IF EXISTS document_type_enum CASCADE;
DROP TYPE IF EXISTS document_status_enum CASCADE;
DROP TYPE IF EXISTS alert_type_enum CASCADE;
DROP TYPE IF EXISTS alert_severity_enum CASCADE;
DROP TYPE IF EXISTS alert_status_enum CASCADE;
DROP TYPE IF EXISTS notification_channel_enum CASCADE;

-- ==============================================================================
-- 1. ENUMS
-- ==============================================================================

CREATE TYPE user_role_enum AS ENUM (
    'ADMIN',
    'SCRUTINY_OFFICER',
    'EVC_COORDINATOR',
    'REGIONAL_HEAD',
    'COMPETENT_AUTHORITY',
    'INSTITUTION_USER',
    'BUREAU_OFFICER',
    'COMMITTEE_MEMBER'
);

CREATE TYPE application_status_enum AS ENUM (
    'DRAFT',
    'IN_PROGRESS',
    'APPROVED',
    'REJECTED',
    'WITHDRAWN',
    'CLOSED'
);

CREATE TYPE stage_status_enum AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED',
    'REVERTED',
    'SKIPPED'
);

CREATE TYPE evc_status_enum AS ENUM (
    'PENDING_SCHEDULE',
    'PENDING_ASSIGNMENT',
    'ASSIGNED',
    'SCHEDULED',
    'VISIT_COMPLETED',
    'VISIT_DONE',
    'REPORT_SUBMITTED',
    'REPORT_RECEIVED',
    'CLOSED',
    'CANCELLED'
);

CREATE TYPE undertaking_status_enum AS ENUM (
    'PENDING_SUBMISSION',
    'PENDING',
    'SUBMITTED',
    'UNDER_VERIFICATION',
    'VERIFIED',
    'REJECTED',
    'NEEDS_MORE_EVIDENCE',
    'COMPLIED',
    'OVERDUE',
    'ESCALATED',
    'DEFAULTED'
);

CREATE TYPE document_type_enum AS ENUM (
    'LAND_LEASE_DEED',
    'BUILDING_PLAN_APPROVAL',
    'FIRE_SAFETY_NOC',
    'OCCUPANCY_CERTIFICATE',
    'AICTE_FDR_GUARANTEE',
    'AFFILIATING_UNIVERSITY_NOC'
);

CREATE TYPE document_status_enum AS ENUM (
    'ACTIVE',
    'VALID',
    'EXPIRING',
    'RENEWAL_SUBMITTED',
    'RENEWED',
    'EXPIRING_SOON',
    'EXPIRED',
    'SUPERSEDED'
);

CREATE TYPE alert_type_enum AS ENUM (
    'NEAR_BREACH',
    'OVERDUE',
    'EVC_UNSCHEDULED',
    'UNDERTAKING_DUE',
    'DOCUMENT_EXPIRING',
    'DOCUMENT_EXPIRED',
    'MULTIPLE_REVERTS',
    'EVC_VISIT_OVERDUE',
    'UNDERTAKING_OVERDUE',
    'DOCUMENT_RENEWAL_OVERDUE',
    'RISK_HIGH'
);

CREATE TYPE alert_severity_enum AS ENUM (
    'INFO',
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);

CREATE TYPE alert_status_enum AS ENUM (
    'ACTIVE',
    'ACKNOWLEDGED',
    'SNOOZED',
    'RESOLVED',
    'ESCALATED'
);

CREATE TYPE notification_channel_enum AS ENUM (
    'IN_APP',
    'EMAIL',
    'SMS'
);

-- ==============================================================================
-- 2. CORE REGIONAL & USER HIERARCHY
-- ==============================================================================

CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,               -- e.g. 'RO_NORTH', 'RO_WEST'
    name VARCHAR(100) NOT NULL,                     -- e.g. 'Northern Regional Office (Kanpur)'
    headquarters VARCHAR(100) NOT NULL,
    states_covered TEXT[] NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    code user_role_enum UNIQUE NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE institutions (
    id SERIAL PRIMARY KEY,
    aicte_id VARCHAR(50) UNIQUE NOT NULL,           -- e.g. '1-109723451'
    name VARCHAR(255) NOT NULL,
    institution_type VARCHAR(100) NOT NULL,         -- e.g. 'Engineering & Technology', 'Management'
    category VARCHAR(50) NOT NULL,                  -- 'Govt', 'Govt-Aided', 'Self-Financing'
    region_id INT NOT NULL REFERENCES regions(id) ON DELETE RESTRICT,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(20) NOT NULL,
    primary_email VARCHAR(150) NOT NULL,
    primary_phone VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role_id INT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    region_id INT REFERENCES regions(id) ON DELETE SET NULL, -- NULL for Central/Admin roles
    institution_id INT REFERENCES institutions(id) ON DELETE SET NULL, -- Non-null for Institution Users
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 3. WORKFLOW CONFIGURATION & STAGE DEFINITIONS
-- ==============================================================================

CREATE TABLE application_categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,               -- e.g. 'NEW_INSTITUTE', 'EOA', 'INCREASE_INTAKE'
    title VARCHAR(150) NOT NULL,
    requires_evc BOOLEAN DEFAULT FALSE,
    requires_sac_shc BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stage_paths (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,               -- e.g. 'PATH_1_SCRUTINY_ONLY', 'PATH_2_SCRUTINY_EVC'
    name VARCHAR(150) NOT NULL,
    description TEXT,
    stage_sequence JSONB NOT NULL,                  -- Array of stage codes in sequential order
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stages (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,               -- 'SUBMITTED', 'SCRUTINY', 'RE_SCRUTINY', 'EVC_PENDING', etc.
    name VARCHAR(100) NOT NULL,
    default_sla_days INT NOT NULL,                  -- Configurable standard SLA limit
    responsible_role user_role_enum NOT NULL,
    description TEXT
);

-- ==============================================================================
-- 4. APPLICATION INSTANCES & LIFECYCLE
-- ==============================================================================

CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    application_number VARCHAR(50) UNIQUE NOT NULL, -- e.g. 'AICTE/2026/APP-10023'
    academic_year VARCHAR(20) NOT NULL DEFAULT '2026-2027',
    institution_id INT NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    category_id INT NOT NULL REFERENCES application_categories(id) ON DELETE RESTRICT,
    stage_path_id INT NOT NULL REFERENCES stage_paths(id) ON DELETE RESTRICT,
    current_stage_id INT NOT NULL REFERENCES stages(id) ON DELETE RESTRICT,
    status application_status_enum NOT NULL DEFAULT 'IN_PROGRESS',
    assigned_officer_id INT REFERENCES users(id) ON DELETE SET NULL,
    region_id INT NOT NULL REFERENCES regions(id) ON DELETE RESTRICT,
    
    stage_entered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    stage_due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    revert_count INT DEFAULT 0,
    
    -- Innovation metadata: ML risk score computed asynchronously
    delay_risk_score FLOAT DEFAULT 0.0,             -- 0.0 to 1.0 (Low to Critical)
    risk_factors JSONB DEFAULT '[]'::jsonb,         -- Reason factors for risk
    
    -- Phase 3 Approval & Escalation Fields
    approval_letter_ref VARCHAR(100),
    approval_letter_data JSONB,
    escalation_required BOOLEAN DEFAULT FALSE,
    escalation_reason TEXT,

    -- Phase 6 Fair Pendency Clock & Closed State Fields
    case_holder VARCHAR(30) NOT NULL DEFAULT 'WITH_AICTE',
    closed_at TIMESTAMP WITH TIME ZONE,
    closure_reason VARCHAR(50),
    closure_remarks TEXT,
    risk_band VARCHAR(20) DEFAULT 'LOW',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE application_communications (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    template_code VARCHAR(50) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    recipient_email VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',    -- 'DRAFT', 'SENT'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE,
    sent_by INT REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE stage_history (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    from_stage_id INT REFERENCES stages(id) ON DELETE RESTRICT,
    to_stage_id INT NOT NULL REFERENCES stages(id) ON DELETE RESTRICT,
    action_taken VARCHAR(100) NOT NULL,             -- 'ADVANCE', 'REVERT', 'RE_SUBMIT', 'REJECT', 'APPROVE'
    actor_id INT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status stage_status_enum NOT NULL,
    reason TEXT,                                    -- Mandatory if REVERT or REJECT
    deficiency_tags TEXT[],                         -- e.g. ['DEF_LAND_TITLE', 'DEF_FIRE_NOC']
    entered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    duration_hours FLOAT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ==============================================================================
-- 4.1 UPLOADED FILES & EVIDENCE ARTIFACTS
-- ==============================================================================

CREATE TABLE uploaded_files (
    id SERIAL PRIMARY KEY,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes INT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    entity_type VARCHAR(50),                        -- 'UNDERTAKING_EVIDENCE', 'DOCUMENT_RENEWAL', 'EVC_REPORT'
    entity_id INT,
    uploaded_by INT REFERENCES users(id) ON DELETE SET NULL,
    is_encrypted BOOLEAN NOT NULL DEFAULT FALSE,
    encryption_key_id VARCHAR(50),
    encryption_iv VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_uploaded_files_entity ON uploaded_files(entity_type, entity_id);

-- ==============================================================================
-- 5. EVC (EXPERT VISIT COMMITTEE) SCHEDULING & EXPERTS POOL
-- ==============================================================================

CREATE TABLE evc_experts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    designation VARCHAR(150) NOT NULL,              -- e.g. 'Professor', 'Dean', 'Principal'
    discipline VARCHAR(100) NOT NULL,               -- e.g. 'Computer Science', 'Mechanical Engineering'
    region_id INT NOT NULL REFERENCES regions(id) ON DELETE RESTRICT,
    home_institution VARCHAR(200) NOT NULL,         -- Used for conflict-of-interest check
    city VARCHAR(100) NOT NULL,                     -- Used for geographic conflict check
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evc_experts_region_id ON evc_experts(region_id);

CREATE TABLE evc_visits (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    status evc_status_enum NOT NULL DEFAULT 'PENDING_ASSIGNMENT',
    coordinator_id INT REFERENCES users(id) ON DELETE SET NULL,
    
    scheduled_date DATE,
    scheduled_time VARCHAR(50),
    visit_type VARCHAR(50) DEFAULT 'PHYSICAL',      -- 'PHYSICAL', 'VIRTUAL', 'SURPRISE'
    committee_chair VARCHAR(150),
    committee_experts JSONB DEFAULT '[]'::jsonb,    -- Array of expert names, affiliations, specializations
    assigned_experts JSONB DEFAULT '[]'::jsonb,     -- 3 assigned experts with conflict checks
    
    visit_completed_at TIMESTAMP WITH TIME ZONE,
    visit_summary TEXT,
    report_uploaded_at TIMESTAMP WITH TIME ZONE,
    report_file_url VARCHAR(255),
    report_file_id INT REFERENCES uploaded_files(id) ON DELETE SET NULL,
    outcome_recommendation VARCHAR(50),             -- 'RECOMMENDED', 'DEFICIENCIES_FOUND', 'REJECTED'
    remarks TEXT,
    closed_at TIMESTAMP WITH TIME ZONE,
    closed_by INT REFERENCES users(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 6. UNDERTAKINGS & CONDITIONAL COMPLIANCE
-- ==============================================================================

CREATE TABLE undertakings (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    institution_id INT NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    condition_title VARCHAR(255) NOT NULL,          -- e.g. 'Build Ramp and Divyangjan Lift by Term 2'
    description TEXT NOT NULL,
    due_date DATE NOT NULL,
    status undertaking_status_enum NOT NULL DEFAULT 'PENDING',
    
    rejection_count INT DEFAULT 0,
    escalated_to_tier INT DEFAULT 1,
    escalation_reason TEXT,
    
    assigned_verifier_id INT REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    verification_remarks TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE undertaking_history (
    id SERIAL PRIMARY KEY,
    undertaking_id INT NOT NULL REFERENCES undertakings(id) ON DELETE CASCADE,
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    action_by INT REFERENCES users(id) ON DELETE SET NULL,
    action_role VARCHAR(50),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_undertaking_history_undertaking_id ON undertaking_history(undertaking_id);

CREATE TABLE undertaking_evidence (
    id SERIAL PRIMARY KEY,
    undertaking_id INT NOT NULL REFERENCES undertakings(id) ON DELETE CASCADE,
    submitted_by INT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(255) NOT NULL,
    file_id INT REFERENCES uploaded_files(id) ON DELETE SET NULL,
    comments TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 7. LEASE & STATUTORY DOCUMENT VALIDITY (VERSIONED)
-- ==============================================================================

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    institution_id INT NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    application_id INT REFERENCES applications(id) ON DELETE SET NULL,
    document_type document_type_enum NOT NULL,
    document_number VARCHAR(100) NOT NULL,          -- e.g. Registered Deed No. 4392/2012
    title VARCHAR(200) NOT NULL,
    issuing_authority VARCHAR(200) NOT NULL,
    issue_date DATE NOT NULL,
    expiry_date DATE NOT NULL,                      -- Key tracking column
    status document_status_enum NOT NULL DEFAULT 'ACTIVE',
    
    version_number INT DEFAULT 1,
    previous_version_id INT REFERENCES documents(id) ON DELETE SET NULL,
    renewal_file_id INT REFERENCES uploaded_files(id) ON DELETE SET NULL,
    verified_by INT REFERENCES users(id) ON DELETE SET NULL,
    verification_remarks TEXT,
    
    file_url VARCHAR(255),
    renewal_application_ref VARCHAR(100),
    renewal_notes TEXT,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 8. ALERTS, ESCALATIONS & NOTIFICATIONS (Explainable Rules)
-- ==============================================================================

CREATE TABLE alert_rules (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,               -- e.g. 'RULE_SCRUTINY_NEAR_BREACH', 'RULE_LEASE_90D'
    name VARCHAR(150) NOT NULL,
    alert_type alert_type_enum NOT NULL,
    entity_type VARCHAR(50) NOT NULL,               -- 'APPLICATION', 'EVC', 'UNDERTAKING', 'DOCUMENT'
    condition_logic JSONB NOT NULL,                 -- e.g. {"field": "days_remaining", "operator": "<=", "value": 2}
    severity alert_severity_enum NOT NULL,
    aph_reference_clause VARCHAR(100),              -- Regulatory citation for explainability
    template_message TEXT NOT NULL,
    day_basis VARCHAR(20) NOT NULL DEFAULT 'WORKING', -- 'WORKING' or 'CALENDAR'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE escalation_rules (
    id SERIAL PRIMARY KEY,
    alert_rule_id INT NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    tier_level INT NOT NULL,                        -- 1: Officer, 2: Regional Head, 3: Competent Authority
    target_role user_role_enum NOT NULL,
    trigger_delay_days INT NOT NULL,                -- Days overdue before this tier triggers
    action_required VARCHAR(150) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_rule_id INT NOT NULL REFERENCES alert_rules(id) ON DELETE RESTRICT,
    alert_type alert_type_enum NOT NULL,
    severity alert_severity_enum NOT NULL,
    status alert_status_enum NOT NULL DEFAULT 'ACTIVE',
    
    application_id INT REFERENCES applications(id) ON DELETE CASCADE,
    institution_id INT REFERENCES institutions(id) ON DELETE CASCADE,
    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
    undertaking_id INT REFERENCES undertakings(id) ON DELETE CASCADE,
    
    recipient_user_id INT REFERENCES users(id) ON DELETE SET NULL,
    recipient_role user_role_enum NOT NULL,
    
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    explanation_meta JSONB NOT NULL,                -- Explainable breakdown: {rule_code, trigger_value, threshold, aph_clause}
    
    escalation_tier INT DEFAULT 1,
    escalated_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    snoozed_until TIMESTAMP WITH TIME ZONE,
    snooze_count INT DEFAULT 0,
    snooze_reason TEXT,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by INT REFERENCES users(id) ON DELETE SET NULL,
    acknowledgement_remarks TEXT,
    resolved_by INT REFERENCES users(id) ON DELETE SET NULL,
    resolution_remarks TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE escalation_history (
    id SERIAL PRIMARY KEY,
    alert_id INT NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    from_tier INT NOT NULL,
    to_tier INT NOT NULL,
    target_role VARCHAR(50) NOT NULL,
    recipient_user_id INT REFERENCES users(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    escalated_by INT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    alert_id INT REFERENCES alerts(id) ON DELETE SET NULL,
    recipient_user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel notification_channel_enum NOT NULL DEFAULT 'IN_APP',
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE email_outbox (
    id SERIAL PRIMARY KEY,
    recipient_email VARCHAR(150) NOT NULL,
    recipient_user_id INT REFERENCES users(id) ON DELETE SET NULL,
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'QUEUED',   -- 'QUEUED', 'SENT', 'FAILED', 'SUPPRESSED'
    template_code VARCHAR(50),
    entity_type VARCHAR(50),
    entity_id INT,
    attempts INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE scheduler_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP WITH TIME ZONE,
    duration_ms INT,
    rules_evaluated INT DEFAULT 0,
    alerts_created INT DEFAULT 0,
    alerts_upgraded INT DEFAULT 0,
    alerts_resolved INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'SUCCESS',
    triggered_by VARCHAR(50) DEFAULT 'SCHEDULER',
    details JSONB DEFAULT '{}'::jsonb
);

-- ==============================================================================
-- 9. CASE SUMMARIES (AI-ASSISTED & AUDIT LOGS)
-- ==============================================================================

CREATE TABLE case_summaries (
    id SERIAL PRIMARY KEY,
    application_id INT UNIQUE NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    executive_summary TEXT NOT NULL,
    key_findings JSONB DEFAULT '[]'::jsonb,
    compliance_flags JSONB DEFAULT '[]'::jsonb,
    risk_assessment TEXT,
    generated_by VARCHAR(50) DEFAULT 'AI_ASSISTANT',-- 'AI_ASSISTANT' or 'USER'
    source_label VARCHAR(50) DEFAULT 'template',
    input_hash VARCHAR(64),
    timeline_highlights JSONB DEFAULT '[]'::jsonb,
    pending_items JSONB DEFAULT '[]'::jsonb,
    upcoming_deadlines JSONB DEFAULT '[]'::jsonb,
    suggested_next_steps JSONB DEFAULT '[]'::jsonb,
    risk_score_at_generation FLOAT,
    top_risk_factors JSONB DEFAULT '[]'::jsonb,
    last_generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE communication_templates (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,               -- e.g. 'DEFICIENCY_NOTICE', 'EVC_SCHEDULE_INTIMATION'
    subject VARCHAR(200) NOT NULL,
    body_template TEXT NOT NULL,
    variables JSONB DEFAULT '[]'::jsonb,            -- e.g. ["institution_name", "deficiencies", "due_date"]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    actor_id INT REFERENCES users(id) ON DELETE SET NULL,
    ip_address VARCHAR(45),
    prev_hash VARCHAR(64),
    hash VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_log_hash ON audit_log(hash);

CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_by INT REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 10. INDEXES FOR HIGH-PERFORMANCE DASHBOARD FILTERING
-- ==============================================================================

-- Applications filter indexes
CREATE INDEX idx_apps_region_id ON applications(region_id);
CREATE INDEX idx_apps_stage_id ON applications(current_stage_id);
CREATE INDEX idx_apps_institution_id ON applications(institution_id);
CREATE INDEX idx_apps_officer_id ON applications(assigned_officer_id);
CREATE INDEX idx_apps_status ON applications(status);
CREATE INDEX idx_apps_stage_due_date ON applications(stage_due_date);
CREATE INDEX idx_apps_delay_risk ON applications(delay_risk_score DESC);

-- Stage history performance
CREATE INDEX idx_history_app_id ON stage_history(application_id);
CREATE INDEX idx_history_entered_at ON stage_history(entered_at);

-- Documents expiry watcher index
CREATE INDEX idx_docs_expiry_date ON documents(expiry_date);
CREATE INDEX idx_docs_status ON documents(status);
CREATE INDEX idx_docs_institution_id ON documents(institution_id);

-- Undertakings compliance index
CREATE INDEX idx_undertakings_due_date ON undertakings(due_date);
CREATE INDEX idx_undertakings_status ON undertakings(status);

-- Alerts & Notifications queries
CREATE INDEX idx_alerts_recipient ON alerts(recipient_user_id, status);
CREATE INDEX idx_alerts_role ON alerts(recipient_role, status);
CREATE INDEX idx_alerts_app_id ON alerts(application_id);
CREATE INDEX idx_notifications_unread ON notifications(recipient_user_id, is_read);

-- ==============================================================================
-- 11. PHASE 6: V2 ALIGNMENT MODULES
-- ==============================================================================

-- Fair Pendency Clock Segments
CREATE TABLE clock_segments (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    stage_id INT NOT NULL REFERENCES stages(id),
    holder VARCHAR(30) NOT NULL, -- 'WITH_AICTE' or 'WITH_INSTITUTION'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_hours FLOAT,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_clock_segments_app_started ON clock_segments(application_id, started_at);
CREATE INDEX idx_clock_segments_holder ON clock_segments(holder);

-- Working-Day Calendar & Holidays
CREATE TABLE holidays (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    name VARCHAR(150) NOT NULL,
    region_id INT REFERENCES regions(id) ON DELETE SET NULL,
    holiday_type VARCHAR(50) NOT NULL DEFAULT 'NATIONAL', -- 'NATIONAL', 'REGIONAL', 'RESTRICTED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_holidays_date ON holidays(date);
CREATE INDEX idx_holidays_region ON holidays(region_id);

-- Committee Assignments & Observations (EVC / SAC / SHC)
CREATE TABLE committee_assignments (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    committee_type VARCHAR(20) NOT NULL, -- 'EVC', 'SAC', 'SHC'
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ASSIGNED',
    notes TEXT
);
CREATE INDEX idx_committee_assignments_app ON committee_assignments(application_id, committee_type);
CREATE INDEX idx_committee_assignments_user ON committee_assignments(user_id);

CREATE TABLE committee_observations (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    committee_type VARCHAR(20) NOT NULL, -- 'EVC', 'SAC', 'SHC'
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    member_name VARCHAR(150) NOT NULL,
    observation_text TEXT NOT NULL,
    recommendation VARCHAR(50) NOT NULL, -- 'RECOMMEND_APPROVAL', 'RECOMMEND_REJECTION', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_committee_obs_app ON committee_observations(application_id, committee_type);

-- ==============================================================================
-- 12. PHASE 7 & 8: INNOVATION, RISK SCORING, SMART RANKING & INTEGRATION LOG
-- ==============================================================================

CREATE TABLE risk_score_snapshots (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    score FLOAT NOT NULL,
    band VARCHAR(20) NOT NULL,
    factor_age FLOAT NOT NULL DEFAULT 0,
    factor_returns FLOAT NOT NULL DEFAULT 0,
    factor_workload FLOAT NOT NULL DEFAULT 0,
    factor_stage FLOAT NOT NULL DEFAULT 0,
    raw_age FLOAT,
    raw_returns FLOAT,
    raw_workload FLOAT,
    raw_stage FLOAT,
    weights JSONB NOT NULL DEFAULT '{}',
    config_version VARCHAR(50),
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_risk_snapshots_app_id ON risk_score_snapshots(application_id);

CREATE TABLE alert_priority_scores (
    id SERIAL PRIMARY KEY,
    alert_id INT NOT NULL REFERENCES alerts(id) ON DELETE CASCADE UNIQUE,
    priority_score FLOAT NOT NULL,
    factor_severity FLOAT NOT NULL DEFAULT 0,
    factor_overdue_days FLOAT NOT NULL DEFAULT 0,
    factor_escalation FLOAT NOT NULL DEFAULT 0,
    factor_risk_impact FLOAT NOT NULL DEFAULT 0,
    explanation TEXT
);
CREATE INDEX idx_alert_priority_alert_id ON alert_priority_scores(alert_id);

CREATE TABLE integration_log (
    id SERIAL PRIMARY KEY,
    direction VARCHAR(20) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    adapter_type VARCHAR(50) NOT NULL DEFAULT 'MOCK_AICTE',
    status VARCHAR(20) NOT NULL,
    idempotency_key VARCHAR(100),
    request_summary JSONB,
    response_summary JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_integration_log_idempotency ON integration_log(idempotency_key);

-- ==============================================================================
-- 13. AUDIT LOG IMMUTABILITY TRIGGER (Strict Database-Level Enforcement)
-- ==============================================================================

CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE statements are strictly blocked at the database level.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_log_prevent_modify ON audit_log;
CREATE TRIGGER trg_audit_log_prevent_modify
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_log_modification();

