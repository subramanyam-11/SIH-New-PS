# 07. Innovation Layer Plan

To make the AICTE Approval Workflow platform stand out during hackathon judging, we implement **four high-impact, practical innovation features**. Each feature is designed to be fully implemented in a few hours, visually compelling in the demo, and equipped with a bulletproof fallback.

---

## Innovation Feature 1: Predictive Delay Risk Score (ML / Heuristic)

### 1. Purpose
Instead of waiting for an application to breach its SLA, this feature predicts the likelihood of delay *before* the breach occurs, allowing regional officers to intervene early.

### 2. Data Inputs
- Application age (days elapsed since submission).
- Current stage dwell time vs stage SLA.
- Officer backlog (number of active applications currently on the assigned officer's desk).
- Historical revert count (applications with >= 1 revert have an 85% higher probability of delay).
- Document flags (presence of any expiring document or pending deficiency).

### 3. Implementation Approach (Doable in 2-3 Hours)
- Use a lightweight, explainable heuristic scoring model or a pre-fit Scikit-Learn `LogisticRegression` pipeline in FastAPI:
  $$\text{Risk Score} = w_1 \cdot \text{DwellRatio} + w_2 \cdot \text{OfficerLoad} + w_3 \cdot \text{RevertPenalty} + w_4 \cdot \text{DocPenalty}$$
- Scaled from `0.0` (Low Risk - Green) to `1.0` (Critical Risk - Red).
- Generates a list of top 3 contributing risk factors (e.g., `["Officer desk load exceeds 15 cases", "Prior deficiency revert recorded", "Stage dwell time at 75% SLA"]`).

### 4. Demo Walkthrough
- On the Dashboard and Case Dossier, each application displays a color-coded **Risk Meter** (Green < 0.4, Yellow 0.4-0.7, Red > 0.7).
- Hovering or clicking the badge reveals a breakdown: *"High Delay Risk: 84% probability of breaching Scrutiny deadline"*.
- The Regional Head can sort the application table by `Risk Score DESC` to instantly surface hidden bottlenecks.

### 5. Fallback Plan
- If ML pipeline training takes too long or encounters environment errors, fall back to a pure rule-based deterministic scoring function in `backend/app/services/risk_scoring.py` (same output format and UI visualization).

---

## Innovation Feature 2: Explainable Alert Engine (Glass-Box Rules)

### 1. Purpose
Regulatory administrative officers distrust "black-box" alerts. This feature provides a complete, glass-box rationale citing the exact APH handbook clause, the triggering data metric, and the prescribed legal remedy.

### 2. Data Inputs
- Fired alert rule code and rule definition (`alert_rules`).
- Target entity data (application stage duration, document expiry date, EVC delay).
- Configured threshold value vs actual value.
- Statutory citation string (e.g., `APH 2026 Chapter II Clause 2.4.3`).

### 3. Implementation Approach (Doable in 1-2 Hours)
- When an alert is inserted into `alerts` by APScheduler, a helper method `format_explanation()` generates a standardized JSON payload stored in `explanation_meta`.
- A reusable React component `<ExplainableAlertModal />` renders the data clearly with badge icons.

### 4. Demo Walkthrough
- A Regional Officer sees an alert badge: `CRITICAL: Fire Safety NOC Expired`.
- Clicking "Why did this alert fire?" opens a drawer showing:
  - **Rule**: `RULE_FIRE_NOC_EXPIRED`
  - **Condition Evaluated**: `Today (2026-10-27) > Expiry Date (2026-10-15)`
  - **Legal Mandate**: *AICTE Approval Process Handbook 2026, Chapter I, Clause 1.4(g) - Mandatory Fire Safety Certificate*.
  - **Prescribed Action**: *Withhold EoA issuance until Form-B Renewal submitted.*

### 5. Fallback Plan
- Static template dictionary in FastAPI providing predefined explanations for all 8 standard alert codes.

---

## Innovation Feature 3: AI-Assisted Executive Case Summary & E-Docket

### 1. Purpose
Senior committees (SAC/SHC and Competent Authority) struggle to read 50-page application dossiers. This feature generates a concise, 1-page executive brief synthesizing scrutiny observations, EVC findings, undertaking history, and overall compliance rating.

### 2. Data Inputs
- Institution basic details (AICTE ID, category, location, intake).
- Stage timeline history (dates, officers involved, revert reasons).
- EVC inspection remarks and committee recommendations.
- Outstanding undertakings and document validity status.

### 3. Implementation Approach (Doable in 2 Hours)
- A prompt-engineered FastAPI service calling Gemini API (or OpenAI compatible endpoint) via `POST /api/v1/applications/{id}/ai-summary`.
- Output structured in JSON containing:
  - `executive_summary`: 3-paragraph synthesized brief.
  - `key_findings`: Bullet points of infrastructure/faculty status.
  - `compliance_flags`: Highlighted risks or clean status.
  - `recommendation_prompt`: Suggested statutory decision options.

### 4. Demo Walkthrough
- In the Application Dossier, the user clicks the prominent **"Generate AI Case Docket"** button.
- Within 2-3 seconds, a polished, professional executive summary card appears with formatted badges, bulleted committee observations, and a one-click **"Export PDF E-Docket"** button.

### 5. Fallback Plan
- If an API key is missing or offline, use a template-based generator (`services/summary_builder.py`) that deterministically stitches together the application data into the exact same rich markdown/JSON structure. Zero demo disruption.

---

## Innovation Feature 4: EVC Scheduling What-If & Capacity Planner

### 1. Purpose
EVC coordination is often delayed because experts are unavailable or travel routes are inefficient. This feature offers a scheduling assistant that checks date feasibility, expert panel balance, and regional clustering.

### 2. Data Inputs
- Pending EVC applications with geographic coordinates/districts.
- Synthetic expert pool (professors, architects, industry experts) with subject specializations and availability flags.
- Inspection date proposed.

### 3. Implementation Approach (Doable in 2 Hours)
- An endpoint `GET /api/v1/evc/capacity-planner` that checks:
  1. Does the proposed panel have at least 1 Chair + 1 Domain Expert + 1 Architect?
  2. Are any experts double-booked on that date?
  3. Are there other pending institutions in the same district that could be inspected on the same tour? (Tour Optimization Flag).

### 4. Demo Walkthrough
- In the EVC Queue screen, selecting an inspection date suggests available experts and displays a "Tour Optimization Tip": *"Tip: Institution #2 is also in Dehradun (14 km away). Combine both visits for Oct 30-31 to save committee travel overhead."*

### 5. Fallback Plan
- Fixed recommendation suggestions based on district matching in the seed dataset.
