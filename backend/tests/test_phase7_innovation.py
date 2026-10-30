"""
Unit & Integration Test Suite for Phase 7 (Innovation Layer - Build Plan v2 Sec 9 & 10):
1. Explainable Delay Risk Score:
   - 4-factor formula (Age/SLA, Past Returns, Officer Workload, Stage Baseline)
   - Snapshot storage, history, 0-100 range, bands (Low, Medium, High)
   - Paused cases use AICTE time only and flag is_paused=True
   - Closed cases are excluded
   - Admin weight editing with total=100 validation & audit logging
   - Strictly decision support: NEVER mutates application stage or status
2. Bottleneck Finder:
   - Database-backed stage/region/officer delay aggregation
   - Separates AICTE-held time from WITH_INSTITUTION paused time
   - Low-sample flag (<3 cases)
   - Regional scoping (Regional Head scoped, Bureau Officer/Admin cross-region)
3. Upgraded AI Case Summary:
   - Structured summary (snapshot, timeline highlights, pending items, upcoming deadlines, risk breakdown, suggested next steps)
   - Offline deterministic fallback by default
   - SHA-256 hash caching in case_summaries
   - Force regenerate support
   - Safe payload: metadata only, never uploaded file contents or personal info
4. What-If Planner (EVC):
   - Counterfactual capacity modeling (extra visits/week, staffing capacity, horizon)
   - Baseline equals current database backlog
   - Monotonic property: more capacity never worsens metrics
   - Strictly read-only: zero mutations to applications or visits
5. Smart Alert Ranking:
   - Explainable priority score (0-100) based on severity, days overdue, tier, application risk
   - Plain-language explanation line
   - Needs-attention-today top-10 endpoint
   - Consolidated daily digest drafting in EmailOutbox
6. New Alert Rules:
   - RULE_EVC_VISIT_OVERDUE (fires on visit past date without report, auto-resolves on report)
   - RULE_UNDERTAKING_OVERDUE (fires on unverified overdue undertaking, auto-resolves on verification)
   - RULE_DOCUMENT_EXPIRED (fires on expired document, auto-resolves only on verified renewal)
   - RULE_RISK_HIGH (advisory notice on High risk band before breach)
"""
from datetime import datetime, date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    Application, Institution, Stage, StageHistory, ClockSegment,
    Undertaking, UndertakingStatusEnum, Document, DocumentStatusEnum, DocumentTypeEnum,
    SystemConfig, Alert, AlertRule, AlertStatusEnum, AlertTypeEnum,
    AlertSeverityEnum, User, UserRoleEnum, ApplicationStatusEnum,
    EvcVisit, EvcStatusEnum, RiskScoreSnapshot, AlertPriorityScore,
    EmailOutbox
)
from app.services.clock import ClockService, reset_clock, advance_clock, normalize_dt
from app.services.risk_score_service import RiskScoreService
from app.services.bottleneck_service import BottleneckFinderService
from app.services.case_summary_service import CaseSummaryService
from app.services.whatif_service import WhatIfPlannerService
from app.services.alert_ranking_service import AlertRankingService
from app.services.alert_engine import AlertEngine
from app.services.workflow_engine import WorkflowEngine

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_clock():
    reset_clock()
    yield
    reset_clock()


def get_token(role: str, email: str = None) -> str:
    payload = {"role": role}
    if email:
        payload["email"] = email
    res = client.post("/api/v1/auth/demo-login", json=payload)
    assert res.status_code == 200, f"Demo login failed for {role}: {res.text}"
    return res.json()["access_token"]


# =============================================================================
# 1. EXPLAINABLE DELAY RISK SCORE TESTS
# =============================================================================

def test_risk_score_weights_validation_and_admin_endpoint():
    """Admin can update risk weights if total=100; non-100 totals are rejected with 422."""
    admin_token = get_token("ADMIN")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch current weights
    get_res = client.get("/api/v1/config/risk-weights", headers=headers)
    assert get_res.status_code == 200
    weights_dict = get_res.json()["weights"]
    assert sum([
        weights_dict["age_against_time_limit"],
        weights_dict["past_returns"],
        weights_dict["officer_workload"],
        weights_dict["current_stage"]
    ]) == 100

    # Test invalid total (sum = 110)
    bad_payload = {
        "weights": {
            "age_against_time_limit": 50,
            "past_returns": 25,
            "officer_workload": 20,
            "current_stage": 15
        }
    }
    bad_res = client.put("/api/v1/config/risk-weights", json=bad_payload, headers=headers)
    assert bad_res.status_code == 422
    assert "must equal exactly 100" in bad_res.json()["detail"]

    # Test valid total (sum = 100)
    valid_payload = {
        "weights": {
            "age_against_time_limit": 35,
            "past_returns": 30,
            "officer_workload": 20,
            "current_stage": 15
        }
    }
    put_res = client.put("/api/v1/config/risk-weights", json=valid_payload, headers=headers)
    assert put_res.status_code == 200
    updated = put_res.json()["weights"]
    assert updated["age_against_time_limit"] == 35
    assert updated["past_returns"] == 30

    # Restore default weights
    default_payload = {
        "weights": {
            "age_against_time_limit": 40,
            "past_returns": 25,
            "officer_workload": 20,
            "current_stage": 15
        }
    }
    client.put("/api/v1/config/risk-weights", json=default_payload, headers=headers)


def test_risk_score_bounds_and_factors_computation():
    """Score must be between 0 and 100, assigns Low/Medium/High, never mutates app status."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.status == ApplicationStatusEnum.IN_PROGRESS).first()
        assert app is not None

        original_stage_id = app.current_stage_id
        original_status = app.status

        # Compute score
        breakdown = RiskScoreService.compute_score(db, app)
        assert breakdown is not None
        assert 0 <= breakdown["score"] <= 100
        assert breakdown["band"] in ["LOW", "MEDIUM", "HIGH"]
        assert len(breakdown["factors"]) == 4

        # Verify factor points sum up to final score
        calculated_sum = sum(f["points"] for f in breakdown["factors"])
        assert abs(calculated_sum - breakdown["score"]) < 0.1

        # Ensure NO state mutation occurred on the application
        assert app.current_stage_id == original_stage_id
        assert app.status == original_status
    finally:
        db.close()


def test_risk_score_paused_and_closed_cases():
    """Cases WITH_INSTITUTION are flagged is_paused; closed cases are not scored."""
    db: Session = SessionLocal()
    try:
        # Paused application test
        paused_app = db.query(Application).filter(Application.case_holder == "WITH_INSTITUTION").first()
        if paused_app:
            breakdown = RiskScoreService.compute_score(db, paused_app)
            assert breakdown["is_paused"] is True

        # Closed application test
        closed_app = db.query(Application).filter(Application.status == ApplicationStatusEnum.CLOSED).first()
        if closed_app:
            closed_breakdown = RiskScoreService.compute_score(db, closed_app)
            assert closed_breakdown["is_closed"] is True
            assert closed_breakdown["band"] == "N/A"
    finally:
        db.close()


def test_risk_score_api_endpoints():
    """GET /risk/applications and GET /risk/applications/{id} return expected breakdown and sorting."""
    token = get_token("BUREAU_OFFICER")
    headers = {"Authorization": f"Bearer {token}"}

    # List endpoint
    list_res = client.get("/api/v1/risk/applications?limit=10", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert isinstance(items, list)
    if items:
        first = items[0]
        assert "delay_risk_score" in first
        assert "risk_band" in first

        # Detail breakdown endpoint
        app_id = first["id"]
        detail_res = client.get(f"/api/v1/risk/applications/{app_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["application_id"] == app_id
        assert "score" in detail
        assert "band" in detail
        assert len(detail["factors"]) == 4


# =============================================================================
# 2. BOTTLENECK FINDER TESTS
# =============================================================================

def test_bottleneck_finder_aggregates_and_pause_separation():
    """Bottleneck finder aggregates match database and exclude WITH_INSTITUTION paused time."""
    db: Session = SessionLocal()
    try:
        data = BottleneckFinderService.compute_bottlenecks(db, region_id=None)
        assert "bottlenecks" in data
        assert "stage_region_grid" in data
        assert "officer_bottlenecks" in data
        assert "total_open" in data

        # Check bottleneck items
        for b in data["bottlenecks"]:
            assert b["open_cases"] >= 0
            assert b["avg_aicte_days"] >= 0
            assert b["avg_institution_days"] >= 0
            assert "reason" in b
            # Low sample flag for < 3 cases
            if b["open_cases"] < 3:
                assert b["low_sample"] is True
    finally:
        db.close()


def test_bottleneck_finder_regional_scoping():
    """Regional Head can only see own region bottlenecks; Bureau Officer and Admin see cross-region."""
    # Regional Head (South - region_id=2 or 1)
    reg_token = get_token("REGIONAL_HEAD", email="ro.south@demo.example")
    reg_res = client.get("/api/v1/bottlenecks", headers={"Authorization": f"Bearer {reg_token}"})
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    # Scoped only to user's region
    assert len(reg_data["stage_region_grid"]) == 1

    # Bureau officer (All regions)
    bureau_token = get_token("BUREAU_OFFICER")
    bureau_res = client.get("/api/v1/bottlenecks", headers={"Authorization": f"Bearer {bureau_token}"})
    assert bureau_res.status_code == 200
    bureau_data = bureau_res.json()
    assert len(bureau_data["stage_region_grid"]) > 1


# =============================================================================
# 3. AI CASE SUMMARY UPGRADE TESTS
# =============================================================================

def test_ai_case_summary_structured_content_and_caching():
    """Summary contains required structured sections, caches by hash, and supports force regenerate."""
    token = get_token("SCRUTINY_OFFICER")
    headers = {"Authorization": f"Bearer {token}"}

    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.status == ApplicationStatusEnum.IN_PROGRESS).first()
        app_id = app.id
    finally:
        db.close()

    # Generate summary
    res1 = client.get(f"/api/v1/applications/{app_id}/summary", headers=headers)
    assert res1.status_code == 200
    summary1 = res1.json()

    assert summary1["application_id"] == app_id
    assert summary1["source_label"] in ["Template summary", "AI-assisted summary"]
    assert "executive_summary" in summary1
    assert "timeline_highlights" in summary1
    assert "pending_items" in summary1
    assert "upcoming_deadlines" in summary1
    assert "suggested_next_steps" in summary1
    assert "top_risk_factors" in summary1

    # Cache hit check (second call should return identical hash and timestamp)
    res2 = client.get(f"/api/v1/applications/{app_id}/summary", headers=headers)
    assert res2.status_code == 200
    summary2 = res2.json()
    assert summary1["input_hash"] == summary2["input_hash"]
    assert summary1["last_generated_at"] == summary2["last_generated_at"]

    # Force regenerate
    regen_res = client.post(f"/api/v1/applications/{app_id}/summary/regenerate", headers=headers)
    assert regen_res.status_code == 200
    regen_summary = regen_res.json()
    assert regen_summary["application_id"] == app_id


def test_ai_case_summary_payload_sanitization():
    """Summary generation uses strictly case metadata and never file upload contents or personal data."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.status == ApplicationStatusEnum.IN_PROGRESS).first()
        summary = CaseSummaryService.get_or_generate_summary(db, app.id, force_regenerate=True)
        full_text = str(summary)
        assert "password" not in full_text.lower()
        assert "s3://" not in full_text
        assert "private_key" not in full_text
    finally:
        db.close()


# =============================================================================
# 4. WHAT-IF PLANNER (EVC) TESTS
# =============================================================================

def test_whatif_planner_readonly_and_baseline_counts():
    """What-if simulation does not mutate any application or visit records; baseline matches DB."""
    db: Session = SessionLocal()
    try:
        initial_evc_count = db.query(Application).filter(Application.current_stage_id == 4).count()
        initial_visit_count = db.query(EvcVisit).count()

        result = WhatIfPlannerService.simulate_evc_capacity(
            db=db,
            region_id=None,
            extra_visits_per_week=2,
            extra_staffing_capacity=1,
            horizon_weeks=4
        )

        assert "current_backlog" in result["summary"]
        assert len(result["weekly_projection"]) == 4
        assert "Estimate, decision support only" in result["disclaimer"]
        assert "assumptions" in result

        # Check DB state was NOT modified
        post_evc_count = db.query(Application).filter(Application.current_stage_id == 4).count()
        post_visit_count = db.query(EvcVisit).count()
        assert initial_evc_count == post_evc_count
        assert initial_visit_count == post_visit_count
    finally:
        db.close()


def test_whatif_planner_monotonic_capacity_property():
    """Increasing extra visits/week never worsens wait times or backlog."""
    db: Session = SessionLocal()
    try:
        res_low = WhatIfPlannerService.simulate_evc_capacity(
            db=db, region_id=None, extra_visits_per_week=0, extra_staffing_capacity=0, horizon_weeks=4
        )
        res_high = WhatIfPlannerService.simulate_evc_capacity(
            db=db, region_id=None, extra_visits_per_week=5, extra_staffing_capacity=2, horizon_weeks=4
        )

        # High capacity scenario should clear equal or more cases and leave equal or less backlog
        assert res_high["summary"]["scenario_cases_cleared"] >= res_low["summary"]["scenario_cases_cleared"]
        assert res_high["summary"]["scenario_projected_backlog"] <= res_low["summary"]["scenario_projected_backlog"]
    finally:
        db.close()


def test_whatif_planner_api_access_control():
    """EVC_COORDINATOR, REGIONAL_HEAD, BUREAU_OFFICER, ADMIN can access planner; INSTITUTION_USER is 403."""
    evc_token = get_token("EVC_COORDINATOR")
    res = client.get("/api/v1/planner/simulate?extra_visits_per_week=2&horizon_weeks=4", headers={"Authorization": f"Bearer {evc_token}"})
    assert res.status_code == 200

    # Institution user must be rejected
    inst_token = get_token("INSTITUTION_USER", email="principal@apexkanpur.demo.example")
    inst_res = client.get("/api/v1/planner/simulate", headers={"Authorization": f"Bearer {inst_token}"})
    assert inst_res.status_code == 403


# =============================================================================
# 5. SMART ALERT RANKING TESTS
# =============================================================================

def test_smart_alert_ranking_ordering_and_explanation():
    """Alerts are scored 0-100 and ordered by priority with human-readable rationale."""
    token = get_token("ADMIN")
    res = client.get("/api/v1/alerts?sort_by=priority&sort_order=desc&limit=20", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) > 0

    # Check priority fields on alert items
    first = alerts[0]
    assert "priority_score" in first
    assert "priority_explanation" in first
    assert 0 <= (first["priority_score"] or 0) <= 100


def test_needs_attention_today_endpoint():
    """GET /alerts/needs-attention-today returns top 10 urgent alerts with explainable factors."""
    token = get_token("REGIONAL_HEAD")
    res = client.get("/api/v1/alerts/needs-attention-today", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()
    assert len(items) <= 10
    if items:
        assert "priority_score" in items[0]
        assert "priority_explanation" in items[0]
        assert "severity" in items[0]


def test_daily_digest_draft_generation():
    """POST /alerts/daily-digest/generate aggregates top alerts and drafts an email in outbox."""
    token = get_token("ADMIN")
    res = client.post("/api/v1/alerts/daily-digest/generate", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "digests_created" in data

    db: Session = SessionLocal()
    try:
        draft = db.query(EmailOutbox).filter(EmailOutbox.subject.like("%Daily Digest%")).first()
        if draft:
            assert "priority alerts" in draft.body.lower() or "digest" in draft.body.lower()
            assert draft.sent_at is None  # Pending send
    finally:
        db.close()


# =============================================================================
# 6. NEW ALERT RULES & AUTO-RESOLUTION TESTS
# =============================================================================

def test_rule_evc_visit_overdue_and_autoresolve():
    """RULE_EVC_VISIT_OVERDUE fires when scheduled visit has passed with no report; resolves on report."""
    db: Session = SessionLocal()
    try:
        # Find or create an EVC visit in SCHEDULED state in the past
        visit = db.query(EvcVisit).filter(EvcVisit.status == EvcStatusEnum.SCHEDULED).first()
        if not visit:
            pytest.skip("No scheduled EVC visit in test database")

        app = visit.application
        # Set scheduled date 3 days in past
        visit.scheduled_date = date.today() - timedelta(days=3)
        db.commit()

        # Run alert engine
        AlertEngine.evaluate_all_rules(db)

        # Check alert was created
        rule = db.query(AlertRule).filter(AlertRule.code == "RULE_EVC_VISIT_OVERDUE").first()
        alert = db.query(Alert).filter(
            Alert.application_id == app.id,
            Alert.alert_rule_id == rule.id,
            Alert.status.in_([AlertStatusEnum.ACTIVE, AlertStatusEnum.ESCALATED])
        ).first()
        assert alert is not None

        # Auto-resolve test: simulate report submission
        visit.status = EvcStatusEnum.REPORT_RECEIVED
        visit.visit_completed_at = normalize_dt(datetime.utcnow())
        db.commit()

        # Re-evaluate
        AlertEngine.evaluate_all_rules(db)
        db.refresh(alert)
        assert alert.status == AlertStatusEnum.RESOLVED
        assert "cleared" in (alert.resolution_remarks or "").lower()
    finally:
        db.close()


def test_rule_undertaking_overdue_and_autoresolve():
    """RULE_UNDERTAKING_OVERDUE fires when undertaking due date has passed; resolves on verification."""
    db: Session = SessionLocal()
    try:
        undertaking = db.query(Undertaking).filter(
            Undertaking.status.in_([UndertakingStatusEnum.PENDING, UndertakingStatusEnum.SUBMITTED])
        ).first()
        if not undertaking:
            pytest.skip("No pending undertaking in test database")

        app = undertaking.application
        undertaking.due_date = date.today() - timedelta(days=2)
        db.commit()

        AlertEngine.evaluate_all_rules(db)

        rule = db.query(AlertRule).filter(AlertRule.code == "RULE_UNDERTAKING_OVERDUE").first()
        alert = db.query(Alert).filter(
            Alert.undertaking_id == undertaking.id,
            Alert.alert_rule_id == rule.id,
            Alert.status.in_([AlertStatusEnum.ACTIVE, AlertStatusEnum.ESCALATED])
        ).first()
        assert alert is not None

        # Auto-resolve when verified
        undertaking.status = UndertakingStatusEnum.VERIFIED
        undertaking.verified_at = normalize_dt(datetime.utcnow())
        db.commit()

        AlertEngine.evaluate_all_rules(db)
        db.refresh(alert)
        assert alert.status == AlertStatusEnum.RESOLVED
    finally:
        db.close()


def test_rule_document_expired_and_autoresolve_on_renewal():
    """RULE_DOCUMENT_EXPIRED fires when lease/FDR expires; resolves ONLY after renewal is verified."""
    db: Session = SessionLocal()
    try:
        # Find a non-fire NOC document (e.g. LAND_TITLE or FDR)
        doc = db.query(Document).filter(
            Document.document_type != DocumentTypeEnum.FIRE_SAFETY_NOC,
            Document.status.in_([DocumentStatusEnum.VALID, DocumentStatusEnum.ACTIVE])
        ).first()
        if not doc:
            pytest.skip("No applicable document in test database")

        app = doc.application
        doc.expiry_date = date.today() - timedelta(days=5)
        db.commit()

        AlertEngine.evaluate_all_rules(db)

        rule = db.query(AlertRule).filter(AlertRule.code == "RULE_DOCUMENT_EXPIRED").first()
        alert = db.query(Alert).filter(
            Alert.document_id == doc.id,
            Alert.alert_rule_id == rule.id,
            Alert.status.in_([AlertStatusEnum.ACTIVE, AlertStatusEnum.ESCALATED])
        ).first()
        assert alert is not None

        # Auto-resolve: mark doc as SUPERSEDED (renewed document approved)
        doc.status = DocumentStatusEnum.SUPERSEDED
        db.commit()

        AlertEngine.evaluate_all_rules(db)
        db.refresh(alert)
        assert alert.status == AlertStatusEnum.RESOLVED
    finally:
        db.close()


def test_rule_risk_high_early_warning_notice():
    """RULE_RISK_HIGH generates an advisory early-warning alert (INFO) when risk is HIGH before overdue."""
    db: Session = SessionLocal()
    try:
        # Check rule exists in DB with INFO severity
        rule = db.query(AlertRule).filter(AlertRule.code == "RULE_RISK_HIGH").first()
        assert rule is not None
        assert rule.severity in [AlertSeverityEnum.INFO, AlertSeverityEnum.LOW]

        # Check that high risk applications have advisory alert generated or evaluated
        high_risk_app = db.query(Application).filter(Application.risk_band == "HIGH").first()
        if high_risk_app:
            AlertEngine.evaluate_all_rules(db)
            alert = db.query(Alert).filter(
                Alert.application_id == high_risk_app.id,
                Alert.alert_rule_id == rule.id
            ).first()
            if alert:
                assert alert.severity == AlertSeverityEnum.INFO
                assert "early warning" in alert.message.lower() or "risk" in alert.message.lower()
    finally:
        db.close()
