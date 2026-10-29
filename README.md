# SIH26262: Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System

> **A secure, intelligent, and configurable regulatory governance platform for the All India Council for Technical Education (AICTE)**. Built for the Smart India Hackathon.

---

## 1. Quick Start Guide (Run in 3 Commands)

### Option A: Using Make (macOS / Linux)

```bash
# 1. Setup environment (Python venv + Frontend npm packages)
make setup

# 2. Reset database and seed foundation records (roles, users, regions, institutions, APH rules)
make db-reset

# 3. Start development servers (Backend on :8000, Frontend on :3000)
make dev
```

### Option B: Step-by-Step for Windows (PowerShell)

```powershell
# 1. Start PostgreSQL (Docker or local service)
docker compose up -d

# 2. Setup and run Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\reset_db.py
uvicorn app.main:app --reload --port 8000

# 3. In a second PowerShell window, run Frontend
cd frontend
npm install
npm run dev
```

Visit the application at: **`http://localhost:3000`**  
FastAPI Interactive API Documentation: **`http://localhost:8000/docs`**

---

## 2. One-Click Demo Personas (`DEMO_MODE=true`)

When navigating to `http://localhost:3000/login`, one-click fast-login buttons are displayed under **One-Click Demo Personas**:

| Persona Role | User Name | Demo Email | Access Scope & Visible Views |
| :--- | :--- | :--- | :--- |
| **Regional Head (North)** | Er. Sunil Trivedi | `ro.north@aicte.gov.in` | Scoped to Northern RO (UP, UK). Views Dashboard, Applications, EVC Queue, Undertakings, Document Validity, Reports, Case Closure. |
| **Scrutiny Officer** | Amit Sharma | `scrutiny1@aicte.gov.in` | Northern RO Desk. Views Dashboard, Assigned Applications, Undertakings, Document Validity, Returns for Deficiency. |
| **EVC Coordinator** | Prof. K. Ramanathan | `evc.coord@aicte.gov.in` | Southern RO Desk. Views Dashboard, Applications, EVC Inspection Queue, Document Validity. |
| **Competent Authority** | Prof. T. G. Sitharam | `chairman@aicte.gov.in` | National Headquarters. High-level dashboard, SAC/SHC review, Reports, Statutory Approval/Rejection & Case Closure. |
| **Bureau Officer** | Smt. Neha Mukherjee | `bureau.officer@aicte.gov.in` | Central Technical Bureau. Cross-region read-only oversight of pendency, bottlenecks, and alerts acknowledgment. |
| **Committee Member (EVC)** | Dr. Anand Swaminathan | `evc.member@aicte.gov.in` | Expert Inspection Panel. Scoped strictly to assigned committee cases; records non-binding advisory observations. |
| **System Admin** | Dr. Rajesh Verma | `admin@aicte.gov.in` | Central HQ. Complete administrative control, APH rules configuration, working-day holiday calendar, audit logs. |
| **Institution User** | Dr. V. K. Saxena | `principal@apexkanpur.edu` | Apex Institute of Technology, Kanpur. Scoped strictly to own institution portal (`/portal`), deficiency clarification responses. |

*Default Password for standard email login*: **`Password@123`**

---

## 3. Database Architecture & One-Command Reset

- **PostgreSQL 15**: Runs via Docker Compose or native Homebrew/service on port `5432`.
- **Cloud Switch**: Swap `DATABASE_URL` in `.env` to connect directly to Neon, Supabase, or AWS RDS without code alterations.
- **One-Command Reset**:
  ```bash
  # Drops all tables/enums, executes db/schema.sql, stamps Alembic version, and seeds foundation data:
  python backend/scripts/reset_db.py
  ```

---

## 4. Architectural Documentation Index

All planning specifications and Phase 2 reports are available under [`docs/`](file:///Users/subramanyam/Sih%20new/docs) and [`db/`](file:///Users/subramanyam/Sih%20new/db):

1. **[01. Scope and Assumptions](file:///Users/subramanyam/Sih%20new/docs/01_scope_and_assumptions.md)** - Scope matrix, decisions, and assumptions.
2. **[02. Stage Paths and Workflow Rules](file:///Users/subramanyam/Sih%20new/docs/02_stage_paths_and_rules.md)** - 5 APH workflow pathways, state machine diagram, and configurable SLA rules.
3. **[03. Roles and Permissions Matrix](file:///Users/subramanyam/Sih%20new/docs/03_roles_and_permissions.md)** - 6-role RBAC security matrix and visibility views.
4. **[04. Data Model & Architecture](file:///Users/subramanyam/Sih%20new/docs/04_data_model.md)** - Database design with Mermaid ER diagram and indexing strategy.
5. **[Database Schema (PostgreSQL)](file:///Users/subramanyam/Sih%20new/db/schema.sql)** - Executable PostgreSQL DDL with 22 tables.
6. **[Synthetic Seed Data Plan](file:///Users/subramanyam/Sih%20new/db/seed_plan.md)** - Seed plan for 15 institutions, 5 regions, and 60 applications.
7. **[05. Alert and Escalation Engine](file:///Users/subramanyam/Sih%20new/docs/05_alert_and_escalation_design.md)** - 3-tier escalation ladder, trigger conditions, and explainability schema.
8. **[06. API & Screen Blueprint](file:///Users/subramanyam/Sih%20new/docs/06_api_and_screens.md)** - REST API catalog and screen wireframe purposes.
9. **[07. Innovation Layer Plan](file:///Users/subramanyam/Sih%20new/docs/07_innovation_plan.md)** - Delay Risk Score, Explainable Alerts, AI Case Docket, and EVC Tour Optimizer.
10. **[08. Team Split & Execution Plan](file:///Users/subramanyam/Sih%20new/docs/08_team_split_and_timeline.md)** - 5-member work allocation across Phases 2 to 7.
11. **[09. Phase 2 Foundation Report](file:///Users/subramanyam/Sih%20new/docs/09_phase2_foundation_report.md)** - Detailed summary of foundation build, tests, and endpoints.
12. **[10. Phase 3 Core Engine Report](file:///Users/subramanyam/Sih%20new/docs/10_phase3_core_engine_report.md)** - Detailed summary of state machine, 60-application dataset, SLA clock, and Letter of Approval generation.
13. **[11. Phase 4 Alerts & Watchers Report](file:///Users/subramanyam/Sih%20new/docs/11_phase4_alerts_report.md)** - Detailed report on alert rules engine, APScheduler, 3-tier escalation ladder, notifications, and outbox queue.
14. **[12. Phase 5 Compliance & Reports Report](file:///Users/subramanyam/Sih%20new/docs/12_phase5_screens_report.md)** - Interactive screens for EVC, Undertakings, Documents, and 5 statutory reports.
15. **[13. Phase 6 Build Plan v2 Alignment Report](file:///Users/subramanyam/Sih%20new/docs/13_phase6_v2_alignment_report.md)** - Fair Pendency Clock, Working-Day Calendar, CLOSED state, Overdue cases report, and new roles.
16. **[14. Phase 7 Innovation Layer Report](file:///Users/subramanyam/Sih%20new/docs/14_phase7_innovation_report.md)** - Delay Risk Score, Bottleneck Finder, AI Case Summary, What-If Planner, and Smart Alert Ranking.

---

## 5. Running Tests and Verification

```bash
# Run backend test suite (73 unit, integration, RBAC, workflow engine, alert watcher, Phase 6, and Phase 7 innovation tests)
make test
# Or: cd backend && .venv/bin/pytest -v

# Run automated end-to-end smoke test suite (28 comprehensive checks covering Phases 1 through 7)
make smoke
# Or: ./scripts/smoke_test.sh

# Re-seed demo dataset (60 applications, clock segments, committee assignments, holidays, alerts)
make seed-demo
```

---

## 6. Phase 4 Interactive Demo Walkthrough

### Scenario A: Real-Time Alert Engine & Explainable Drawer
1. Log in via one-click persona as **Regional Head (North)** (`ro.north@aicte.gov.in`) or **Admin** (`admin@aicte.gov.in`).
2. Navigate to **Alerts** (`/alerts`) via the left sidebar.
3. Observe the live summary cards (Critical: 5, High: 22, Medium: 34) loaded strictly from the database.
4. Click on any alert (e.g. `RULE_FIRE_NOC_EXPIRED` or `RULE_SCRUTINY_OVERDUE`).
5. Inspect the **"Why This Alert Fired"** explainability panel:
   - Plain-English explanation sentence
   - Actual observed value vs. statutory threshold
   - Regulatory APH clause with the visible `(sample reference)` marker
   - Escalation history timeline

### Scenario B: Procedural Officer Actions (Acknowledge, Snooze, Resolve)
1. On the open alert drawer, click **Acknowledge** and enter remarks. The status transitions to `ACKNOWLEDGED`.
2. Click **Snooze**, choose 24 Hours, and enter a substantive justification. The alert is snoozed. Note: attempting a third snooze triggers the strict database limit error (max 2).
3. Log in as **Competent Authority** (`chairman@aicte.gov.in`) or **Admin**. Open the alert drawer and click **Mark Resolved** with a written justification. The alert is statutorily resolved.

### Scenario C: Regional Escalation Hierarchy Matrix
1. Click **Escalation Matrix** (`/escalation-matrix`) in the navigation menu.
2. View the 5 regional offices against the 3-tier escalation ladder:
   - **Tier 1**: Scrutiny / Desk Officer (Assigned officer, delay 0d)
   - **Tier 2**: Regional Head (delay 2d)
   - **Tier 3**: Member Secretary / Competent Authority (delay 5d)
3. View open alert counts at each tier and click through to inspect filtered alerts.

### Scenario D: Dynamic Time-Travel Escalation & Outbox Queue
1. In the Top Bar, observe the **Notification Bell** with unread count badge. Click it to preview the latest alerts.
2. Click **Run Checks Now** in the top bar to evaluate rules on demand.
3. Advance the demo clock by **+24 Hours** or **+168 Hours (+7 Days)** on `/applications`.
4. Observe that the alert engine automatically evaluates the advanced clock: near-breach alerts upgrade to overdue, and unacknowledged alerts escalate from L1 to L2 and L3.
5. As Admin, navigate to **Email Outbox** (`/admin/outbox`). Inspect all queued notifications. Because `EMAIL_SEND_ENABLED=false` by default, all emails are safely held in `SUPPRESSED` status with full in-app previewability.

---

## 7. Email Outbox Configuration (`EMAIL_SEND_ENABLED`)

In `.env`:
```ini
# When false (default for hackathon demo): emails stay in database outbox as SUPPRESSED
# and are viewable in the app at /admin/outbox without sending actual SMTP traffic.
EMAIL_SEND_ENABLED=false

# When true: emails are dispatched through configured SMTP credentials
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=demo@aicte.gov.in
SMTP_PASSWORD=secret
```

---

14. **[12. Phase 5 Operational Screens Report](file:///Users/subramanyam/Sih%20new/docs/12_phase5_screens_report.md)** - Detailed report on EVC queue, Undertakings, Document validity, Executive reports, and Institution Portal.

---

## 5. Running Tests and Verification

```bash
# Run backend test suite (38 unit, RBAC, workflow engine, alert watchers, and Phase 5 screen tests)
make test

# Execute automated smoke test suite (17 end-to-end integration steps)
./scripts/smoke_test.sh

# Re-seed demo database with full lived-in dataset
make seed-demo
```

---

## 6. Role-Based Demo Walkthrough Script (Phase 5)

### Scenario A: Institution User (`principal@apexkanpur.edu`)
1. Login with one-click chip **Institution User (Apex Institute)**.
2. Note that your sidebar shows only **My Applications** (`/portal`), **Undertakings** (`/portal/undertakings`), and **Document Validity** (`/portal/documents`). Alerts and officer screens are completely hidden.
3. In `/portal`:
   - Inspect the statutory progress stepper on application `AICTE/2026/APP-10001`.
   - Review formal notices dispatched by AICTE in the *Notices & Letters* feed.
   - Click **Submit New Application** to file a new institutional submission.
4. In `/portal/undertakings`:
   - Inspect open conditions and due date countdowns.
   - Click **Upload Evidence Document** on an open undertaking, attach a PDF (`/tmp/sample.pdf`), add justification, and submit. Status transitions to `Submitted (Awaiting Officer Audit)`.
5. In `/portal/documents`:
   - Inspect statutory certificates (Lease, Fire NOC, FDR Guarantee).
   - Click **Upload Renewal**, specify a new expiry date, select a file, and submit. Notice status shows *"Renewal submitted, awaiting verification"*.

### Scenario B: Scrutiny Officer (`scrutiny1@aicte.gov.in`)
1. Login with one-click chip **Scrutiny Officer (Northern RO)**.
2. Navigate to **Undertakings** (`/undertakings`):
   - Locate the undertaking submitted by Apex Institute.
   - Click **Review & Audit** to open the slide-out drawer.
   - Download and inspect the uploaded evidence file.
   - Select **Verified** (or **Reject** / **Need Evidence**) with officer audit remarks and click **Submit Determination**. Notice the audit history timeline records the event.
3. Navigate to **Document Validity** (`/document-validity`):
   - Find documents in `Critical <=30d` or `Renewal submitted`.
   - Click **Review & Audit** to view the version history (`v1 -> v2`).
   - Approve or reject the renewal dossier. Notice linked alerts auto-resolve upon officer verification.

### Scenario C: EVC Coordinator (`evc.coord@aicte.gov.in`)
1. Login with one-click chip **EVC Coordinator**.
2. Navigate to **EVC Queue** (`/evc-queue`):
   - Filter by status `Pending Assignment` or toggle to **Inspection Calendar** view.
   - Notice institutions marked with the **NEW INSTITUTION** badge.
   - Click **Manage Visit** on a visit in `Pending Assignment`.
   - In Step 1, review the decision-support **Suggested Experts** ranked by suitability.
   - Observe conflict warnings displayed in plain English (e.g. *Home city matches institution location* or *Exceeds max concurrent visits*).
   - Select exactly 3 conflict-free experts and click **Confirm 3-Member Panel**.
   - In Step 2, pick the inspection date and assembly time and click **Confirm Inspection Date**. Notice linked unscheduled alerts auto-resolve.
   - In Step 3 & 4, mark visit completed and upload the signed EVC report.
   - In Step 5, click **Close EVC Visit**. The scrutiny officer can now advance the case to SAC/SHC.

### Scenario D: Regional Head (`ro.north@aicte.gov.in`)
1. Login with one-click chip **Regional Head (North)**.
2. Navigate to **Reports** (`/reports`):
   - Inspect **Pendency & Ageing** with Recharts bar chart showing pending vs overdue cases by stage.
   - Switch to **Regional Performance Matrix** to compare SLA breach rates across all regions.
   - Click **Export CSV** to download `aicte_regional_performance_report.csv`.
   - Click **Export PDF** to generate and download a formal `aicte_regional_performance_report.pdf` docket.
   - Switch to **Institution Health Dossier**, select any institution, and inspect its 360-degree regulatory compliance score and dossier.

### Scenario E: Competent Authority (`chairman@aicte.gov.in`)
1. Login with one-click chip **Competent Authority**.
2. Navigate to **Undertakings** (`/undertakings`):
   - View undertakings flagged with the **Escalated to Council** badge (&ge; 2 rejections or severe overdue delay).
   - Review the failure history and exercise council override authority.
3. Navigate to **Applications** (`/applications/1`):
   - Click **Record Statutory Decision**, select `APPROVE`, and record formal council justification.
   - Click **View Sample Order (LoA)** to inspect the generated Letter of Approval with visible `SAMPLE` watermark.

---

## 7. Email Outbox Configuration (`EMAIL_SEND_ENABLED`)

In `.env`:
```ini
# When false (default for hackathon demo): emails stay in database outbox as SUPPRESSED
# and are viewable in the app at /admin/outbox without sending actual SMTP traffic.
EMAIL_SEND_ENABLED=false

# When true: emails are dispatched through configured SMTP credentials
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=demo@aicte.gov.in
SMTP_PASSWORD=secret
```

---

## 8. Phase 7 Innovation Layer (Build Plan v2 Sections 9 & 10)

Phase 7 introduces explainable intelligent decision support for AICTE officers, regional directors, and council leadership. Every smart feature strictly adheres to Section 10 human oversight principles:
- Carries the persistent **"Decision support only"** badge.
- Provides transparent plain-language explanations for all calculations.
- **NEVER** moves, approves, rejects, reverts, or closes an application automatically.

### Key Innovation Features

1. **Explainable Delay Risk Score**:
   - Computes a transparent 0-100 score from 4 database-backed factors:
     - **Age against time limit** (40 pts): AICTE-held working days in current stage divided by SLA, capped at 150%. Paused institution time is strictly excluded.
     - **Past returns** (25 pts): `revert_count` divided by revert cap (default 2).
     - **Officer workload** (20 pts): Open active cases of assigned officer divided by capacity (default 12).
     - **Current stage baseline** (15 pts): Multiplier reflecting inherent logistical complexity (higher for EVC / SAC / SHC).
   - Classified into Low (<40), Medium (40-70), and High (>70) risk bands.
   - Fully inspectable breakdown card on `/applications/[id]` and Admin weights configuration tab on `/settings/rules`.

2. **Bottleneck Finder (`/bottlenecks`)**:
   - Aggregates by stage, region, and officer queue: open cases, average AICTE-held working days, overdue breach rate, and percentage share of total system delay.
   - Separates institutional response time so desk officers are never unfairly penalized.
   - Region-by-stage interactive heat grid and low-sample guards (<3 cases).

3. **Structured AI Case Summary (`/applications/[id]`)**:
   - Structured summary components: case snapshot, timeline highlights, pending items, upcoming deadlines, top delay risk drivers, and suggested next steps for the desk officer.
   - Offline deterministic template summary by default.
   - Optional provider switch in `.env` (Gemini API) to rewrite structured facts in natural prose.
   - SHA-256 payload caching in `case_summaries` table with manual "Regenerate Summary" action.
   - **Strict Privacy Rule**: Transmits only sanitized metadata (stage, dates, counts, deficiency tags, rule codes). Never transmits uploaded file contents or personal data.

4. **What-If Capacity Planner (`/planner`)**:
   - Read-only simulation modeling:
     - (a) Extra EVC visits completed per week (0 to 10)
     - (b) Extra staffing capacity units (0 to 5)
     - Horizon in weeks (1 to 8)
   - Computes counterfactual backlog depletion, queue wait day reductions, cases moving forward, and avoided overdue inspection alerts.
   - **Strict Invariance**: Never alters real database records.

5. **Smart Alert Ranking & Daily Digests (`/alerts`)**:
   - Multi-factor priority score (0-100) combining severity (35%), days overdue (30%), escalation tier (20%), and regulatory impact (15%).
   - Alerts list defaults to explainable priority order with a dedicated "why ranked here" rationale line.
   - "Needs Attention Today" top-10 card on the main dashboard (`/`).
   - Admin action to draft consolidated daily digests in the email outbox (`/admin/outbox`).

---

## 9. Optional LLM Provider Configuration

In `.env`:
```ini
# LLM Provider Configuration (Phase 7 Innovation)
# Default is 'none' (deterministic offline template summary)
LLM_PROVIDER=none
# To enable Gemini API summarization:
# LLM_PROVIDER=gemini
# LLM_API_KEY=your_gemini_api_key_here
# LLM_TIMEOUT_SECONDS=10
```

*Fallback Guarantee*: If `LLM_PROVIDER=none`, `LLM_API_KEY` is missing, or an external API call times out or fails, the system automatically falls back to the deterministic offline template summary without throwing errors. The user interface explicitly labels each summary as either *"Template summary"* or *"AI-assisted summary"*.

---

## 10. Next Steps: Phase 8 (Security Hardening & Final Deliverables)
- Append-only immutable audit log export & signature verification
- Anti-virus / MIME file upload scanner verification
- Configurable statutory record retention rules
- Mock AICTE National Portal adapter
- End-to-end architecture diagram & test verification report

