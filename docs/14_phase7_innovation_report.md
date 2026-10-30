# Phase 7 Completion Report: Innovation Layer & Human Oversight

**System:** AICTE Approval Workflow Automation & Compliance Monitoring System (SIH26262)  
**Phase:** 7 (Innovation Layer: Delay Risk Score, Bottleneck Finder, AI Case Summary, What-If Planner, and Smart Alert Ranking)  
**Status:** **APPROVED & FULLY IMPLEMENTED**  
**Build Plan v2 Alignment:** Section 9 (Innovation Layer) & Section 10 (Strict Human Oversight Invariance)

---

## 1. Executive Summary & Statutory Invariance Commitment

Phase 7 implements the intelligence and decision-support layer for the AICTE approval workflow platform. Unlike opaque "black-box" systems, all innovation features in SIH26262 are **transparent, explainable, and mathematically grounded in database state**.

### Strict Human Oversight Invariance Commitment (Plan v2 Section 10)
> **Statutory Safeguard Principle:** Every smart feature carries the reusable, interactive **"Decision support only"** badge. Smart tools inform, explain, rank, and warn; they **NEVER** move, approve, reject, revert, or close an application. Statutory authority remains exclusively in the hands of authorized human officers.

---

## 2. Feature-by-Feature Architecture & Formula Specification

### 2.1 Feature 1: Explainable Delay Risk Score (Plan v2 Section 9.1)
- **Concept:** Predicts the likelihood of an application violating its stage SLA before the breach occurs, providing early intervention warnings.
- **Formula:** A transparent 4-factor composite score (0 to 100), calculated as:

$$\text{Risk Score} = \min\left(100, W_{\text{age}} \cdot R_{\text{age}} + W_{\text{returns}} \cdot R_{\text{returns}} + W_{\text{workload}} \cdot R_{\text{workload}} + W_{\text{stage}} \cdot R_{\text{stage}}\right)$$

- **Default Factor Weights (Stored in `system_config`, editable by Admin, must sum to 100):**
  1. **Age against time limit ($W_{\text{age}} = 40$ points):**
     $$R_{\text{age}} = \min\left(1.5, \frac{\text{AICTE-held working days in stage}}{\text{Stage SLA days}}\right)$$
     *Paused institutional time is strictly excluded.*
  2. **Past returns ($W_{\text{returns}} = 25$ points):**
     $$R_{\text{returns}} = \min\left(1.0, \frac{\text{revert\_count}}{\text{revert\_cap}}\right) \quad (\text{default revert cap} = 2)$$
  3. **Officer workload ($W_{\text{workload}} = 20$ points):**
     $$R_{\text{workload}} = \min\left(1.0, \frac{\text{Active open cases of assigned officer}}{\text{Configurable capacity limit}}\right) \quad (\text{default capacity} = 12)$$
  4. **Current stage baseline ($W_{\text{stage}} = 15$ points):**
     $$R_{\text{stage}} = \text{Per-stage baseline factor from config table} \quad (\text{EVC} = 0.8, \text{SAC/SHC} = 0.8, \text{Scrutiny} = 0.5, \text{Intake} = 0.2)$$

- **Risk Bands:**
  - **LOW**: Score $< 40$
  - **MEDIUM**: $40 \le \text{Score} < 70$
  - **HIGH**: Score $\ge 70$
- **Invariance & State Handling:**
  - `WITH_INSTITUTION`: Displayed with a "Clock Paused" indicator; calculation only counts AICTE-held working days.
  - `CLOSED`: Closed applications are not scored.
  - Snapshot History: Every recomputation writes an immutable record to `risk_score_snapshots` (score, band, factor values, weighted points, config version, timestamp).
- **Statutory Notice on Screen:** *"Rule-based baseline; can be trained on real AICTE data later."*

---

### 2.2 Feature 2: Bottleneck Finder (`/bottlenecks`) (Plan v2 Section 9.2)
- **Concept:** Identifies administrative logjams across stages, regional offices, and individual officer queues.
- **Metrics Computed:**
  - Open applications in queue
  - Average AICTE-held working days vs. Stage SLA
  - Overdue rate (percentage of cases past SLA)
  - Percentage share of total systemic delay days
  - Separate reporting of institutional response time to avoid unfair officer blame
- **Safeguards & Presentation:**
  - **Low Sample Guard:** Any queue or cohort with $< 3$ cases is flagged with a `Low sample` badge.
  - **One-Sentence Reason:** Generated for every detected bottleneck (e.g., *"Scrutiny in Southern RO: 6 cases averaging 6.0 days against 7-day SLA (50.0% overdue, 40.2% of total delay)."*).
  - **Heat Grid:** Visual region-by-stage matrix rendering $\frac{\text{Average AICTE Days}}{\text{SLA}}$ ratios.
  - **Access Scoping:** Visible to Bureau Officer (National), Regional Head (own region), Competent Authority, and Admin.

---

### 2.3 Feature 3: Structured AI Case Summary (`/applications/[id]`) (Plan v2 Section 9.3)
- **Concept:** Condenses multi-page regulatory dossiers into an actionable procedural summary for the desk officer.
- **Structured Sections:**
  1. **Case Snapshot:** Application number, institution category, current stage, case holder, days in queue.
  2. **Timeline Highlights:** Intake date, stage entries, and revert history.
  3. **Pending Items:** Open conditional undertakings, unrenewed documents, or inspection report submissions.
  4. **Upcoming Deadlines:** Days remaining on stage SLA and statutory certificates.
  5. **Risk Assessment:** Current delay risk score and top 2 contributing drivers.
  6. **Suggested Next Steps:** Procedural recommendations tailored to the current stage (e.g., *"Schedule EVC panel"*, *"Verify renewal certificate"*).
- **Deterministic-First Fallback:**
  - The system defaults to an offline, deterministic Python template summary.
  - If `LLM_PROVIDER=gemini` is configured, the model is strictly constrained: it only rewrites the structured metadata into fluent sentences; it cannot hallucinate or invent new regulatory facts.
  - If the LLM call times out or fails, the offline template summary renders seamlessly.
- **Privacy & Caching:**
  - **Metadata-Only Policy:** Transmits only non-PII case metadata (dates, stages, counts, deficiency tags, rule codes). Never transmits uploaded documents or personal data.
  - **SHA-256 Caching:** Output is cached in `case_summaries` keyed by a hash of the input metadata. Includes a manual **"Regenerate Summary"** button.

---

### 2.4 Feature 4: What-If Capacity Planner (`/planner`) (Plan v2 Section 9.4)
- **Concept:** An interactive counterfactual planning simulator enabling regional heads and bureau officers to model how resource adjustments impact the EVC backlog over a 1 to 8 week horizon.
- **Configurable Inputs:**
  - Target Region (or All Regions)
  - Extra EVC visits completed per week ($0$ to $10$)
  - Extra staffing capacity units ($0$ to $5$)
  - Planning horizon ($1$ to $8$ weeks)
- **Simulation Outputs:**
  - **Backlog Depletion Curve:** Baseline projected backlog vs. Scenario projected backlog.
  - **Waiting Time Reduction:** Average days in queue under baseline vs. scenario.
  - **Cases Moving Forward:** Exact table of queued applications that advance under the scenario, ordered by statutory FIFO queue rank and risk score.
  - **Avoided Alerts Counter:** Quantifies overdue EVC inspection alerts prevented by the intervention.
- **Strict Read-Only Invariance:** Counterfactual simulation executes in-memory. It **never modifies real database records**.

---

### 2.5 Feature 5: Smart Alert Ranking & Consolidated Digests (Plan v2 Section 9.5)
- **Concept:** Ranks dozens of active statutory compliance alerts by an explainable urgency index so officers know what needs attention first.
- **Priority Scoring Formula ($0$ to $100$):**
  $$\text{Priority} = \min\left(100, 35 \cdot R_{\text{sev}} + 30 \cdot R_{\text{overdue}} + 20 \cdot R_{\text{tier}} + 15 \cdot R_{\text{impact}}\right)$$
  - **Severity ($35$ pts):** CRITICAL ($1.0$), HIGH ($0.75$), MEDIUM ($0.45$), LOW ($0.25$), INFO ($0.10$).
  - **Days Overdue ($30$ pts):** Days past statutory deadline divided by 10 (capped at $1.0$).
  - **Escalation Tier ($20$ pts):** Tier 3 ($1.0$), Tier 2 ($0.6$), Tier 1 ($0.25$).
  - **Impact ($15$ pts):** Linked application delay risk score ($80\%$) + New institution flag ($20\%$).
- **UI & Outbox Integration:**
  - Default sort on `/alerts` is **Smart Priority**.
  - Shows plain-language ranking rationale: e.g., *"Priority 70.0: CRITICAL severity (35.0/35 pts), 25.0d overdue (30.0/30 pts)"*.
  - **"Needs Attention Today"** top-10 card added to the home dashboard (`/`).
  - **Consolidated Daily Digest Drafts:** Action to generate consolidated officer email drafts in the database outbox (`/admin/outbox`), minimizing email noise.

---

## 3. Statutory Alert Rules Matrix (11 Active Rules + 1 Advisory Rule)

| Rule Code | Monitored Entity | Trigger Condition | Day Basis | Default Severity | Auto-Resolve Condition |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RULE_SCRUTINY_NEAR_BREACH` | `APPLICATION` | Stage time elapsed $\ge$ 80% SLA | Working Days | `MEDIUM` | Stage advanced or clock paused |
| `RULE_SCRUTINY_OVERDUE` | `APPLICATION` | Current time $>$ `stage_due_date` | Working Days | `HIGH` | Stage advanced or clock paused |
| `RULE_EVC_UNSCHEDULED` | `EVC_VISIT` | Status `SCHEDULED` not set within 5d | Calendar Days | `HIGH` | EVC inspection date confirmed |
| `RULE_EVC_VISIT_OVERDUE` *(New)* | `EVC_VISIT` | Inspection date passed with no report | Working Days | `HIGH` | EVC inspection report uploaded |
| `RULE_UNDERTAKING_DUE_15D` | `UNDERTAKING` | Status `PENDING` and due within 15d | Calendar Days | `MEDIUM` | Undertaking marked verified |
| `RULE_UNDERTAKING_OVERDUE` *(New)* | `UNDERTAKING` | Past statutory due date & unverified | Calendar Days | `HIGH` | Undertaking marked verified |
| `RULE_LEASE_90D` | `DOCUMENT` | Land lease / FDR expiring in $\le$ 90d | Calendar Days | `MEDIUM` | Renewal verified by officer |
| `RULE_LEASE_30D` | `DOCUMENT` | Land lease / FDR expiring in $\le$ 30d | Calendar Days | `HIGH` | Renewal verified by officer |
| `RULE_FIRE_NOC_EXPIRED` | `DOCUMENT` | Fire Safety NOC has expired | Calendar Days | `CRITICAL` | Renewal verified by officer |
| `RULE_DOCUMENT_EXPIRED` *(New)* | `DOCUMENT` | Prescribed lease/FDR expired without verified renewal | Calendar Days | `HIGH` | Officer verifies new version |
| `RULE_MULTIPLE_REVERTS` | `APPLICATION` | Revert count reaches $\ge$ 2 | Event/Count | `HIGH` | Application approved/closed |
| `RULE_RISK_HIGH` *(Advisory)* | `APPLICATION` | Delay Risk Score reaches High band ($\ge$ 70) | Rule Score | `INFO` | Risk score drops below 70 |

---

## 4. REST API Endpoint Reference Catalog

| HTTP Method | Endpoint Path | Role Access | Purpose & Features |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/risk/applications` | All authenticated | List applications with risk scores, bands, filter by `risk_band` |
| `GET` | `/api/v1/risk/applications/{id}` | All authenticated | Full 4-factor risk score breakdown, points, and explanation |
| `GET` | `/api/v1/config/risk-weights` | All authenticated | Current factor weights, thresholds, and capacity settings |
| `PUT` | `/api/v1/config/risk-weights` | `ADMIN` | Update factor weights (validates sum == 100, audited) |
| `GET` | `/api/v1/bottlenecks` | Bureau, RO, CA, Admin | Queue bottlenecks, region-by-stage heat matrix, officer queues |
| `GET` | `/api/v1/applications/{id}/summary` | All authenticated | Structured case brief (cached, deterministic or Gemini) |
| `POST` | `/api/v1/applications/{id}/summary/regenerate` | All authenticated | Force recomputation and cache refresh of summary |
| `GET`/`POST` | `/api/v1/planner/simulate` | EVC, RO, Bureau, CA, Admin | Read-only counterfactual EVC capacity simulation |
| `GET` | `/api/v1/alerts` | Scoped by role | Alerts list defaulting to explainable priority score sorting |
| `GET` | `/api/v1/alerts/needs-attention-today` | Scoped by role | Top-10 prioritized alerts for the current officer |
| `POST` | `/api/v1/alerts/daily-digest/generate` | `ADMIN` | Generates consolidated daily digest drafts in email outbox |

---

## 5. Seed Dataset Demographic & Synthetic Skew Distribution

Running `make seed-demo` executes deterministic database seeding across 60 applications (`APP-10001` to `APP-10060`), 12 alert rules, 25 documents, 20 undertakings, and 12 EVC visits.

### Delay Risk Band Distribution (60 Applications)
- **LOW** ($< 40$ points): **27 applications** ($45.0\%$)
- **MEDIUM** ($40-70$ points): **25 applications** ($41.7\%$)
- **HIGH** ($\ge 70$ points): **8 applications** ($13.3\%$)

### Synthetic Skew Note (Documented per Specification)
> **Synthetic Skew Declaration:** To provide realistic demonstration data for the Bottleneck Finder and What-If Planner, a synthetic queue concentration was intentionally seeded in the **Northern Regional Office (Kanpur)** and **Southern Regional Office (Chennai)** EVC queues, and on Scrutiny Desk Officer **Amit Sharma (12 open cases)**. This skew is purely synthetic for demonstration purposes.

### Total Active Alerts Distribution (Post-Seed)
- **Total Open Alerts**: **57**
  - By Severity: `CRITICAL`: 5, `HIGH`: 26, `MEDIUM`: 26
  - By Escalation Tier: Tier 1 (Desk Officer): 57
  - By Rule:
    - `RULE_SCRUTINY_NEAR_BREACH`: 15
    - `RULE_SCRUTINY_OVERDUE`: 8
    - `RULE_UNDERTAKING_DUE_15D`: 6
    - `RULE_UNDERTAKING_OVERDUE`: 4
    - `RULE_FIRE_NOC_EXPIRED`: 5
    - `RULE_DOCUMENT_EXPIRED`: 2
    - `RULE_LEASE_90D`: 5
    - `RULE_LEASE_30D`: 5
    - `RULE_EVC_UNSCHEDULED`: 4
    - `RULE_EVC_VISIT_OVERDUE`: 2
    - `RULE_MULTIPLE_REVERTS`: 1

---

## 6. Test Suite & Verification Results

### Backend Test Suite (`pytest`): 73 of 73 Tests Passed (100%)
- **Legacy Regression Suite (55 tests)**: All Phase 1 through Phase 6 tests continue to pass without regression.
- **Phase 7 Innovation Suite (`test_phase7_innovation.py`, 18 tests)**:
  1. `test_risk_score_weights_validation_and_admin_endpoint`: Validates total == 100 constraint and Admin PUT audit log.
  2. `test_risk_score_bounds_and_factors_computation`: Validates score remains 0-100 across boundary conditions.
  3. `test_risk_score_paused_and_closed_cases`: Confirms paused cases exclude institution time and closed cases are not scored.
  4. `test_risk_score_api_endpoints`: Validates GET `/risk/applications` filtering and GET `/risk/applications/{id}` breakdown.
  5. `test_bottleneck_finder_aggregates_and_pause_separation`: Verifies direct database aggregates and institution time separation.
  6. `test_bottleneck_finder_regional_scoping`: Enforces regional jurisdiction visibility.
  7. `test_ai_case_summary_structured_content_and_caching`: Validates structured format, privacy, and SHA-256 caching.
  8. `test_ai_case_summary_payload_sanitization`: Verifies no file contents or PII are transmitted.
  9. `test_whatif_planner_readonly_and_baseline_counts`: Confirms simulation is read-only and baseline matches database.
  10. `test_whatif_planner_monotonic_capacity_property`: Confirms more visits never worsens backlog or wait times.
  11. `test_whatif_planner_api_access_control`: Validates role-based permissions (blocked for Institution User).
  12. `test_smart_alert_ranking_ordering_and_explanation`: Confirms deterministic ordering and plain-language rationale.
  13. `test_needs_attention_today_endpoint`: Verifies top-10 role-based prioritization.
  14. `test_daily_digest_draft_generation`: Verifies outbox batching of consolidated officer digests.
  15. `test_rule_evc_visit_overdue_and_autoresolve`: Fired when visit date passes; auto-resolves on report receipt.
  16. `test_rule_undertaking_overdue_and_autoresolve`: Fired past due date; auto-resolves on verification.
  17. `test_rule_document_expired_and_autoresolve_on_renewal`: Fired past expiry; auto-resolves on verified renewal.
  18. `test_rule_risk_high_early_warning_notice`: Fired when score $\ge 70$; low severity warning notice.

### Smoke Test Script (`smoke_test.sh`): 28 of 28 Steps Passed (100%)
- Fully automated regression and end-to-end integration covering Phase 1 through Phase 7.

### Frontend Production Build (`npm run build`): Zero Errors
- Compiled all 21 Next.js 14 App Router routes with static optimization and TypeScript type safety.

---

## 7. Traceability Mapping to Build Plan v2

| Build Plan v2 Section | Requirement Description | Implementation Mapping |
| :--- | :--- | :--- |
| **Section 9.1** | Transparent Rule-Based Delay Risk Score | `app/services/risk_score_service.py`, `app/api/v1/risk.py`, `/applications/[id]` card, `/settings/rules` tab |
| **Section 9.2** | Automated Bottleneck Finder & Heat Grid | `app/services/bottleneck_service.py`, `app/api/v1/bottlenecks.py`, `/bottlenecks` page |
| **Section 9.3** | AI Case Brief & Privacy-Preserving Summaries | `app/services/case_summary_service.py`, `app/api/v1/applications.py`, `/applications/[id]` summary card |
| **Section 9.4** | What-If Capacity & Tour Planner (EVC) | `app/services/whatif_service.py`, `app/api/v1/planner.py`, `/planner` page |
| **Section 9.5** | Smart Alert Prioritization & Officer Digests | `app/services/alert_ranking_service.py`, `app/api/v1/alerts.py`, `/alerts` priority table, Dashboard cards |
| **Section 10** | Strict Human Oversight & Statutory Invariance | `DecisionSupportBadge.tsx` across all innovation views; zero automated decision-making |

---

## 8. Demo Script for Evaluators & Judges (Steps 3 & 4)

1. **Step 1: Early-Warning Delay Risk Detection**
   - Log in as **Regional Head (North)** (`ro.north@demo.example`).
   - On the Dashboard, review the **"Highest Delay Risk Cases"** card.
   - Click into a high-risk dossier (e.g. `APP-10045`, Risk Score: $84$).
   - Inspect the **Risk Breakdown** card: observe the exact 4-factor sentence (*"Open for 14 of 10 working days, so 40 of 40 points..."*) and the prominent **"Decision support only"** badge.
2. **Step 2: Time Travel & Alert Escalation**
   - In the top bar, advance the demo clock by **+7 Days (+168h)**.
   - Click **Run Checks Now**.
   - Notice that the early risk warning materialized into an active SLA breach. Alert `RULE_SCRUTINY_OVERDUE` escalates from Tier 1 (Officer) to Tier 2 (Regional Head) and Tier 3 (Competent Authority).
3. **Step 3: Bottleneck Identification**
   - Click **Bottlenecks** (`/bottlenecks`) in the sidebar.
   - View the ranked logjams, the interactive region-by-stage heat matrix, and notice that institutional response time is cleanly isolated from AICTE processing time.
4. **Step 4: Procedural AI Case Summary**
   - Open any application dossier (`/applications/[id]`).
   - Review the **Case Brief & Procedural Summary** card. Notice the **"Template summary"** source label, structured timeline highlights, pending covenants, and suggested next steps.
   - Click **Regenerate Summary** to observe instant cache refresh.
5. **Step 5: Interactive What-If Capacity Simulation**
   - Navigate to **Capacity Planner** (`/planner`).
   - Drag the **Extra Visits per Week** slider to `+4` and **Extra Staffing Units** to `+2`.
   - Click **Run Counterfactual Simulation**.
   - Observe the projected backlog drop to 0, queue wait times fall by 80%, and inspect the specific cases that move forward in the simulation table, all labeled *"Estimate, decision support only"*.
6. **Step 6: Smart Alert Priority & Daily Digest**
   - Navigate to **Alerts** (`/alerts`).
   - Observe alerts sorted by **Priority Score** ($70.0$, $64.5$, etc.) with a clear explanation line under each alert (*"Rank rationale: CRITICAL severity (35.0/35 pts), 25.0d overdue..."*).
   - As Admin, click **Draft Officer Daily Digests** and verify consolidated notification drafts queued in the email outbox.
