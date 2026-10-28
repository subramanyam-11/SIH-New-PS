# 08. Team Split, Timeline, and Phase Checklists

This execution plan organizes a 5-member team across Phases 2 through 7 for the overnight build. Each phase has a clear, unambiguous checklist.

---

## 1. Team Role Allocation

| Member | Designated Role | Primary Ownership Areas |
| :--- | :--- | :--- |
| **Member 1** | **Backend Lead** | FastAPI setup, PostgreSQL migrations, workflow state engine, REST endpoints, database queries. |
| **Member 2** | **Frontend Lead** | Next.js architecture, Tailwind UI design system, Recharts data visualization, core screens. |
| **Member 3** | **AI / ML & Engine Specialist** | Delay Risk Score model, Explainable Alerts logic, Gemini LLM API integration, APScheduler watchers. |
| **Member 4** | **Integration & QA Lead** | API-Frontend wiring, seed dataset loading, edge-case testing, error handling, demo environment stability. |
| **Member 5** | **Presenter & Documentation Lead**| Hackathon pitch deck, problem-to-solution narrative, demo script rehearsal, live demo data setup. |

---

## 2. Phase-by-Phase Roadmap and Checklists

```
Phase 2: Foundation ─────────► Phase 3: Core Engine ────────► Phase 4: Watchers
 (Setup, DB, Auth)             (Workflow, State Machine)       (APScheduler, Escalations)
                                                                       │
Phase 7: Polish & Rehearse ◄── Phase 6: Innovation Layer ◄── Phase 5: Screens
 (Pitch Deck, Live Dry Run)    (AI Summary, Risk Score)        (Dashboard, Dossier, EVC)
```

---

### Phase 2: Foundation (Hours 0.0 - 2.0)
*Goal: Scaffold repositories, instantiate PostgreSQL, run schema, and establish multi-role authentication.*

- [ ] **Backend Lead**:
  - [ ] Initialize `backend/` with FastAPI, SQLAlchemy/SQLModel, Pydantic, and Alembic or raw SQL runner.
  - [ ] Execute `db/schema.sql` against local/cloud PostgreSQL.
  - [ ] Create JWT authentication endpoints (`/api/v1/auth/login`, `/api/v1/auth/me`).
  - [ ] Implement fast-switch demo token generation for all 6 roles.
- [ ] **Frontend Lead**:
  - [ ] Initialize `frontend/` using Next.js 14 (App Router), Tailwind CSS, Lucide icons, and Axios/Fetch client.
  - [ ] Implement global color palette: AICTE Navy (`#0f2b5c`), Saffron accent (`#f97316`), and clean slate cards.
  - [ ] Build `/login` screen with one-click quick-login role chips (Admin, Regional Head, Scrutiny Officer, Institution).
- [ ] **Integration & QA**:
  - [ ] Verify database connection string and cross-origin CORS settings.
  - [ ] Load base lookup data (`regions`, `roles`, `application_categories`, `stages`, `stage_paths`).
- [ ] **Presenter**:
  - [ ] Draft slide structure (Problem Context, Ministry Pain Points, Solution Architecture, Live Demo).

---

### Phase 3: Core Engine (Hours 2.0 - 4.0)
*Goal: Build the state machine, stage transition rules, and revert logic.*

- [ ] **Backend Lead**:
  - [ ] Implement application CRUD and filtering by region/stage/officer.
  - [ ] Implement state transition engine (`POST /applications/{id}/transition`): validate path order and permissions.
  - [ ] Implement revert endpoint (`POST /applications/{id}/revert`): enforce mandatory `deficiency_tags` and `reason`.
  - [ ] Record all movements in `stage_history`.
- [ ] **Frontend Lead**:
  - [ ] Build base layout (`Sidebar`, `Header`, role badge, and notification bell).
  - [ ] Build `/applications/[id]` Case Dossier: application metadata card, status chip, and APH path stepper.
  - [ ] Build interactive "Advance Stage" and "Revert with Deficiencies" modal dialogs.
- [ ] **AI / ML Specialist**:
  - [ ] Implement heuristic/ML delay risk scoring module (`services/risk_scoring.py`).
  - [ ] Compute baseline risk score on application insert or update.
- [ ] **Integration & QA**:
  - [ ] Test Scrutiny -> Re-Scrutiny -> Clarification -> Scrutiny roundtrip.
  - [ ] Ensure non-authorized roles are blocked from triggering invalid stage transitions.

---

### Phase 4: Watchers & Alert Engine (Hours 4.0 - 6.0)
*Goal: Implement APScheduler background jobs, explainable alert generation, and the 3-tier escalation ladder.*

- [ ] **Backend Lead & AI Specialist**:
  - [ ] Configure `APScheduler` inside FastAPI lifespan.
  - [ ] Create `job_check_stage_slas()`: detects SLA breaches and near-breach conditions.
  - [ ] Create `job_check_document_expiries()`: detects 90/60/30/7-day lease/NOC warnings.
  - [ ] Create `job_check_undertakings()`: flags delinquent conditional approvals.
  - [ ] Implement 3-tier escalation promotion logic (`escalate_stalled_alerts()`).
- [ ] **Frontend Lead**:
  - [ ] Build Notification Dropdown component with live unread counter.
  - [ ] Build `<ExplainableAlertModal />`: displays rule code, actual vs threshold values, and APH legal citation.
- [ ] **Integration & QA**:
  - [ ] Run synthetic seed script (`db/seed_plan.md`) populating 15 institutions and 60 applications with pre-baked alerts.
  - [ ] Verify that near-breach and overdue badges render accurately.

---

### Phase 5: Frontend Screens & Workbenches (Hours 6.0 - 8.5)
*Goal: Build dedicated operational screens for all key administrative modules.*

- [ ] **Frontend Lead & Backend Lead**:
  - [ ] Screen 1: `/dashboard` (KPI stat cards, Aging Breakdown bar chart, Regional Comparison chart, Bottleneck heatmap).
  - [ ] Screen 2: `/evc-queue` (List of applications needing inspection, Date Picker, Committee Panel assignment modal).
  - [ ] Screen 3: `/undertakings` (Digital condition ledger, institution evidence submission, officer verification toggle).
  - [ ] Screen 4: `/document-validity` (Lease & Fire NOC expiry tracker, color-coded countdown days, renewal upload).
  - [ ] Screen 5: `/settings/rules` (View & edit stage SLAs, alert threshold days, and escalation delays).
  - [ ] Screen 6: `/portal` (Clean view for applicant institutions: stepper, deficiency responses, upload docs).
- [ ] **Integration & QA**:
  - [ ] Perform responsive layout testing and check filter operations across all tables.

---

### Phase 6: Innovation Layer (Hours 8.5 - 10.5)
*Goal: Deliver the 4 standout features with zero-fail fallbacks.*

- [ ] **AI / ML Specialist**:
  - [ ] Deploy Gemini LLM Executive Case Summary service (`services/ai_summary.py`) with template fallback.
  - [ ] Add Risk Score visualization widget with top 3 contributing factors on the Case Dossier screen.
  - [ ] Connect Explainable Alert badges across all screens.
  - [ ] Implement EVC Capacity & Tour Optimization tip in the EVC Scheduling view.
- [ ] **Frontend Lead**:
  - [ ] Integrate "Generate AI Case Docket" button with rich markdown rendering and PDF export preview.
- [ ] **Integration & QA**:
  - [ ] Test offline/fallback resilience (ensure UI does not hang if Gemini API key is unset).

---

### Phase 7: Polish, Seed Verification, and Demo Rehearsal (Hours 10.5 - 12.0)
*Goal: Eliminate bugs, ensure visual excellence, and rehearse the winning pitch narrative.*

- [ ] **Entire Team**:
  - [ ] Run through the complete 5-minute hackathon demo story:
    1. *Login as Regional Head North*: Spot high-risk overdue application in Scrutiny.
    2. *Open Explainable Alert*: Show APH clause 2.3 citation.
    3. *Switch to Scrutiny Desk*: Review dossier, raise deficiency (Revert), and note mandatory reason requirement.
    4. *Switch to Institution Portal*: Show instant notification, reply to deficiency, and check Land Lease countdown (28 days left).
    5. *Switch to EVC Coordinator*: Show EVC queue, assign expert panel with Tour Optimization hint.
    6. *Switch to Competent Authority*: Generate 1-click AI Executive Case Docket for council hearing.
  - [ ] Verify all Recharts graphs animate cleanly.
  - [ ] Finalize pitch deck and architecture summary slides.
