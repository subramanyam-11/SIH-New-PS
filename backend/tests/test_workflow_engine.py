import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import SessionLocal
from app.models import (
    Application, Institution, ApplicationCategory, StagePath, Stage,
    User, UserRoleEnum, ApplicationStatusEnum, StageHistory
)
from app.services.workflow_engine import WorkflowEngine
from app.services.clock import get_system_time, advance_clock, reset_clock, calculate_sla_status

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_apps():
    db = SessionLocal()
    db.query(Application).filter(Application.application_number.like("AICTE/TEST/%")).delete(synchronize_session=False)
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(Application).filter(Application.application_number.like("AICTE/TEST/%")).delete(synchronize_session=False)
    db.commit()
    db.close()


def get_token_for(email: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_seed_integrity_and_distribution():
    """Verify 60 seeded applications with valid sequences and SLA status."""
    db: Session = SessionLocal()
    try:
        # Check that all 60 core demo seed apps exist
        seed_numbers = [f"AICTE/2026/APP-{10000 + i}" for i in range(1, 61)]
        seed_apps = db.query(Application).filter(Application.application_number.in_(seed_numbers)).all()
        assert len(seed_apps) == 60, f"Expected 60 seed applications, found {len(seed_apps)}"

        # Every seed application has non-empty stage history
        for a in seed_apps:
            assert len(a.stage_history) > 0, f"App {a.application_number} has no stage history"
            # History is chronologically ordered
            for i in range(len(a.stage_history) - 1):
                assert a.stage_history[i].entered_at <= a.stage_history[i + 1].entered_at

        # Check special 2-revert app
        app27 = db.query(Application).filter(Application.application_number == "AICTE/2026/APP-10027").first()
        assert app27 is not None
        assert app27.revert_count == 2
        assert app27.current_stage.code == "RE_SCRUTINY"

        # Check approved seed applications have valid mock letters with watermark
        approved = [a for a in seed_apps if a.status == ApplicationStatusEnum.APPROVED]
        assert len(approved) == 4
        for ap in approved:
            assert ap.approval_letter_ref is not None
            assert ap.approval_letter_data is not None
            assert "SAMPLE - SYNTHETIC DEMO DOCUMENT, NOT AN OFFICIAL AICTE ORDER" in ap.approval_letter_data.get("watermark", "")
    finally:
        db.close()


def test_state_machine_all_5_paths():
    """Verify end-to-end execution of all 5 stage paths from submission to approval."""
    db: Session = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin@aicte.gov.in").first()
        chairman = db.query(User).filter(User.username == "chairman@aicte.gov.in").first()
        evc_coord = db.query(User).filter(User.username == "evc.coord@aicte.gov.in").first()
        scrutiny1 = db.query(User).filter(User.username == "scrutiny1@aicte.gov.in").first()
        ro_north = db.query(User).filter(User.username == "ro.north@aicte.gov.in").first()
        inst = db.query(Institution).filter(Institution.id == 1).first()
        cat = db.query(ApplicationCategory).first()

        paths = db.query(StagePath).all()
        for p in paths:
            app_num = f"AICTE/TEST/{p.code}"
            existing = db.query(Application).filter(Application.application_number == app_num).first()
            if existing:
                db.delete(existing)
                db.commit()

            # 1. Submit
            app = WorkflowEngine.submit_application(
                db=db,
                actor=admin,
                institution_id=inst.id,
                category_id=cat.id,
                application_number=app_num,
                stage_path_id=p.id
            )
            assert app.status == ApplicationStatusEnum.IN_PROGRESS
            assert app.current_stage.code == p.stage_sequence[0]

            # 2. Advance through path
            seq = [s for s in p.stage_sequence if s != "RE_SCRUTINY"]
            for step_idx in range(len(seq) - 2):
                curr_code = app.current_stage.code
                curr_stage = db.query(Stage).filter(Stage.code == curr_code).first()
                
                # Pick role
                if curr_stage.responsible_role == UserRoleEnum.SCRUTINY_OFFICER:
                    actor = scrutiny1
                elif curr_stage.responsible_role == UserRoleEnum.EVC_COORDINATOR:
                    actor = evc_coord
                elif curr_stage.responsible_role == UserRoleEnum.REGIONAL_HEAD:
                    actor = ro_north
                elif curr_stage.responsible_role == UserRoleEnum.COMPETENT_AUTHORITY:
                    actor = chairman
                else:
                    actor = admin

                app, next_stage = WorkflowEngine.complete_stage(
                    db=db, application_id=app.id, actor=actor, remarks=f"Completed {curr_stage.name}"
                )

            # 3. Final Decision
            app = WorkflowEngine.record_decision(
                db=db, application_id=app.id, actor=chairman,
                decision="APPROVE", remarks="Approved after rigorous statutory testing."
            )
            assert app.status == ApplicationStatusEnum.APPROVED
            assert app.approval_letter_ref is not None
            assert "SAMPLE - SYNTHETIC DEMO DOCUMENT, NOT AN OFFICIAL AICTE ORDER" in app.approval_letter_data["watermark"]
    finally:
        db.close()


def test_role_and_regional_permissions():
    """Verify that wrong roles and mismatched regional offices are rejected with 403."""
    db: Session = SessionLocal()
    try:
        inst_north = db.query(Institution).filter(Institution.region_id == 1).first()
        cat = db.query(ApplicationCategory).first()
        path1 = db.query(StagePath).filter(StagePath.code == "PATH_1_SCRUTINY_ONLY").first()
        admin = db.query(User).filter(User.username == "admin@aicte.gov.in").first()

        app = WorkflowEngine.submit_application(
            db=db, actor=admin, institution_id=inst_north.id,
            category_id=cat.id, application_number="AICTE/TEST/PERM-001",
            stage_path_id=path1.id
        )

        # Scrutiny officer from West (region 2) cannot act on North (region 1)
        scrutiny_west = db.query(User).filter(User.username == "scrutiny2@aicte.gov.in").first()
        with pytest.raises(Exception) as exc:
            WorkflowEngine.complete_stage(db=db, application_id=app.id, actor=scrutiny_west, remarks="Invalid region attempt")
        assert "403" in str(exc.value)

        # Scrutiny officer cannot record final decision
        scrutiny_north = db.query(User).filter(User.username == "scrutiny1@aicte.gov.in").first()
        with pytest.raises(Exception) as exc:
            WorkflowEngine.record_decision(db=db, application_id=app.id, actor=scrutiny_north, decision="APPROVE", remarks="Invalid authority attempt")
        assert "403" in str(exc.value)
    finally:
        db.close()


def test_revert_validation_and_cap():
    """Verify mandatory deficiency tags, free-text remark, DEF_OTHER check, and revert cap."""
    db: Session = SessionLocal()
    try:
        inst = db.query(Institution).filter(Institution.region_id == 1).first()
        cat = db.query(ApplicationCategory).first()
        path1 = db.query(StagePath).filter(StagePath.code == "PATH_1_SCRUTINY_ONLY").first()
        admin = db.query(User).filter(User.username == "admin@aicte.gov.in").first()
        scrutiny = db.query(User).filter(User.username == "scrutiny1@aicte.gov.in").first()
        principal = db.query(User).filter(User.username == "principal@apexkanpur.edu").first()

        app = WorkflowEngine.submit_application(
            db=db, actor=admin, institution_id=inst.id,
            category_id=cat.id, application_number="AICTE/TEST/REVERT-001",
            stage_path_id=path1.id
        )
        # Advance to SCRUTINY
        app, _ = WorkflowEngine.complete_stage(db=db, application_id=app.id, actor=scrutiny, remarks="Advance to Scrutiny")

        # 1. Revert with empty tags fails
        with pytest.raises(Exception) as exc:
            WorkflowEngine.return_application(db=db, application_id=app.id, actor=scrutiny, deficiency_tags=[], reason="No tags provided")
        assert "422" in str(exc.value)

        # 2. Revert with empty remark fails
        with pytest.raises(Exception) as exc:
            WorkflowEngine.return_application(db=db, application_id=app.id, actor=scrutiny, deficiency_tags=["DEF_FIRE_NOC"], reason="")
        assert "422" in str(exc.value)

        # 3. DEF_OTHER with too short remark fails
        with pytest.raises(Exception) as exc:
            WorkflowEngine.return_application(db=db, application_id=app.id, actor=scrutiny, deficiency_tags=["DEF_OTHER"], reason="Short")
        assert "422" in str(exc.value)

        # 4. Valid Revert 1 succeeds
        app = WorkflowEngine.return_application(
            db=db, application_id=app.id, actor=scrutiny,
            deficiency_tags=["DEF_FIRE_NOC"], reason="Fire safety clearance certificate has expired."
        )
        assert app.current_stage.code == "RE_SCRUTINY"
        assert app.revert_count == 1

        # Clarify by institution
        app, _ = WorkflowEngine.complete_stage(db=db, application_id=app.id, actor=principal, remarks="Uploaded valid fire clearance.")
        assert app.current_stage.code == "SCRUTINY"

        # Valid Revert 2 succeeds
        app = WorkflowEngine.return_application(
            db=db, application_id=app.id, actor=scrutiny,
            deficiency_tags=["DEF_FACULTY_CADRE"], reason="Faculty cadre ratio is deficient in Computer Science department."
        )
        assert app.current_stage.code == "RE_SCRUTINY"
        assert app.revert_count == 2

        # Clarify again
        app, _ = WorkflowEngine.complete_stage(db=db, application_id=app.id, actor=principal, remarks="Faculty appointment orders uploaded.")
        assert app.current_stage.code == "SCRUTINY"

        # Attempt Revert 3: exceeds cap of 2 -> must flag escalation_required and return 400
        with pytest.raises(Exception) as exc:
            WorkflowEngine.return_application(
                db=db, application_id=app.id, actor=scrutiny,
                deficiency_tags=["DEF_INFRASTRUCTURE"], reason="Instructional lab area still deficient."
            )
        assert "400" in str(exc.value)
        db.refresh(app)
        assert app.escalation_required is True
        assert "limit exceeded" in app.escalation_reason.lower()
    finally:
        db.close()


def test_closed_application_guard():
    """Verify that applications marked APPROVED or REJECTED cannot be transitioned further."""
    db: Session = SessionLocal()
    try:
        app = db.query(Application).filter(Application.status == ApplicationStatusEnum.APPROVED).first()
        chairman = db.query(User).filter(User.username == "chairman@aicte.gov.in").first()
        with pytest.raises(Exception) as exc:
            WorkflowEngine.complete_stage(db=db, application_id=app.id, actor=chairman, remarks="Illegal transition on closed case")
        assert "400" in str(exc.value)
    finally:
        db.close()


def test_sla_calculation_and_demo_clock_advance():
    """Verify SLA status buckets and demo clock advance endpoint."""
    now = get_system_time()
    
    # 1. On Time
    sla_on_time = calculate_sla_status(now - timedelta(days=1), now + timedelta(days=6), 7)
    assert sla_on_time["ageing_bucket"] == "ON_TIME"

    # 2. Near Due (>= 80% SLA elapsed or <= 2 days remaining)
    sla_near_due = calculate_sla_status(now - timedelta(days=6), now + timedelta(days=1), 7)
    assert sla_near_due["ageing_bucket"] == "NEAR_DUE"

    # 3. Overdue
    sla_overdue = calculate_sla_status(now - timedelta(days=9), now - timedelta(days=2), 7)
    assert sla_overdue["ageing_bucket"] == "OVERDUE"

    # 4. Advance clock via demo API
    admin_token = get_token_for("admin@aicte.gov.in")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    res = client.post("/api/v1/demo/advance-clock", json={"hours": 48.0}, headers=headers)
    assert res.status_code == 200
    assert res.json()["advanced_hours"] == 48.0

    # Reset clock
    res_reset = client.post("/api/v1/demo/reset-clock", headers=headers)
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "success"


def test_applications_api_endpoints():
    """Verify all REST API endpoints for applications list, detail, timeline, and tags."""
    admin_token = get_token_for("admin@aicte.gov.in")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Deficiency Tags API
    res_tags = client.get("/api/v1/config/deficiency-tags", headers=headers)
    assert res_tags.status_code == 200
    tags = res_tags.json()
    assert len(tags) >= 9
    assert any(t["code"] == "DEF_OTHER" for t in tags)

    # 2. Applications list with filters
    res_list = client.get("/api/v1/applications?limit=10&page=1", headers=headers)
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] >= 60
    assert len(data["applications"]) == 10

    # Filter by region
    res_reg = client.get("/api/v1/applications?region_id=1", headers=headers)
    assert res_reg.status_code == 200

    # Filter by SLA ageing bucket
    res_overdue = client.get("/api/v1/applications?ageing_bucket=OVERDUE", headers=headers)
    assert res_overdue.status_code == 200
    assert res_overdue.json()["total"] > 0

    # 3. Application Detail
    app_id = data["applications"][0]["id"]
    res_detail = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert "stage_path" in detail
    assert "ageing_bucket" in detail
    assert "days_in_stage" in detail

    # 4. Timeline
    res_timeline = client.get(f"/api/v1/applications/{app_id}/timeline", headers=headers)
    assert res_timeline.status_code == 200
    assert len(res_timeline.json()) > 0

    # 5. Communications
    res_comms = client.get(f"/api/v1/applications/{app_id}/communications", headers=headers)
    assert res_comms.status_code == 200
    assert len(res_comms.json()) > 0
    comm_id = res_comms.json()[0]["id"]

    # Mark communication sent
    res_sent = client.post(f"/api/v1/applications/{app_id}/communications/{comm_id}/mark-sent", headers=headers)
    assert res_sent.status_code == 200
    assert res_sent.json()["status"] == "SENT"
