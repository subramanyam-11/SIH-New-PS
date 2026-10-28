# 01. Scope and Assumptions

## 1. Project Overview
**SIH26262**: *Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System*.

AICTE processes thousands of institution approval applications annually across diverse pathways specified in the Approval Process Handbook (APH). The statutory approval lifecycle involves Scrutiny/Re-Scrutiny, Expert Visit Committee (EVC) inspections, and Standing Appellate Committee / Standing Hearing Committee (SAC/SHC) hearings. Many approvals carry time-bound undertakings and time-sensitive legal documents (land leases, building safety certificates, AICTE FDRs, fire NOCs).

This platform acts as an **intelligent operational backbone**:
- It tracks pendency, alerts on near-breach deadlines, schedules inspections, and monitors document/undertaking validity.
- **Human-in-the-Loop Principle**: The system *never* replaces statutory committee judgment or authority decisions. Automation routes, alerts, summarizes, and escalates; humans evaluate and decide.
- **APH Configurability**: All timelines, stages, alert thresholds, and escalation hierarchies are defined in configuration tables—never hardcoded.

---

## 2. Scope Matrix (Hackathon Timeline: ~1 Night Build)

Given the hackathon constraint, we divide features into **Full Implementation (Deep)** and **Simple & Working (Functional)** to ensure an impressive, end-to-end working demonstration.

| Module | Scope Level | What We Will Fully Build | What We Keep Simple (Hackathon Pragmatism) | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Module A: Workflow Engine** | **Full** | Dynamic routing across 5 APH paths, stage advancement, mandatory reason-backed revert/return, stage history tracking, and case summary sheet. | Document attachments stored locally/mock S3; OCR is simulated or handled via direct text fields. | Workflow routing is the core requirement of the problem statement. |
| **Module B: Dashboard & Pendency** | **Full** | Multi-role dashboards (Regional Head, Scrutiny Officer, Admin, Authority), aging breakdown, bottlenecks, KPI cards, and filterable tables. | Complex custom drag-and-drop report builders omitted; clean predefined operational views provided. | Visual wow-factor and instant clarity for judges evaluating administrative efficiency. |
| **Module C: EVC Scheduling** | **Simple & Working** | Queue of applications requiring EVC, date picker assignment, committee member count, visit status toggle (Scheduled/Completed), report upload metadata. | Real-time calendar synchronization (Google Cal/Outlook) and multi-factor biometric travel tracking omitted. | Focus on scheduling queue, delay tracking, and alerting. |
| **Module D: Undertakings & Compliance** | **Simple & Working** | Digital undertaking registry with due dates, institution evidence submission interface, officer verification toggle (Accepted/Rejected with remarks). | Digital cryptographic signature (DSC) validation simplified to OTP/status confirmation. | Fully satisfies end-to-end compliance tracking flow. |
| **Module E: Lease & Document Validity** | **Full** | Expiry tracking ledger, 90/60/30/7-day advance expiry warnings, renewal status tracking, and expired document alert triggers. | Automatic third-party land registry API integration is mocked with uploaded certificate metadata. | Document validity is a specific highlighted bottleneck in AICTE operations. |
| **Module F: Notifications & Alerts** | **Simple & Working** | In-app notification center, explainable alert generation via background worker (APScheduler), email simulation (console/SMTP logs). | Heavy SMS gateway integration simulated via webhooks/in-app alert feeds. | Judges can see real-time alerts without dependency on external paid SMS credits. |
| **Innovation Layer** | **Targeted (3-4 Features)** | 1. Delay Risk Score (ML/Heuristic)<br>2. Explainable Alert Badges<br>3. AI Executive Case Summary (LLM)<br>4. EVC What-If / Capacity Indicator. | Heavy deep learning pipelines avoided; fast, explainable, and reliable models chosen. | High innovation scoring during hackathon pitching. |

---

## 3. Key Architectural Decisions

1. **Role of AI/Automation**:
   - *Decision*: Automation is purely advisory and operational. Decisions (Approve, Reject, Revert, Issue Deficiencies) require authenticated user action.
   - *Reason*: Regulatory and legal compliance mandates institutional accountability under APH guidelines.

2. **Configuration Over Hardcoding**:
   - *Decision*: Store stage durations, alert thresholds (e.g., T-3 days for near breach), and escalation contacts in PostgreSQL tables (`system_config`, `stage_paths`, `alert_rules`).
   - *Reason*: The AICTE Approval Process Handbook changes annually; code changes must not be required for rule updates.

3. **Single Source of Truth for State**:
   - *Decision*: Linear, state-machine driven application state transitions recorded in `stage_history` with actor ID, timestamp, from-stage, to-stage, and remarks.
   - *Reason*: Absolute transparency and immutable auditability required during appeals or legal scrutiny.

4. **Synthetic Demo Data**:
   - *Decision*: Use realistic synthetic data covering 5 regions (Northern, Western, Southern, Eastern, Central), 15 institutions, and 60+ applications representing clean, near-breach, overdue, and escalated states.
   - *Reason*: Protects confidentiality and guarantees judges see rich edge cases immediately upon demo launch.

---

## 4. Key Assumptions

1. **Academic Cycle**: The system runs against an annual approval cycle (e.g., Academic Year 2026-2027) with standard application categories (New Technical Institution, Extension of Approval, Increase/Variation in Intake, Introduction of New Courses, Closure).
2. **Regions**: AICTE operates across regional offices (e.g., Northern - Kanpur, Western - Mumbai, Southern - Chennai, South-Western - Bangalore, Eastern - Kolkata). Regional Heads supervise their respective jurisdiction.
3. **Document Categories**: Key tracking documents are Land Lease / Title Deed, Building Plan Approval, Fire Safety NOC, and AICTE FDR / Bank Guarantee.
4. **Identity & Auth**: Mock role-based authentication (JWT) with standard demo switches (one-click login as Admin, Regional Head, Scrutiny Officer, Institution User).

---

## 5. Open Questions for Phase 2 Confirmation

- **Q1**: Do you want one-click demo login buttons (e.g., "Login as Regional Officer", "Login as Institution") on the login page for fast judge walkthroughs? *(Recommended: Yes)*
- **Q2**: For LLM Case Summaries, do we use Gemini API with local fallback template if no API key is provided? *(Recommended: Yes, fallback ensures zero demo failure)*
- **Q3**: Should institutions have self-service upload access to respond to deficiency letters and upload lease renewals directly? *(Recommended: Yes, Institution Portal view)*
