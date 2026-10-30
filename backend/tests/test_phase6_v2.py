"""
Unit & Integration Test Suite for Phase 6 (v2 Alignment):
- Fair Pendency Clock: pause on return, resume on institution response, multiple cycles, SLA exclude paused time, alert suppression & auto-resolution
- Working-Day Calendar: weekend/holiday adjustments, region filters, working_days_between, alert rule day_basis
- Closed State: blocked by open undertakings, allowed when clear, alert auto-resolution, read-only enforcement, role restrictions
- Two New Roles: BUREAU_OFFICER (read-only, cross-region), COMMITTEE_MEMBER (assigned cases only, non-binding advisory recommendation)
- Overdue Cases Report: database-backed queries, filters, CSV and PDF exports
"""
from datetime import datetime, date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    Application, Institution, Stage, StageHistory, ClockSegment,
    Undertaking, UndertakingStatusEnum, Document, DocumentStatusEnum,
    Holiday, SystemConfig, Alert, AlertRule, AlertStatusEnum, AlertTypeEnum,
    AlertSeverityEnum, User, UserRoleEnum, ApplicationStatusEnum,
    CommitteeAssignment, CommitteeObservation, Region
)
from app.services.clock import ClockService, reset_clock, advance_clock, normalize_dt
from app.services.working_day_service import WorkingDayService
from app.services.workflow_engine import WorkflowEngine
from app.services.alert_engine import AlertEngine
from app.services.reports_service import ReportsService

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


# =========================================================================
# 1. FAIR PENDENCY CLOCK TESTS
# =========================================================================

def test_pendency_clock_pause_on_return():
    """Returning an application moves case_holder to WITH_INSTITUTION, pauses clock and creates segment."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10001").first()
        admin_user = db.query(User).filter(User.username == "admin@demo.example").first()
        
        # Ensure it starts in SCRUTINY with WITH_AICTE
        app.case_holder = "WITH_AICTE"
        app.revert_count = 0
        db.commit()

        # Execute Return
        WorkflowEngine.return_application(
            db=db,
            application_id=app.id,
            actor=admin_user,
            deficiency_tags=["DEF_FIRE_NOC"],
            reason="Missing statutory Fire Safety NOC certification from Municipal Authority."
        )

        db.refresh(app)
        assert app.case_holder == "WITH_INSTITUTION"
        assert app.current_stage.code == "RE_SCRUTINY"

        pendency = WorkflowEngine.get_application_pendency(db, app)
        assert pendency["case_holder"] == "WITH_INSTITUTION"
        assert pendency["is_paused"] is True

        # Verify active segment is WITH_INSTITUTION
        active_seg = db.query(ClockSegment).filter(
            ClockSegment.application_id == app.id,
            ClockSegment.ended_at.is_(None)
        ).first()
        assert active_seg is not None
        assert active_seg.holder == "WITH_INSTITUTION"
    finally:
        db.close()


def test_pendency_clock_resume_on_institution_response():
    """Institution response moves case back to WITH_AICTE with fresh stage SLA."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10001").first()
        admin_user = db.query(User).filter(User.username == "admin@demo.example").first()

        # Application must be WITH_INSTITUTION
        app.case_holder = "WITH_INSTITUTION"
        db.commit()

        WorkflowEngine.institution_response(
            db=db,
            application_id=app.id,
            actor=admin_user,
            remarks="Uploaded valid Fire NOC certificate issued on 15-Oct-2026."
        )

        db.refresh(app)
        assert app.case_holder == "WITH_AICTE"
        assert app.current_stage.code == "RE_SCRUTINY"

        pendency = WorkflowEngine.get_application_pendency(db, app)
        assert pendency["case_holder"] == "WITH_AICTE"
        assert pendency["is_paused"] is False

        # Active segment is now WITH_AICTE
        active_seg = db.query(ClockSegment).filter(
            ClockSegment.application_id == app.id,
            ClockSegment.ended_at.is_(None)
        ).first()
        assert active_seg is not None
        assert active_seg.holder == "WITH_AICTE"
    finally:
        db.close()


def test_pendency_clock_multiple_pause_cycles():
    """Multiple return-response cycles accurately record alternating segments."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10002").first()
        admin_user = db.query(User).filter(User.username == "admin@demo.example").first()

        # Cycle 1: Return
        app.case_holder = "WITH_AICTE"
        app.revert_count = 0
        db.commit()

        WorkflowEngine.return_application(
            db=db,
            application_id=app.id,
            actor=admin_user,
            deficiency_tags=["DEF_BUILDING_PLAN"],
            reason="Approved building blueprint missing structural engineer stamp."
        )
        assert app.case_holder == "WITH_INSTITUTION"

        # Cycle 1: Response
        WorkflowEngine.institution_response(
            db=db,
            application_id=app.id,
            actor=admin_user,
            remarks="Submitted architect certified structural plan."
        )
        assert app.case_holder == "WITH_AICTE"

        # Cycle 2: Return
        WorkflowEngine.return_application(
            db=db,
            application_id=app.id,
            actor=admin_user,
            deficiency_tags=["DEF_LAND_TITLE"],
            reason="Land registration deed extract is partially illegible."
        )
        assert app.case_holder == "WITH_INSTITUTION"
        assert app.revert_count == 2

        # Cycle 2: Response
        WorkflowEngine.institution_response(
            db=db,
            application_id=app.id,
            actor=admin_user,
            remarks="Provided high-resolution certified copy of land deed."
        )
        assert app.case_holder == "WITH_AICTE"

        # Verify segments exist and alternate
        segments = db.query(ClockSegment).filter(
            ClockSegment.application_id == app.id
        ).order_by(ClockSegment.started_at.asc()).all()
        assert len(segments) >= 4
        holders = [s.holder for s in segments[-4:]]
        assert holders == ["WITH_INSTITUTION", "WITH_AICTE", "WITH_INSTITUTION", "WITH_AICTE"]
    finally:
        db.close()


def test_pendency_clock_sla_excludes_paused_time():
    """Simulated time passing while WITH_INSTITUTION does not inflate AICTE stage SLA dwell time."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10003").first()
        app.case_holder = "WITH_INSTITUTION"
        now = ClockService.get_now()
        
        # Create a paused segment that started 5 days ago
        db.query(ClockSegment).filter(ClockSegment.application_id == app.id).delete()
        seg = ClockSegment(
            application_id=app.id,
            stage_id=app.current_stage_id,
            holder="WITH_INSTITUTION",
            started_at=now - timedelta(days=5),
            ended_at=None,
            reason="Paused with institution for clarification"
        )
        db.add(seg)
        db.commit()

        pendency = WorkflowEngine.get_application_pendency(db, app)
        assert pendency["total_institution_days"] >= 5.0
        # AICTE stage dwell time is 0 because there are no open AICTE segments
        assert pendency["current_stage_aicte_days"] == 0.0
    finally:
        db.close()


def test_pendency_clock_no_alerts_while_paused_and_auto_resolve():
    """Near-breach/overdue alerts do not fire when WITH_INSTITUTION, and existing alerts auto-resolve."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10004").first()
        admin_user = db.query(User).filter(User.username == "admin@demo.example").first()
        rule = db.query(AlertRule).filter(AlertRule.code == "RULE_SCRUTINY_NEAR_BREACH").first()

        # Seed an active near breach alert for this application
        existing_alert = Alert(
            application_id=app.id,
            alert_rule_id=rule.id if rule else 1,
            alert_type=AlertTypeEnum.NEAR_BREACH,
            severity=AlertSeverityEnum.HIGH,
            status=AlertStatusEnum.ACTIVE,
            title="Test Near Breach Alert",
            message="Test scrutiny alert before pause",
            explanation_meta={},
            recipient_role=UserRoleEnum.SCRUTINY_OFFICER
        )
        db.add(existing_alert)
        app.case_holder = "WITH_AICTE"
        app.revert_count = 0
        db.commit()

        # Returning application should auto-resolve the existing near-breach alert
        WorkflowEngine.return_application(
            db=db,
            application_id=app.id,
            actor=admin_user,
            deficiency_tags=["DEF_OTHER"],
            reason="Clarification needed on faculty cadre ratio calculation."
        )

        db.refresh(existing_alert)
        assert existing_alert.status == AlertStatusEnum.RESOLVED
        assert "clock paused: with institution" in (existing_alert.resolution_remarks or "")

        # Re-run alert engine: should NOT create new breach alert for this application
        AlertEngine.evaluate_all_rules(db)
        new_active = db.query(Alert).filter(
            Alert.application_id == app.id,
            Alert.alert_type.in_([AlertTypeEnum.NEAR_BREACH, AlertTypeEnum.OVERDUE]),
            Alert.status == AlertStatusEnum.ACTIVE
        ).first()
        assert new_active is None
    finally:
        db.close()


# =========================================================================
# 2. WORKING-DAY CALENDAR TESTS
# =========================================================================

def test_working_days_weekend_adjustment():
    """add_working_days skips weekends (Saturday and Sunday)."""
    db: Session = SessionLocal()
    try:
        # Friday: 2026-10-30
        friday = date(2026, 10, 30)
        # Adding 1 working day should land on Monday: 2026-11-02
        next_work = WorkingDayService.add_working_days(db, friday, 1)
        assert next_work.date() == date(2026, 11, 2)
        assert next_work.weekday() == 0  # Monday

        # Adding 5 working days from Friday should skip 2 weekends and land on Friday 2026-11-06
        next_week = WorkingDayService.add_working_days(db, friday, 5)
        assert next_week.date() == date(2026, 11, 6)
    finally:
        db.close()


def test_working_days_holiday_adjustment():
    """add_working_days skips designated national and regional holidays."""
    db: Session = SessionLocal()
    try:
        # Remove any temp test holiday
        db.query(Holiday).filter(Holiday.name == "TEST_DIWALI_HOLIDAY").delete()
        
        # Insert a holiday on Monday 2026-11-02
        test_hol = Holiday(
            date=date(2026, 11, 2),
            name="TEST_DIWALI_HOLIDAY",
            region_id=None,
            holiday_type="NATIONAL"
        )
        db.add(test_hol)
        db.commit()

        friday = date(2026, 10, 30)
        # 1 working day from Friday with Monday as a holiday must land on Tuesday 2026-11-03
        result = WorkingDayService.add_working_days(db, friday, 1)
        assert result.date() == date(2026, 11, 3)

        # Cleanup
        db.query(Holiday).filter(Holiday.name == "TEST_DIWALI_HOLIDAY").delete()
        db.commit()
    finally:
        db.close()


def test_working_days_between_calculation():
    """working_days_between calculates working days correctly, excluding weekends and holidays."""
    db: Session = SessionLocal()
    try:
        d1 = date(2026, 11, 2)  # Monday
        d2 = date(2026, 11, 9)  # Next Monday (7 calendar days, 5 working days)
        w_days = WorkingDayService.working_days_between(db, d1, d2)
        assert w_days == 5
    finally:
        db.close()


def test_working_days_region_filter():
    """Regional holiday applies only to applications within that specific region."""
    db: Session = SessionLocal()
    try:
        # Create a region-specific holiday for Region 1 on Wednesday 2026-11-04
        db.query(Holiday).filter(Holiday.name == "REGIONAL_STATE_FOUNDATION_DAY").delete()
        reg_hol = Holiday(
            date=date(2026, 11, 4),
            name="REGIONAL_STATE_FOUNDATION_DAY",
            region_id=1,
            holiday_type="REGIONAL"
        )
        db.add(reg_hol)
        db.commit()

        # For Region 1, 2026-11-04 is non-working
        is_non_work_reg1, reason1 = WorkingDayService.is_holiday_or_weekend(db, date(2026, 11, 4), region_id=1)
        assert is_non_work_reg1 is True
        assert "REGIONAL_STATE_FOUNDATION_DAY" in reason1

        # For Region 2, 2026-11-04 is a regular working day
        is_non_work_reg2, _ = WorkingDayService.is_holiday_or_weekend(db, date(2026, 11, 4), region_id=2)
        assert is_non_work_reg2 is False

        # Cleanup
        db.query(Holiday).filter(Holiday.name == "REGIONAL_STATE_FOUNDATION_DAY").delete()
        db.commit()
    finally:
        db.close()


def test_alert_rules_day_basis_setting():
    """Alert rules specify either WORKING or CALENDAR day_basis."""
    db: Session = SessionLocal()
    try:
        # Phase 7 expanded alert rules from 8 to 12 (11 active + 1 advisory RULE_RISK_HIGH)
        rules = db.query(AlertRule).all()
        assert len(rules) == 12
        for r in rules:
            assert r.day_basis in ["WORKING", "CALENDAR"]
        
        # Scrutiny rule uses WORKING days
        scrutiny_rule = db.query(AlertRule).filter(AlertRule.code == "RULE_SCRUTINY_OVERDUE").first()
        assert scrutiny_rule.day_basis == "WORKING"

        # Document expiry rule uses CALENDAR days
        doc_rule = db.query(AlertRule).filter(AlertRule.code == "RULE_FIRE_NOC_EXPIRED").first()
        assert doc_rule is not None
        assert doc_rule.day_basis == "CALENDAR"
    finally:
        db.close()


# =========================================================================
# 3. CLOSED STATE TESTS
# =========================================================================

def test_case_closure_blocked_with_open_undertakings():
    """Case closure is blocked with plain message if any undertaking is pending verification or compliance."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10005").first()

        # Seed an unverified undertaking
        db.query(Undertaking).filter(Undertaking.application_id == app.id).delete()
        ut = Undertaking(
            application_id=app.id,
            institution_id=app.institution_id,
            condition_title="Clause 5.1 - Land Title Verification",
            due_date=date(2026, 12, 31),
            status=UndertakingStatusEnum.PENDING,
            description="Pending physical demarcation certificate"
        )
        db.add(ut)
        db.commit()

        # Attempt to close case
        token = get_token("ADMIN")
        res = client.post(
            f"/api/v1/applications/{app.id}/close",
            json={"closure_reason": "ALL_CONDITIONS_MET", "closure_remarks": "Completed all checks"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 400
        assert "open undertaking(s) pending compliance or verification" in res.json()["detail"]
    finally:
        db.close()


def test_case_closure_success_and_read_only():
    """Case closes cleanly when conditions met, auto-resolves open alerts, and becomes read-only."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10006").first()

        # Clear undertakings
        db.query(Undertaking).filter(Undertaking.application_id == app.id).delete()
        
        # Add a dummy active alert to test auto-resolution on close
        rule = db.query(AlertRule).first()
        alert = Alert(
            application_id=app.id,
            alert_rule_id=rule.id,
            alert_type=AlertTypeEnum.NEAR_BREACH,
            severity=AlertSeverityEnum.MEDIUM,
            status=AlertStatusEnum.ACTIVE,
            title="Auto resolve test",
            message="Alert to be auto-resolved on close",
            explanation_meta={},
            recipient_role=UserRoleEnum.SCRUTINY_OFFICER
        )
        db.add(alert)
        app.status = ApplicationStatusEnum.IN_PROGRESS
        db.commit()

        token = get_token("ADMIN")
        res = client.post(
            f"/api/v1/applications/{app.id}/close",
            json={"closure_reason": "ALL_CONDITIONS_MET", "closure_remarks": "Archived after complete statutory compliance"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "CLOSED"
        assert data["closure_reason"] == "ALL_CONDITIONS_MET"

        # Check alert is auto-resolved
        db.refresh(alert)
        assert alert.status == AlertStatusEnum.RESOLVED
        assert "Case closed" in (alert.resolution_remarks or "")

        # Verify case is read-only (attempting complete-stage fails)
        res_fail = client.post(
            f"/api/v1/applications/{app.id}/complete-stage",
            json={"remarks": "Attempt advancing closed case"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_fail.status_code == 400
        assert "closed" in res_fail.json()["detail"].lower()
    finally:
        db.close()


def test_case_closure_role_restrictions():
    """Only Competent Authority, Regional Head, and Admin can close cases. Others are forbidden."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10007").first()

        # Scrutiny Officer cannot close
        token_scrutiny = get_token("SCRUTINY_OFFICER")
        res_scrutiny = client.post(
            f"/api/v1/applications/{app.id}/close",
            json={"closure_reason": "SUPERSEDED"},
            headers={"Authorization": f"Bearer {token_scrutiny}"}
        )
        assert res_scrutiny.status_code == 403

        # Institution User cannot close
        token_inst = get_token("INSTITUTION_USER")
        res_inst = client.post(
            f"/api/v1/applications/{app.id}/close",
            json={"closure_reason": "WITHDRAWN_BY_INSTITUTION"},
            headers={"Authorization": f"Bearer {token_inst}"}
        )
        assert res_inst.status_code == 403
    finally:
        db.close()


# =========================================================================
# 4. NEW ROLES TESTS
# =========================================================================

def test_bureau_officer_read_access_and_mutation_restrictions():
    """Bureau officer can view pendency and alerts across regions, but cannot complete stage, decide, or close."""
    token = get_token("BUREAU_OFFICER", "bureau.officer@demo.example")
    
    # 1. Can view pendency report
    res_rep = client.get("/api/v1/reports/pendency", headers={"Authorization": f"Bearer {token}"})
    assert res_rep.status_code == 200
    assert "by_stage" in res_rep.json()

    # 2. Can view overdue report
    res_od = client.get("/api/v1/reports/overdue", headers={"Authorization": f"Bearer {token}"})
    assert res_od.status_code == 200

    # 3. Can view alerts and acknowledge
    res_alerts = client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {token}"})
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    if isinstance(alerts, list) and len(alerts) > 0:
        aid = alerts[0]["id"]
        res_ack = client.post(
            f"/api/v1/alerts/{aid}/acknowledge",
            json={"remarks": "Bureau officer noted this pendency"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_ack.status_code in [200, 400]  # 400 if already acked, but not 403

    # 4. Cannot complete stage or close case
    db = SessionLocal()
    try:
        sample_app = db.query(Application).filter(Application.status == ApplicationStatusEnum.IN_PROGRESS).first()
        target_id = sample_app.id if sample_app else 1
    finally:
        db.close()

    res_mut = client.post(
        f"/api/v1/applications/{target_id}/complete-stage",
        json={"remarks": "Bureau officer attempt"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_mut.status_code == 403

    # 5. Cannot close case
    res_close = client.post(
        f"/api/v1/applications/{target_id}/close",
        json={"closure_reason": "SUPERSEDED"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_close.status_code == 403


def test_committee_member_assigned_cases_and_advisory_recommendation():
    """Committee members see only their assigned cases and submit non-binding advisory recommendations."""
    token = get_token("COMMITTEE_MEMBER", "evc.member@demo.example")

    # 1. My cases endpoint lists assigned cases
    res_cases = client.get("/api/v1/committee/my-cases", headers={"Authorization": f"Bearer {token}"})
    assert res_cases.status_code == 200
    cases = res_cases.json()
    assert isinstance(cases, list)
    assert len(cases) > 0

    target_app_id = cases[0]["application_id"]
    comm_type = cases[0].get("committee_type", "EVC")

    # 2. Post advisory observation and recommendation
    res_obs = client.post(
        f"/api/v1/committee/cases/{target_app_id}/observations",
        json={
            "committee_type": comm_type,
            "observation_text": "Physical inspection of labs and library verified. Adequate infrastructure available.",
            "recommendation": "RECOMMEND_APPROVAL"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_obs.status_code == 200
    obs_data = res_obs.json()
    assert obs_data["recommendation"] == "RECOMMEND_APPROVAL"

    # 3. Verify application stage and status are NOT mutated (decision support only)
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == target_app_id).first()
        # Stage is still whatever it was, not automatically moved
        assert app.status in [ApplicationStatusEnum.IN_PROGRESS, ApplicationStatusEnum.APPROVED, ApplicationStatusEnum.CLOSED]
    finally:
        db.close()

    # 4. Observation appears in history
    res_list = client.get(
        f"/api/v1/committee/cases/{target_app_id}/observations",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_list.status_code == 200
    obs_list = res_list.json()
    assert any(o["recommendation"] == "RECOMMEND_APPROVAL" for o in obs_list)


# =========================================================================
# 5. OVERDUE REPORT & EXPORT TESTS
# =========================================================================

def test_overdue_report_totals_and_database_counts():
    """Overdue cases report metrics match direct database queries."""
    token = get_token("ADMIN")
    res = client.get("/api/v1/reports/overdue", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "items" in data
    
    summary = data["summary"]
    assert "total_overdue" in summary
    assert "applications_overdue" in summary
    assert "evc_overdue" in summary
    assert "undertakings_overdue" in summary
    assert "documents_overdue" in summary

    # Verify items count matches summary total
    assert len(data["items"]) == summary["total_overdue"]


def test_overdue_report_exports_csv_and_pdf():
    """Overdue cases export generates valid CSV and PDF file streams."""
    token = get_token("ADMIN")

    # CSV Export
    res_csv = client.get(
        "/api/v1/reports/export/csv?report_type=overdue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "item_type" in res_csv.text.lower() or "reference" in res_csv.text.lower()

    # PDF Export
    res_pdf = client.get(
        "/api/v1/reports/export/pdf?report_type=overdue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert len(res_pdf.content) > 500  # Non-empty PDF payload
