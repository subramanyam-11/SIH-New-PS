# 04. Data Model and Database Architecture

## 1. Entity Relationship Overview

The data model for SIH26262 is designed around an immutable state-transition log, configurable regulatory paths, and dedicated compliance tracking for conditional undertakings and expiring statutory documents.

```mermaid
erDiagram
    REGIONS ||--o{ INSTITUTIONS : hosts
    REGIONS ||--o{ USERS : assigns
    ROLES ||--o{ USERS : grants
    INSTITUTIONS ||--o{ USERS : employs
    INSTITUTIONS ||--o{ APPLICATIONS : submits
    INSTITUTIONS ||--o{ DOCUMENTS : holds
    INSTITUTIONS ||--o{ UNDERTAKINGS : binds
    
    APPLICATION_CATEGORIES ||--o{ APPLICATIONS : categorizes
    STAGE_PATHS ||--o{ APPLICATIONS : dictates_route
    STAGES ||--o{ APPLICATIONS : current_stage
    USERS ||--o{ APPLICATIONS : assigned_officer
    
    APPLICATIONS ||--o{ STAGE_HISTORY : tracks_transitions
    APPLICATIONS ||--o{ EVC_VISITS : requires_inspection
    APPLICATIONS ||--o{ UNDERTAKINGS : imposes_conditions
    APPLICATIONS ||--o| CASE_SUMMARIES : summarizes
    
    UNDERTAKINGS ||--o{ UNDERTAKING_EVIDENCE : provides_proof
    
    ALERT_RULES ||--o{ ALERTS : triggers
    ALERT_RULES ||--o{ ESCALATION_RULES : defines_tiers
    ALERTS ||--o{ NOTIFICATIONS : delivers
```

---

## 2. Core Architectural Pillars

### A. Dynamic Workflow State Engine
- **`stage_paths` & `stages`**: Defines allowable paths (e.g. `PATH_1_SCRUTINY_ONLY`, `PATH_2_SCRUTINY_EVC`). Each stage specifies its default SLA (`default_sla_days`) and the responsible role.
- **`stage_history`**: Every movement (`ADVANCE`, `REVERT`, `RE_SUBMIT`, `REJECT`) creates an immutable record capturing:
  - `actor_id`: Who made the decision.
  - `reason`: Mandatory for any revert or rejection.
  - `deficiency_tags`: Standardized taxonomy of issues (e.g., `DEF_LAND_TITLE`, `DEF_FIRE_NOC`).
  - `duration_hours`: Exact time elapsed in stage for bottleneck analytics.

### B. EVC Inspection Tracking
- **`evc_visits`**: Decoupled from application core to allow full scheduling logistics:
  - Supports panel chair + experts stored as structured JSONB (`committee_experts`).
  - Tracks key statutory milestones: `PENDING_SCHEDULE`, `SCHEDULED`, `VISIT_COMPLETED`, and `REPORT_SUBMITTED`.
  - Captures geo-inspection report metadata and final recommendation (`RECOMMENDED`, `DEFICIENCIES_FOUND`, `REJECTED`).

### C. Compliance & Statutory Document Tracking
- **`documents`**: Specifically addresses lease expirations and recurring NOC renewals.
  - Tracks `document_type` (`LAND_LEASE_DEED`, `FIRE_SAFETY_NOC`, `AICTE_FDR_GUARANTEE`, etc.).
  - Has explicit `expiry_date` with indexed B-tree search for the automated nightly watcher.
  - Tracks renewal status (`ACTIVE`, `RENEWAL_SUBMITTED`, `EXPIRING_SOON`, `EXPIRED`).
- **`undertakings` & `undertaking_evidence`**:
  - Encapsulates conditions imposed during provisional approval.
  - Institutions submit evidence files (`undertaking_evidence`) reviewed by designated verification officers.

### D. Explainable Alert & Escalation System
- **`alert_rules`**: Stores rule code, condition logic in JSONB, severity, and the specific **APH reference clause** (e.g., "APH 2026 Clause 2.4.3: Land Lease Validity").
- **`alerts`**: When an alert fires, it saves `explanation_meta` capturing:
  ```json
  {
    "rule_code": "RULE_LEASE_90D",
    "days_until_expiry": 84,
    "threshold_days": 90,
    "aph_clause": "APH 2026 Chapter I Clause 1.4(e)"
  }
  ```
- **`escalation_rules`**: Defines multi-tiered ladders (Tier 1: Scrutiny Officer, Tier 2: Regional Head, Tier 3: Competent Authority) based on days overdue.

---

## 3. High-Performance Indexing Strategy

To support sub-second response times on regional and national dashboards, the schema creates specialized indexes:

| Table | Index | Purpose |
| :--- | :--- | :--- |
| `applications` | `(region_id, current_stage_id, status)` | Fast dashboard slicing by region, stage, and state. |
| `applications` | `(assigned_officer_id, stage_due_date)` | Instant personal task queues sorted by impending deadlines. |
| `applications` | `(delay_risk_score DESC)` | High-risk application sorting for executive intervention. |
| `documents` | `(expiry_date, status)` | High-frequency nightly cron queries checking for expiring leases/NOCs. |
| `undertakings` | `(due_date, status)` | Fast retrieval of delinquent or pending compliance conditions. |
| `alerts` | `(recipient_user_id, status)` | Real-time notification badge counts and unread alert feeds. |
