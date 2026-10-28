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
| **Regional Head (North)** | Er. Sunil Trivedi | `ro.north@aicte.gov.in` | Scoped to Northern RO (UP, UK). Views Dashboard, Applications, EVC Queue, Undertakings, Document Validity, Reports. |
| **Scrutiny Officer** | Amit Sharma | `scrutiny1@aicte.gov.in` | Northern RO Desk. Views Dashboard, Assigned Applications, Undertakings, Document Validity. |
| **EVC Coordinator** | Prof. K. Ramanathan | `evc.coord@aicte.gov.in` | Southern RO Desk. Views Dashboard, Applications, EVC Inspection Queue, Document Validity. |
| **Competent Authority** | Prof. T. G. Sitharam | `chairman@aicte.gov.in` | National Headquarters. High-level dashboard, SAC/SHC review, Reports. |
| **System Admin** | Dr. Rajesh Verma | `admin@aicte.gov.in` | Central HQ. Complete administrative control, APH rules configuration, audit logs. |
| **Institution User** | Dr. V. K. Saxena | `principal@apexkanpur.edu` | Apex Institute of Technology, Kanpur. Scoped strictly to own institution portal (`/portal`). |

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

---

## 5. Running Tests and Verification

```bash
# Run backend test suite (18 unit, RBAC, and workflow engine tests)
make test
# Or: cd backend && .venv/bin/pytest -v

# Run automated end-to-end smoke test suite
make smoke
# Or: ./scripts/smoke_test.sh

# Re-seed 60 synthetic applications with historical transitions
make seed-demo
```

---

## 6. Phase 3 Interactive Demo Walkthrough

### Scenario A: Regulatory Application Dossier & Stage Advance
1. Go to `http://localhost:3000/login` and click **Scrutiny Officer** (Amit Sharma).
2. You land on the Northern RO application queue. Click on any application in `SUBMITTED` or `SCRUTINY` (e.g. `AICTE/2026/APP-10001`).
3. View the **Visual Pathway Stepper**, **SLA Countdown Timer**, and **AI Case Docket Summary**.
4. Click **Complete Stage**, enter verification remarks (e.g. *"Statutory documents verified and cleared"*), and submit. The dossier dynamically advances to the next stage along its APH pathway.

### Scenario B: Deficiency Loop & Revert Cap Enforcement
1. As a Scrutiny Officer, open a scrutiny dossier (e.g. `AICTE/2026/APP-10026`).
2. Click **Return for Clarification**. Select deficiency tags (`DEF_FIRE_NOC`, `DEF_INFRASTRUCTURE`), enter detailed remarks, and submit.
3. The application moves to `RE_SCRUTINY` and increments `revert_count`. Notice that an urgent deficiency communication draft is automatically generated.
4. Open Application `AICTE/2026/APP-10027` (already has 2 reverts). Notice the **Escalation Required** banner indicating the regulatory revert cap was reached.

### Scenario C: Final Decision & Statutory Letter of Approval
1. Log in as **Competent Authority** (Prof. T. G. Sitharam) or **Admin**.
2. Open an application in committee review or scrutiny stage (e.g. `AICTE/2026/APP-10051`).
3. Click **Record Decision**, select **Approve**, enter approval notes, and submit.
4. The application transitions to `APPROVAL_GRANTED`. Click **View Official Order** to preview the rendered Letter of Approval complete with reference number, Council seal, and visible statutory disclaimer watermark:
   > *"SAMPLE - SYNTHETIC DEMO DOCUMENT, NOT AN OFFICIAL AICTE ORDER"*

### Scenario D: Hackathon Demo Clock Time-Travel
1. Notice the floating **Demo Time-Travel Clock** bar on the Applications page (`/applications`).
2. Click **+24 Hours** or **+48 Hours**. The system dynamically updates stage elapsed days and shifts applications from `ON_TIME` to `APPROACHING_DUE` or `OVERDUE`.
3. Click **Reset Clock** to return to real-world UTC time.

---

## 7. Next Step: Phase 4 (Watchers: Alert Rules Engine & Escalation Ladder)

Ready to begin **Phase 4 (Watchers)**:
- Implement the background alert scanner service evaluating 8 pre-seeded statutory rules.
- Implement the 3-tier escalation ladder (Scrutiny Officer $\rightarrow$ Regional Head $\rightarrow$ Member Secretary).
- Implement in-app notifications and email dispatch queue.
- Build the Regional Escalation Matrix and Officer Notifications Center on the frontend.
