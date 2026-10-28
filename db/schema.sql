-- ==============================================================================
-- SIH26262: AICTE Approval Workflow Automation & Compliance Monitoring System
-- Database Schema (PostgreSQL 15+)
-- ==============================================================================

-- Drop existing tables and types if re-running
DROP TABLE IF EXISTS audit_log CASCADE;
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
    'INSTITUTION_USER'
);

CREATE TYPE application_status_enum AS ENUM (
    'DRAFT',
    'IN_PROGRESS',
    'APPROVED',
    'REJECTED',
    'WITHDRAWN'
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
    'SCHEDULED',
    'VISIT_COMPLETED',
    'REPORT_SUBMITTED',
    'CANCELLED'
);

CREATE TYPE undertaking_status_enum AS ENUM (
    'PENDING_SUBMISSION',
    'UNDER_VERIFICATION',
    'COMPLIED',
    'OVERDUE',
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
    'RENEWAL_SUBMITTED',
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
    'MULTIPLE_REVERTS'
);

CREATE TYPE alert_severity_enum AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);

CREATE TYPE alert_status_enum AS ENUM (
    'ACTIVE',
    'ACKNOWLEDGED',
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
-- 5. EVC (EXPERT VISIT COMMITTEE) SCHEDULING & REPORTS
-- ==============================================================================

CREATE TABLE evc_visits (
    id SERIAL PRIMARY KEY,
    application_id INT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    status evc_status_enum NOT NULL DEFAULT 'PENDING_SCHEDULE',
    coordinator_id INT REFERENCES users(id) ON DELETE SET NULL,
    
    scheduled_date DATE,
    visit_type VARCHAR(50) DEFAULT 'PHYSICAL',      -- 'PHYSICAL', 'VIRTUAL', 'SURPRISE'
    committee_chair VARCHAR(150),
    committee_experts JSONB DEFAULT '[]'::jsonb,    -- Array of expert names, affiliations, specializations
    
    visit_completed_at TIMESTAMP WITH TIME ZONE,
    report_uploaded_at TIMESTAMP WITH TIME ZONE,
    report_file_url VARCHAR(255),
    outcome_recommendation VARCHAR(50),             -- 'RECOMMENDED', 'DEFICIENCIES_FOUND', 'REJECTED'
    remarks TEXT,
    
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
    status undertaking_status_enum NOT NULL DEFAULT 'PENDING_SUBMISSION',
    
    assigned_verifier_id INT REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    verification_remarks TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE undertaking_evidence (
    id SERIAL PRIMARY KEY,
    undertaking_id INT NOT NULL REFERENCES undertakings(id) ON DELETE CASCADE,
    submitted_by INT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(255) NOT NULL,
    comments TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 7. LEASE & STATUTORY DOCUMENT VALIDITY
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
    action VARCHAR(20) NOT NULL,                    -- 'INSERT', 'UPDATE', 'DELETE', 'STATE_TRANSITION'
    old_values JSONB,
    new_values JSONB,
    actor_id INT REFERENCES users(id) ON DELETE SET NULL,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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
