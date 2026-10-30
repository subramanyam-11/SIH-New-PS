# Operational User Guide & Deployment Manual

> **Project:** AICTE Approval Workflow Automation System (SIH26262)  
> **Status:** Phase 8 Completed  

---

## 1. Quick Setup & Execution

### 1.1 Prerequisites
- **Python 3.9+** (with `pip` and `venv`)
- **Node.js 18+** (with `npm`)
- **PostgreSQL 14+** running locally on port 5432 with database `aicte_workflow`

### 1.2 Setup on macOS / Linux
```bash
# 1. Clone repository and navigate to root
cd "Sih new"

# 2. Run full automated setup
make setup

# 3. Initialize database and seed 60 demo applications
make db-reset
make seed
make seed-demo

# 4. Verify cryptographic audit log integrity
make verify-audit

# 5. Launch both backend and frontend servers
make dev
```
*Backend runs on `http://localhost:8000`. Frontend runs on `http://localhost:3000` (or `http://localhost:3001`).*

### 1.3 Setup on Windows (PowerShell)
```powershell
# 1. Backend environment setup
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Initialize database
python scripts/reset_db.py
python scripts/seed_foundation.py
python scripts/seed_demo.py

# 3. Frontend environment setup
cd ..\frontend
npm install

# 4. Start servers (in separate terminal windows)
# Window 1 (Backend):
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Window 2 (Frontend):
cd frontend
npm run dev
```

---

## 2. Verified Demo Personas & Credentials

> **Notice:** All demo accounts share the uniform password `Password@123` for evaluation ease. When `DEMO_MODE=True`, you can also bypass credential entry using the one-click demo chips on the login screen.

| Role | Name & Title | Email / Username | Default Scope & Region |
| :--- | :--- | :--- | :--- |
| **System Admin** | Dr. Rajesh Verma | `admin@demo.example` | National (All Screens, Security & Settings) |
| **Competent Authority** | Dr. Anand V. Joshi (Competent Authority) | `chairman@demo.example` | National (Final Approval Decisions & Closures) |
| **Regional Head** | Er. Sunil Trivedi | `ro.north@demo.example` | Northern Region (Escalation Tier 2, EVC Approval) |
| **Scrutiny Officer** | Amit Sharma | `scrutiny1@demo.example` | Northern Region (Doc Verification, Stage Return) |
| **EVC Coordinator** | Prof. K. Ramanathan | `evc.coord@demo.example` | Northern Region (3-Member Inspection Panels) |
| **Bureau Officer** | Dr. Alok Verma | `bureau.officer@demo.example` | National (Read-Only Policy & Oversight) |
| **Committee Member** | Dr. Ramesh Sharma (EVC Member) | `evc.member@demo.example` | Assigned Cases (Advisory Observations) |
| **Institution User** | Apex Institute of Technology | `principal@apexkanpur.demo.example` | Kanpur, UP (Self-Service Submissions & Renewals) |

---

## 3. Role-by-Role Action Guides

### 3.1 Institution User (`principal@apexkanpur.demo.example`)
- **Main Goal:** Track institutional approval applications, submit conditional compliance undertakings, and upload document renewals.
- **Key Actions:**
  1. Navigate to **My Applications** (`/portal`) to check stage progress, net pendency days, and revert notices.
  2. If returned for deficiencies, click **Submit Response** to explain remediations and resume the paused pendency clock.
  3. Navigate to **Undertakings** (`/portal/undertakings`) to upload required photo/video evidence for pending compliance items.
  4. Navigate to **Document Validity** (`/portal/documents`) to upload new versions of expiring fire NOCs, FDRs, or lease deeds.

### 3.2 Scrutiny Officer (`scrutiny1@demo.example`)
- **Main Goal:** Review application documentation against APH statutory requirements.
- **Key Actions:**
  1. Access **Applications** (`/applications`) filtered to your region.
  2. Open an application in `SCRUTINY` or `RE_SCRUTINY`. Review the auto-generated **AI Case Summary** and **Dynamic Risk Score**.
  3. Inspect uploaded statutory files (files stream decrypted on demand).
  4. If compliant, click **Mark Stage Complete** to advance to EVC or Regional Review.
  5. If deficiencies exist, click **Return Application**, select statutory deficiency tags, and enter mandatory remarks (pauses the pendency clock).

### 3.3 EVC Coordinator (`evc.coord@demo.example`)
- **Main Goal:** Schedule Expert Visit Committee (EVC) surprise and scheduled inspections.
- **Key Actions:**
  1. Open the **EVC Queue** (`/evc-queue`).
  2. Review cases in `EVC_PENDING`.
  3. Click **Assign Panel**: the system enforces a strict 3-member minimum, filters out experts with city/institution conflicts, and guards against coordinator overload.
  4. Once scheduled, coordinate inspection date and upload the joint committee inspection report.

### 3.4 Regional Head (`ro.north@demo.example`)
- **Main Goal:** Manage regional throughput, act on Tier 2 escalations, and review EVC inspection outcomes.
- **Key Actions:**
  1. Monitor the regional dashboard for SLA breaches and bottleneck warnings (`/bottlenecks`).
  2. Review Tier 2 escalated alerts on the **Alerts** screen (`/alerts`).
  3. Approve EVC inspection reports and forward cases to SAC/SHC or the Competent Authority.
  4. Perform case closure on finalized applications (`/applications/{id}/close`).

### 3.5 Bureau Officer (`bureau.officer@demo.example`)
- **Main Goal:** High-level statutory monitoring and national oversight without operational mutation permissions.
- **Key Actions:**
  1. Inspect national pendency reports (`/reports`).
  2. Run the **What-If Capacity Planner** (`/planner`) to model simulated officer intake scenarios.
  3. View national bottleneck distributions and overdue case rosters.

### 3.6 Committee Member (`evc.member@demo.example`)
- **Main Goal:** Review assigned institutional dossiers and submit advisory recommendations.
- **Key Actions:**
  1. Access **My Committee Cases** (`/committee/my-cases`).
  2. Review the structured institutional briefing, deficiency history, and evidence.
  3. Record decision-support recommendations (`RECOMMEND_APPROVAL`, `RECOMMEND_REJECTION`, or `FURTHER_CLARIFICATION_REQUIRED`).

### 3.7 Competent Authority (Member Secretary / Competent Authority)
- **Main Goal:** Render final statutory decisions and review high-level national escalations.
- **Key Actions:**
  1. Review cases in `SAC_SHC_REVIEW` or final decision stages.
  2. Review the comprehensive **Institution Health Dossier** and risk factors.
  3. Execute final decisions (`APPROVE` or `REJECT`) with formal recorded reasoning.
  4. Review Tier 3 escalated alerts (Member Secretary / Competent Authority level).

### 3.8 System Admin (`admin@demo.example`)
- **Main Goal:** Maintain system integrity, monitor security controls, and inspect audit logs.
- **Key Actions:**
  1. Access **Audit Trail** (`/admin/audit`) and click **Verify Integrity** to validate the SHA-256 cryptographic chain across all rows.
  2. Access **Data Retention** (`/admin/retention`) to adjust statutory thresholds and review non-destructive archival previews.
  3. Access **AICTE Integration** (`/integration`) to inspect adapter status, run test lookups, and review inbound/outbound sync logs.
  4. Configure APH rules, stage durations, and escalation thresholds in **APH Rules** (`/settings/rules`).
