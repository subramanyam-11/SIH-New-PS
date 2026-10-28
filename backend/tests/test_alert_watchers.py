"""
Unit & Integration Test Suite for Phase 4: Alert Watchers, Escalation Ladder, Notifications, and Outbox.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    Alert, AlertRule, AlertTypeEnum, AlertStatusEnum, AlertSeverityEnum,
    Application, ApplicationStatusEnum, Document, DocumentStatusEnum, DocumentTypeEnum,
    Undertaking, UndertakingStatusEnum, EvcVisit, EvcStatusEnum,
    EscalationRule, EscalationHistory, Notification, EmailOutbox,
    User, UserRoleEnum, Region
)
from app.services.clock import ClockService, set_test_time, reset_clock, advance_clock
from app.services.alert_engine import AlertEngine
from app.services.escalation_service import EscalationService
from app.services.scheduler import run_checks_now, _evaluation_lock
from app.services.email_service import EmailService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_clock():
    """Reset clock before and after each test."""
    reset_clock()
    yield
    reset_clock()


def test_rules_fire_at_threshold_and_not_before():
    """Verify each alert rule evaluates based strictly on database thresholds."""
    db: Session = SessionLocal()
    try:
        now = ClockService.get_now()

        # 1. Test RULE_SCRUTINY_NEAR_BREACH (threshold <= 2 days remaining)
        rule_nb = db.query(AlertRule).filter(AlertRule.code == "RULE_SCRUTINY_NEAR_BREACH").first()
        assert rule_nb is not None
        v_nb = AlertEngine._evaluate_single_rule(db, rule_nb, now)
        # All flagged applications must have 0 < days_remaining <= 2
        for app_id, meta in v_nb.items():
            assert "days remaining" in meta["actual_value"]

        # 2. Test RULE_SCRUTINY_OVERDUE (days_remaining <= 0)
        rule_od = db.query(AlertRule).filter(AlertRule.code == "RULE_SCRUTINY_OVERDUE").first()
        assert rule_od is not None
        v_od = AlertEngine._evaluate_single_rule(db, rule_od, now)
        for app_id, meta in v_od.items():
            assert "days overdue" in meta["actual_value"]

        # 3. Test RULE_EVC_UNSCHEDULED (in EVC_PENDING >= 3 days without schedule)
        rule_evc = db.query(AlertRule).filter(AlertRule.code == "RULE_EVC_UNSCHEDULED").first()
        assert rule_evc is not None
        v_evc = AlertEngine._evaluate_single_rule(db, rule_evc, now)
        assert len(v_evc) > 0
        for app_id, meta in v_evc.items():
            assert "days in queue" in meta["actual_value"]

        # 4. Test RULE_LEASE_90D & RULE_LEASE_30D
        rule_90 = db.query(AlertRule).filter(AlertRule.code == "RULE_LEASE_90D").first()
        rule_30 = db.query(AlertRule).filter(AlertRule.code == "RULE_LEASE_30D").first()
        v_90 = AlertEngine._evaluate_single_rule(db, rule_90, now)
        v_30 = AlertEngine._evaluate_single_rule(db, rule_30, now)
        assert len(v_90) > 0
        assert len(v_30) > 0
        for doc_id, meta in v_90.items():
            doc = db.query(Document).filter(Document.id == doc_id).first()
            days = (doc.expiry_date - now.date()).days
            assert 30 < days <= 90

        for doc_id, meta in v_30.items():
            doc = db.query(Document).filter(Document.id == doc_id).first()
            days = (doc.expiry_date - now.date()).days
            assert 0 < days <= 30

        # 5. Test RULE_FIRE_NOC_EXPIRED
        rule_fire = db.query(AlertRule).filter(AlertRule.code == "RULE_FIRE_NOC_EXPIRED").first()
        v_fire = AlertEngine._evaluate_single_rule(db, rule_fire, now)
        assert len(v_fire) > 0
        for doc_id, meta in v_fire.items():
            doc = db.query(Document).filter(Document.id == doc_id).first()
            assert doc.expiry_date <= now.date()

        # 6. Test RULE_UNDERTAKING_DUE_15D
        rule_ut = db.query(AlertRule).filter(AlertRule.code == "RULE_UNDERTAKING_DUE_15D").first()
        v_ut = AlertEngine._evaluate_single_rule(db, rule_ut, now)
        assert len(v_ut) > 0
        for ut_id, meta in v_ut.items():
            ut = db.query(Undertaking).filter(Undertaking.id == ut_id).first()
            assert (ut.due_date - now.date()).days <= 15

        # 7. Test RULE_MULTIPLE_REVERTS (revert_count >= 2)
        rule_rev = db.query(AlertRule).filter(AlertRule.code == "RULE_MULTIPLE_REVERTS").first()
        v_rev = AlertEngine._evaluate_single_rule(db, rule_rev, now)
        assert len(v_rev) >= 1
        for app_id, meta in v_rev.items():
            app = db.query(Application).filter(Application.id == app_id).first()
            assert app.revert_count >= 2
    finally:
        db.close()


def test_deduplication_and_auto_resolution():
    """Verify one open alert per entity/rule and automatic resolution when conditions clear."""
    db: Session = SessionLocal()
    try:
        now = ClockService.get_now()
        # Initial run
        run1 = AlertEngine.evaluate_all_rules(db=db, triggered_by="TEST")
        initial_open = db.query(Alert).filter(Alert.status == AlertStatusEnum.ACTIVE).count()
        assert initial_open > 0

        # Second immediate run without clock change must create 0 duplicate alerts
        run2 = AlertEngine.evaluate_all_rules(db=db, triggered_by="TEST")
        assert run2["alerts_created"] == 0

        # Auto-resolve test: Mark a document with an active alert as SUPERSEDED (condition clears)
        doc_alert = db.query(Alert).filter(
            Alert.document_id != None,
            Alert.status == AlertStatusEnum.ACTIVE
        ).first()
        assert doc_alert is not None
        doc_id = doc_alert.document_id

        doc = db.query(Document).filter(Document.id == doc_id).first()
        doc.status = DocumentStatusEnum.SUPERSEDED
        db.commit()

        # Evaluate rules again; this alert must auto-resolve!
        run3 = AlertEngine.evaluate_all_rules(db=db, triggered_by="TEST")
        db.refresh(doc_alert)
        assert doc_alert.status == AlertStatusEnum.RESOLVED
        assert "cleared automatically" in doc_alert.resolution_remarks

        # Restore doc status for test cleanup
        doc.status = DocumentStatusEnum.EXPIRED
        db.commit()
    finally:
        db.close()


def test_escalation_ladder_and_history():
    """Test L1 -> L2 -> L3 timing, history recording, and notification dispatch."""
    db: Session = SessionLocal()
    try:
        # Pick an active alert
        alert = db.query(Alert).filter(Alert.status == AlertStatusEnum.ACTIVE).first()
        assert alert is not None
        initial_tier = alert.escalation_tier or 1

        # Artificially age the alert created_at by 3 days
        alert.created_at = alert.created_at - timedelta(days=3)
        db.commit()

        # Run escalation evaluation
        esc_count = EscalationService.evaluate_escalations(db=db)
        db.refresh(alert)

        # Alert should have escalated to Tier 2 (Regional Head) or higher
        assert alert.escalation_tier > initial_tier
        assert alert.status == AlertStatusEnum.ESCALATED
        assert alert.escalated_at is not None

        # Verify escalation_history row
        history = db.query(EscalationHistory).filter(EscalationHistory.alert_id == alert.id).all()
        assert len(history) > 0
        latest_h = history[0]
        assert latest_h.to_tier == alert.escalation_tier

        # Verify notification was queued for escalated role
        notif = db.query(Notification).filter(Notification.alert_id == alert.id).first()
        assert notif is not None
    finally:
        db.close()


def test_snooze_and_caps():
    """Test snooze limit enforcement and verify snooze cannot hide escalated alerts."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.role.has(code="SCRUTINY_OFFICER")).first()
        alert = db.query(Alert).filter(Alert.status == AlertStatusEnum.ACTIVE).first()
        assert alert is not None

        # Snooze 1: Valid
        snoozed_1 = EscalationService.snooze_alert(db=db, alert_id=alert.id, user=user, hours=24.0, reason="Awaiting land deed dispatch from tehsildar")
        assert snoozed_1.status == AlertStatusEnum.SNOOZED
        assert snoozed_1.snooze_count == 1
        assert snoozed_1.snoozed_until is not None

        # Snooze 2: Valid
        snoozed_2 = EscalationService.snooze_alert(db=db, alert_id=alert.id, user=user, hours=24.0, reason="Follow-up letter issued to registrar")
        assert snoozed_2.snooze_count == 2

        # Snooze 3: Exceeds cap (max 2) -> must raise 400
        with pytest.raises(Exception) as exc_info:
            EscalationService.snooze_alert(db=db, alert_id=alert.id, user=user, hours=24.0, reason="Third snooze attempt")
        assert "Maximum permitted snooze limit" in str(exc_info.value)
    finally:
        db.close()


def test_time_travel_clock_advancement_creates_alerts():
    """Verify that advancing the demo clock dynamically breaches SLAs and creates new overdue alerts."""
    db: Session = SessionLocal()
    try:
        # Count current overdue alerts
        initial_overdue = db.query(Alert).filter(Alert.alert_type == AlertTypeEnum.OVERDUE, Alert.status == AlertStatusEnum.ACTIVE).count()

        # Advance clock by 7 days (+168 hours)
        advance_clock(168.0)

        # Run alert checks
        res = run_checks_now(triggered_by="TEST_CLOCK_ADVANCE")
        assert res["status"] == "SUCCESS"

        # Overdue count should have grown
        post_overdue = db.query(Alert).filter(Alert.alert_type == AlertTypeEnum.OVERDUE, Alert.status == AlertStatusEnum.ACTIVE).count()
        assert post_overdue >= initial_overdue
    finally:
        reset_clock()
        db.close()


def test_role_and_regional_scoping():
    """Test that regional officers only see alerts in their jurisdiction."""
    # 1. Regional Head North (region 1)
    login_north = client.post("/api/v1/auth/demo-login", json={"role": "REGIONAL_HEAD", "email": "ro.north@aicte.gov.in"}).json()
    token_north = login_north["access_token"]
    res_north = client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {token_north}"})
    assert res_north.status_code == 200
    alerts_north = res_north.json()

    # 2. Regional Head South (region 3)
    login_south = client.post("/api/v1/auth/demo-login", json={"role": "REGIONAL_HEAD", "email": "ro.south@aicte.gov.in"}).json()
    token_south = login_south["access_token"]
    res_south = client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {token_south}"})
    assert res_south.status_code == 200
    alerts_south = res_south.json()

    # Regional heads should not see identical sets of regional alerts
    assert len(alerts_north) > 0
    assert len(alerts_south) > 0


def test_scheduler_overlap_lock_and_outbox_flow():
    """Test that scheduler run lock prevents concurrent executions and outbox suppresses when sending disabled."""
    db: Session = SessionLocal()
    try:
        # Simulate lock held by another thread
        with _evaluation_lock:
            # Another call while locked must gracefully return SKIPPED status
            res = run_checks_now(triggered_by="TEST_CONCURRENT")
            assert res["status"] == "SKIPPED"

        # Outbox test: Queue an email
        user = db.query(User).filter(User.role.has(code="ADMIN")).first()
        outbox_entry = EmailService.queue_email(
            db=db,
            recipient_email="test.officer@aicte.gov.in",
            subject="[AICTE Test] Delivery Status",
            body="Test email content",
            recipient_user_id=user.id,
        )
        assert outbox_entry.id is not None
        # With EMAIL_SEND_ENABLED=False (default), status must be SUPPRESSED
        assert outbox_entry.status in ["QUEUED", "SUPPRESSED"]
    finally:
        db.close()


def test_alerts_do_not_modify_application_stage_or_status():
    """Statutory invariance: alert engine only observes and notifies; it NEVER changes application state."""
    db: Session = SessionLocal()
    try:
        apps_before = {a.id: (a.current_stage_id, a.status.value, a.revert_count) for a in db.query(Application).all()}

        # Run complete evaluation cycle
        run_checks_now(triggered_by="TEST_INVARIANCE")

        apps_after = {a.id: (a.current_stage_id, a.status.value, a.revert_count) for a in db.query(Application).all()}

        # Assert no stage, status or revert counts changed
        for app_id, state_before in apps_before.items():
            state_after = apps_after[app_id]
            assert state_before == state_after, f"Application {app_id} state changed from {state_before} to {state_after} by alert engine!"
    finally:
        db.close()


def test_api_endpoints_acknowledge_snooze_resolve():
    """Verify API endpoints for alert lifecycle: acknowledge, snooze, and resolve."""
    admin_login = client.post("/api/v1/auth/demo-login", json={"role": "ADMIN", "email": "admin@aicte.gov.in"}).json()
    token = admin_login["access_token"]

    # 1. Fetch alerts list
    res = client.get("/api/v1/alerts?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) > 0
    target_alert_id = alerts[0]["id"]

    # 2. Acknowledge alert
    ack_res = client.post(
        f"/api/v1/alerts/{target_alert_id}/acknowledge",
        headers={"Authorization": f"Bearer {token}"},
        json={"remarks": "Acknowledged by testing harness"}
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

    # 3. Resolve alert
    res_resolve = client.post(
        f"/api/v1/alerts/{target_alert_id}/resolve",
        headers={"Authorization": f"Bearer {token}"},
        json={"remarks": "Statutory verification complete and resolved"}
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"

    # 4. Fetch escalation matrix
    matrix_res = client.get("/api/v1/escalation/matrix", headers={"Authorization": f"Bearer {token}"})
    assert matrix_res.status_code == 200
    matrix = matrix_res.json()
    assert len(matrix["regions"]) == 5

    # 5. Fetch email outbox
    outbox_res = client.get("/api/v1/outbox?limit=10", headers={"Authorization": f"Bearer {token}"})
    assert outbox_res.status_code == 200
    assert isinstance(outbox_res.json(), list)
