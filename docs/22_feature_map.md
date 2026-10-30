# Problem Statement to Architecture & Feature Traceability Map (SIH26262)

This traceability matrix maps every statutory requirement from the Smart India Hackathon problem statement across Modules A to F, the role-based dashboards, security hardening, integration adapters, and evaluation criteria directly to frontend screens, backend REST APIs, automated tests, and documentation.

---

## 1. Statutory Modules Traceability (Modules A to F)

| Module & Requirement | Statutory Logic & Implementation | Frontend Screen(s) | Backend REST API(s) | Automated Test(s) | Reference Documentation |
|:---|:---|:---|:---|:---|:---|
| **Module A: Application Ingestion & Stage Routing** | Auto-routing by category (`NEW_INSTITUTION`, `EXTENSION_APPROVAL`, `CLOSURE`), stage paths, immutable stage history. | `/portal`<br>`/applications`<br>`/applications/[id]` | `POST /api/v1/applications/submit`<br>`GET /api/v1/applications`<br>`POST /api/v1/applications/{id}/advance` | `test_workflow_engine.py`<br>`test_phase5_screens.py` | `docs/04_stage_engine.md`<br>`docs/19_user_guide.md` |
| **Module B: Fair Pendency Clock & Timelines** | AICTE vs Institution clock segments, SLA status computation (`ON_TIME`, `NEAR_BREACH`, `BREACHED`), holiday calendar. | `/applications/[id]`<br>`/portal`<br>`/demo` | `GET /api/v1/applications/{id}/clock-segments`<br>`POST /api/v1/applications/{id}/revert`<br>`POST /api/v1/applications/{id}/respond` | `test_workflow_engine.py`<br>`test_phase6_v2.py` | `docs/05_clock_service.md`<br>`docs/19_user_guide.md` |
| **Module C: Explainable Alert Engine & Escalation** | 12 regulatory rules, working day basis, 3-tier escalation ladder (L1 Scrutiny, L2 Regional Head, L3 Competent Authority). | `/alerts`<br>`/escalation-matrix`<br>`/notifications`<br>`/settings/rules` | `GET /api/v1/alerts`<br>`GET /api/v1/alerts/summary`<br>`POST /api/v1/alerts/{id}/acknowledge`<br>`GET /api/v1/escalation-matrix` | `test_alert_watchers.py`<br>`test_phase5_screens.py` | `docs/06_alert_rules.md`<br>`docs/11_phase4_alerts_report.md` |
| **Module D: EVC Expert Inspections & Panels** | 15 expert pool, conflict-of-interest screening (parent inst, state, past visits), 3-member panel selection, site schedule. | `/evc-queue`<br>`/reports` | `GET /api/v1/evc/visits`<br>`GET /api/v1/evc/visits/{id}/suggested-experts`<br>`POST /api/v1/evc/visits/{id}/assign-panel` | `test_phase5_screens.py`<br>`test_phase6_v2.py` | `docs/08_phase5_screens_report.md` |
| **Module E: Conditional Undertakings & Document Validity** | Conditional approval evidence upload/audit, versioned documents (deeds, FDRs, Fire NOCs), 30/90-day expiry warnings. | `/undertakings`<br>`/document-validity`<br>`/portal/undertakings`<br>`/portal/documents` | `GET /api/v1/undertakings`<br>`POST /api/v1/undertakings/{id}/verify`<br>`GET /api/v1/documents`<br>`POST /api/v1/documents/{id}/verify-renewal` | `test_phase5_screens.py`<br>`test_phase6_v2.py` | `docs/13_phase6_v2_report.md` |
| **Module F: Executive Reports & Bottleneck Finder** | Pendency report, regional performance matrix, stage bottleneck heat grid, what-if capacity planner, CSV/PDF export. | `/reports`<br>`/bottlenecks`<br>`/planner` | `GET /api/v1/reports/pendency`<br>`GET /api/v1/reports/regional-performance`<br>`GET /api/v1/bottlenecks`<br>`GET /api/v1/reports/export/csv` | `test_phase5_screens.py`<br>`test_phase6_v2.py` | `docs/08_phase5_screens_report.md`<br>`docs/13_phase6_v2_report.md` |

---

## 2. Advanced Innovation Features (Phase 7)

| Innovation Capability | Implementation Logic | Frontend Screen(s) | Backend REST API(s) | Automated Test(s) | Reference Documentation |
|:---|:---|:---|:---|:---|:---|
| **Explainable Delay Risk Score** | 0–100 score across 4 transparent factors (age, returns, officer load, baseline); 3 bands: Low (<40), Med (40–69), High (>=70). | `/` (Dashboard)<br>`/applications`<br>`/applications/[id]` | `GET /api/v1/risk/applications`<br>`GET /api/v1/risk/applications/{id}`<br>`POST /api/v1/risk/recompute` | `test_phase7_innovation.py`<br>`test_phase9_polish.py` | `docs/14_phase7_innovation_report.md` |
| **Dynamic Alert Priority Ranking** | Multi-factor prioritization score (severity, overdue days, tier, risk impact); sorts alert queue explainably. | `/alerts` | `GET /api/v1/alerts?sort_by=priority` | `test_phase7_innovation.py` | `docs/14_phase7_innovation_report.md` |
| **Plain-English AI Case Summaries** | Read-only deterministic metadata compiler (optional LLM rewrites summaries with fallback to offline template). | `/applications/[id]` | `GET /api/v1/applications/{id}/summary`<br>`POST /api/v1/applications/{id}/summary/refresh` | `test_phase7_innovation.py` | `docs/14_phase7_innovation_report.md` |
| **What-If Capacity Planner** | Simulates institutional surge (+10% to +100%) or officer hiring/leave; projects regional breach rates without modifying DB. | `/planner` | `POST /api/v1/planner/simulate` | `test_phase7_innovation.py` | `docs/14_phase7_innovation_report.md` |

---

## 3. Security, Hardening & Integration (Phase 8)

| Security Control | Technical Implementation | Frontend Screen(s) | Backend REST API(s) | Automated Test(s) | Reference Documentation |
|:---|:---|:---|:---|:---|:---|
| **Cryptographic Audit Ledger** | SHA-256 blockchain-style hash chain; DB trigger blocks UPDATE/DELETE; 1-click integrity verifier. | `/admin/audit` | `GET /api/v1/audit`<br>`GET /api/v1/audit/verify-integrity`<br>`GET /api/v1/audit/export-csv` | `test_phase8_security.py` | `docs/18_phase8_security_report.md` |
| **Encrypted File Storage** | AES-256-GCM encryption at rest; magic byte verification; EICAR malware string rejection; 10MB limit. | `/applications/[id]`<br>`/undertakings`<br>`/document-validity` | `POST /api/v1/files/upload`<br>`GET /api/v1/files/{id}/download` | `test_phase8_security.py` | `docs/18_phase8_security_report.md` |
| **Mock AICTE National Adapter** | Inbound/outbound REST adapter; HMAC-SHA256 signatures; idempotency keys; 5-minute replay rejection. | `/integration` | `POST /api/v1/integration/inbound/application`<br>`GET /api/v1/integration/status` | `test_phase8_security.py` | `docs/18_phase8_security_report.md` |
| **Statutory Data Retention** | 7-year regulatory retention lifecycle for closed cases; permanent audit log preservation. | `/admin/retention` | `GET /api/v1/retention/preview`<br>`POST /api/v1/retention/archive-closed-cases` | `test_phase8_security.py` | `docs/18_phase8_security_report.md` |
| **Rate Limiting & Account Defense** | 5 failed attempts locks user for 15 minutes; audited Admin unlock endpoint and CLI. | `/login`<br>`/admin/audit` | `POST /api/v1/auth/login`<br>`POST /api/v1/auth/unlock/{user_id}` | `test_phase8_security.py`<br>`test_phase9_polish.py` | `docs/18_phase8_security_report.md` |

---

## 4. Role-Based Screen & Dashboard Access Matrix

| Role Code | Role Name | Allowed Routes / Primary Screens | Scope & Jurisdiction |
|:---|:---|:---|:---|
| `ADMIN` | System Administrator | All 25 screens (`/`, `/applications`, `/alerts`, `/admin/*`, `/settings/rules`, `/integration`, etc.) | National (All 5 Regions) |
| `COMPETENT_AUTHORITY` | Member Secretary / Chairman | `/`, `/applications`, `/alerts`, `/reports`, `/bottlenecks`, `/planner`, `/demo` | National (Final Approval Authority) |
| `REGIONAL_HEAD` | Regional Officer (RO) | `/`, `/applications`, `/alerts`, `/evc-queue`, `/undertakings`, `/document-validity`, `/reports`, `/bottlenecks` | Scoped to Regional Jurisdiction |
| `SCRUTINY_OFFICER` | Scrutiny Officer | `/applications`, `/alerts`, `/undertakings`, `/document-validity` | Scoped to Regional Office Queue |
| `EVC_COORDINATOR` | EVC Coordinator | `/evc-queue`, `/alerts`, `/reports` | Regional Expert Panel Scheduling |
| `COMMITTEE_MEMBER` | SAC / SHC Committee Member | `/committee/my-cases` | Assigned Hearing Dockets Only |
| `INSTITUTION_USER` | Principal / Registrar | `/portal`, `/portal/undertakings`, `/portal/documents` | Scoped to Institution Records Only |

---

## 5. SIH Evaluation Criteria Coverage

| SIH Evaluation Criterion | How It Is Addressed & Grounded | Proof Point / Demo Step |
|:---|:---|:---|
| **1. Innovation & Novelty** | Explainable 4-factor Delay Risk Score (not black-box ML); What-if capacity planner; Fair pendency clock. | Step 3 (Risk Badge) & Step 5 (Paused Clock) |
| **2. Technical Feasibility** | Clean decoupled 3-tier architecture: FastAPI + PostgreSQL + Next.js; sub-65ms endpoint latencies. | Profiled in Phase 9 (`backend/scripts/profile_endpoints.py`) |
| **3. Regulatory Compliance (APH)** | APH statutory clause citation on every alert; working days calendar; deficiency return limits. | Step 4 (Alert Drawer) & Step 5 (Return tags) |
| **4. Security & Data Integrity** | AES-256-GCM file encryption; SHA-256 blockchain-style audit ledger; database-level immutability trigger. | Step 8 & Optional Security Deep-Dive |
| **5. Usability & User Experience** | Calm institutional aesthetic; neutral geometric icons; responsive tablet/mobile layout; 1-click demo personas. | Presenter Guide (`/demo`) & Live UI |
