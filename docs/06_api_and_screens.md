# 06. API Specifications and Frontend Screen Blueprint

## 1. REST API Architecture (FastAPI Backend)

All endpoints follow RESTful conventions, returning JSON responses. Standard authentication via Bearer JWT with embedded role claims.

---

### Module A: Workflow Engine & Applications
- `GET /api/v1/applications`: Query applications with filters (`region_id`, `stage_id`, `status`, `officer_id`, `is_overdue`, `search`).
- `GET /api/v1/applications/{id}`: Detailed application dossier including category, assigned officer, stage SLA, and innovation risk score.
- `GET /api/v1/applications/{id}/timeline`: Historical stage audit trail with actor details, timestamps, duration, and deficiency reasons.
- `POST /api/v1/applications/{id}/transition`: Advance application to the next allowable stage in its path.
- `POST /api/v1/applications/{id}/revert`: Revert application to `RE_SCRUTINY` with mandatory `deficiency_tags` and `reason`.
- `POST /api/v1/applications/{id}/reassign`: Reassign application to another officer (Regional Head / Admin only).
- `GET /api/v1/stage-paths`: Retrieve all configurable APH workflow paths and sequences.

---

### Module B: Dashboard & Pendency Analytics
- `GET /api/v1/dashboard/metrics`: High-level summary counters (`total_applications`, `in_scrutiny`, `evc_queue`, `near_breach`, `overdue_escalated`).
- `GET /api/v1/dashboard/aging-breakdown`: Applications grouped by days spent in current stage (`0-3 days`, `4-7 days`, `8-14 days`, `15+ days`).
- `GET /api/v1/dashboard/regional-comparison`: Cross-regional performance breakdown (intake volume, on-time clearance %, average cycle days).
- `GET /api/v1/dashboard/officer-workload`: Active application count and overdue count per officer in a region.
- `GET /api/v1/dashboard/bottlenecks`: Identification of stages with the highest average dwell time vs standard SLA.

---

### Module C: EVC Scheduling & Inspections
- `GET /api/v1/evc/queue`: List of applications in `EVC_PENDING` awaiting panel and date assignment.
- `POST /api/v1/evc/{application_id}/schedule`: Assign visit date, visit type (`PHYSICAL`/`VIRTUAL`), committee chair, and expert panel members.
- `GET /api/v1/evc/visits`: List scheduled and completed inspections with filters (`region_id`, `date_range`, `status`).
- `POST /api/v1/evc/{visit_id}/report`: Upload inspection outcome (`RECOMMENDED`, `DEFICIENCIES_FOUND`, `REJECTED`), report URL, and remarks.

---

### Module D: Undertakings & Compliance
- `GET /api/v1/undertakings`: List undertakings filtered by status (`PENDING_SUBMISSION`, `UNDER_VERIFICATION`, `COMPLIED`, `OVERDUE`).
- `GET /api/v1/institutions/{id}/undertakings`: Undertakings specific to an institution with countdown timers.
- `POST /api/v1/undertakings/{id}/submit-evidence`: Institution endpoint to upload compliance evidence (PDF/photos) and response remarks.
- `POST /api/v1/undertakings/{id}/verify`: Officer endpoint to sign off (`COMPLIED`) or request re-submission with comments.

---

### Module E: Lease & Statutory Document Validity
- `GET /api/v1/documents`: List statutory documents with filter parameters (`institution_id`, `document_type`, `status`, `expiring_in_days`).
- `GET /api/v1/documents/expiry-watchlist`: Prioritized watchlist of documents expiring within 90/60/30/7 days or already expired.
- `POST /api/v1/documents/{id}/renewal`: Submit renewed certificate/lease deed details with new expiry date and verification document.
- `POST /api/v1/documents/{id}/verify-renewal`: Regional officer signoff on verified renewal deed.

---

### Module F: Alerts, Escalations & Reports
- `GET /api/v1/alerts`: Paginated feed of active alerts filtered by `recipient_role`, `severity`, and `status`.
- `GET /api/v1/alerts/{id}/explain`: Returns detailed `explanation_meta` showing rule code, trigger threshold, and APH clause.
- `POST /api/v1/alerts/{id}/acknowledge`: Mark alert acknowledged by the responsible officer.
- `POST /api/v1/alerts/{id}/resolve`: Mark alert resolved with optional action notes.
- `GET /api/v1/notifications`: User-specific in-app notification list with unread counter.
- `PUT /api/v1/notifications/{id}/read`: Mark notification as read.
- `GET /api/v1/reports/export`: Generate consolidated Excel/CSV or PDF summary of regional pendency and compliance.

---

### Innovation Endpoints
- `GET /api/v1/applications/{id}/risk-score`: Computes real-time delay risk score (0.0 to 1.0) and lists contributing factors.
- `POST /api/v1/applications/{id}/ai-summary`: Generates or retrieves executive case summary using LLM integration.
- `GET /api/v1/evc/capacity-planner`: What-if simulation evaluating expert availability and regional travel clustering.

---

## 2. Frontend Screen Blueprint (Next.js Application)

| Screen Name | Route | Target Roles | One-Line Purpose |
| :--- | :--- | :--- | :--- |
| **1. Universal Login & Role Switcher** | `/login` | All Roles | Secure login with convenient one-click demo role switcher for judges. |
| **2. Operations Command Dashboard** | `/dashboard` | Officer, Regional Head, Authority, Admin | Visual operational hub displaying KPIs, stage aging breakdown, bottleneck charts, and urgent action lists. |
| **3. Application Case Dossier & Timeline** | `/applications/[id]` | All Staff Roles | Comprehensive case sheet displaying application details, current stage SLA, visual timeline, and stage progression/revert actions. |
| **4. EVC Scheduling Queue** | `/evc-queue` | EVC Coordinator, Regional Head | Dedicated workbench to inspect pending inspections, schedule visit dates, and assign committee panels. |
| **5. Undertakings Compliance Tracker** | `/undertakings` | Scrutiny Officer, Regional Head, Institution | Central compliance ledger tracking conditional approval commitments, evidence submissions, and verification signoffs. |
| **6. Lease & Document Validity Monitor**| `/document-validity` | All Staff Roles, Institution | High-visibility statutory watchtower tracking land lease, building plan, and fire NOC expiry dates with countdown warnings. |
| **7. APH Rules & Configuration Center** | `/settings/rules` | Admin, Regional Head | Graphical settings panel to adjust stage SLAs, alert thresholds, and escalation delays without touching code. |
| **8. Institution Self-Service Portal** | `/portal` | Institution User | Clean, intuitive applicant interface to track application progress, reply to deficiency notices, and upload lease renewals. |
| **9. Reports & Regional Audit Center** | `/reports` | Regional Head, Competent Authority, Admin | Executive reporting suite featuring cross-regional comparison charts, aging export, and statutory audit logs. |
