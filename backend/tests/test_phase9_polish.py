"""
Phase 9 Tests: Polish, Reliability, Config Centralization, Demo Check Idempotence, and Audit.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import User, Institution, AuditLog
from app.services.risk_score_service import RiskScoreService
from scripts.demo_check import run_demo_check
from scripts.check_consistency import check_consistency


def test_docs_endpoints_disabled_outside_demo_mode(monkeypatch):
    """
    When DEMO_MODE=False, FastAPI documentation routes (/docs, /redoc, /openapi.json)
    must be disabled (or return 404).
    """
    from app.main import create_app
    
    # Simulate production mode (DEMO_MODE=False)
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    prod_app = create_app()
    prod_client = TestClient(prod_app)

    r_docs = prod_client.get("/docs")
    assert r_docs.status_code == 404, f"Expected 404 for /docs in non-demo mode, got {r_docs.status_code}"

    r_redoc = prod_client.get("/redoc")
    assert r_redoc.status_code == 404, f"Expected 404 for /redoc in non-demo mode, got {r_redoc.status_code}"

    r_openapi = prod_client.get("/openapi.json")
    assert r_openapi.status_code == 404, f"Expected 404 for /openapi.json in non-demo mode, got {r_openapi.status_code}"


def test_admin_unlock_account_endpoint():
    """
    Admin can unlock a locked user account. Unlocking must reset failed attempts,
    unfreeze the account, and record an immutable audit entry.
    """
    client = TestClient(app)
    db: Session = SessionLocal()
    try:
        target_user = db.query(User).filter(User.email == "scrutiny1@demo.example").first()
        assert target_user is not None

        # 1. Trigger account lockout with 5 failed login attempts
        for _ in range(5):
            client.post("/api/v1/auth/login", json={
                "email": target_user.email,
                "password": "WrongPassword123"
            })

        # 2. 6th attempt should be blocked with 429
        blocked_resp = client.post("/api/v1/auth/login", json={
            "email": target_user.email,
            "password": "Password@123"
        })
        assert blocked_resp.status_code == 429, f"Expected 429, got {blocked_resp.status_code}"

        # 3. Login as Admin
        admin_login = client.post("/api/v1/auth/login", json={
            "email": "admin@demo.example",
            "password": "Password@123"
        })
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 4. Call unlock endpoint
        unlock_resp = client.post(f"/api/v1/auth/unlock/{target_user.id}", headers=headers)
        assert unlock_resp.status_code == 200, unlock_resp.text
        data = unlock_resp.json()
        assert data["status"] == "UNLOCKED"
        assert data["user_id"] == target_user.id

        # 5. User can now log in successfully
        login_after_unlock = client.post("/api/v1/auth/login", json={
            "email": target_user.email,
            "password": "Password@123"
        })
        assert login_after_unlock.status_code == 200, "User should be able to log in after unlock"

        # 6. Verify audit trail
        audit_entry = db.query(AuditLog).filter(
            AuditLog.table_name == "users",
            AuditLog.record_id == target_user.id,
            AuditLog.action == "ACCOUNT_UNLOCKED"
        ).order_by(AuditLog.id.desc()).first()
        assert audit_entry is not None
        assert audit_entry.actor_id == 1  # Admin
    finally:
        db.close()


def test_centralized_risk_band_config():
    """
    Confirms risk band thresholds originate from one single config source
    in app.core.config (settings.RISK_BAND_THRESHOLDS).
    """
    thresholds = settings.RISK_BAND_THRESHOLDS
    assert "low_max" in thresholds
    assert "medium_max" in thresholds
    assert thresholds["low_max"] == 39
    assert thresholds["medium_max"] == 69

    # Verify score_to_band mapping follows config
    assert RiskScoreService.score_to_band(0.0, thresholds) == "LOW"
    assert RiskScoreService.score_to_band(39.0, thresholds) == "LOW"
    assert RiskScoreService.score_to_band(39.1, thresholds) == "MEDIUM"
    assert RiskScoreService.score_to_band(69.0, thresholds) == "MEDIUM"
    assert RiskScoreService.score_to_band(70.0, thresholds) == "HIGH"
    assert RiskScoreService.score_to_band(100.0, thresholds) == "HIGH"


def test_no_real_person_names_or_gov_emails_in_seed():
    """
    Ensures zero occurrences of real public officials' names (e.g. Sitharam)
    and zero occurrences of @aicte.gov.in email addresses in active user records.
    """
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for u in users:
            assert "sitharam" not in u.full_name.lower(), f"Real name found in user {u.id}: {u.full_name}"
            assert not u.email.endswith("@aicte.gov.in"), f"Real domain found in user {u.id}: {u.email}"
            assert u.email.endswith("@demo.example") or u.email.endswith(".example"), f"Non-demo email domain in user {u.id}: {u.email}"

        institutions = db.query(Institution).all()
        for inst in institutions:
            assert "sitharam" not in inst.name.lower(), f"Real name found in institution {inst.id}: {inst.name}"
    finally:
        db.close()


def test_consistency_check_passes_cleanly():
    """Consistency check passes with zero mismatches on seeded database."""
    # check_consistency() raises SystemExit if any mismatch occurs
    try:
        check_consistency()
    except SystemExit as exc:
        pytest.fail(f"Consistency check failed with exit code: {exc.code}")


def test_demo_check_idempotence():
    """
    demo_check runs through the complete 8-step story and restores the database.
    Running it twice back-to-back must succeed both times.
    """
    run_demo_check()
    # Second run immediately following the first
    run_demo_check()
