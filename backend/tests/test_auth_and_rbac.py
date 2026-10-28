import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import SessionLocal
from app.models import AuditLog, User, Institution, UserRoleEnum

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "healthy"
    assert data["demo_mode"] is True


def test_login_success():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@aicte.gov.in",
        "password": "Password@123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"
    assert data["token_type"] == "bearer"


def test_login_failure():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@aicte.gov.in",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401
    assert "detail" in response.json()


def test_demo_login_regional_head():
    response = client.post("/api/v1/auth/demo-login", json={
        "role": "REGIONAL_HEAD",
        "email": "ro.north@aicte.gov.in"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "REGIONAL_HEAD"
    assert "access_token" in data


def test_demo_login_all_roles():
    roles = [
        "ADMIN", "REGIONAL_HEAD", "SCRUTINY_OFFICER",
        "EVC_COORDINATOR", "COMPETENT_AUTHORITY", "INSTITUTION_USER"
    ]
    for r in roles:
        response = client.post("/api/v1/auth/demo-login", json={"role": r})
        assert response.status_code == 200, f"Demo login failed for role {r}"
        assert response.json()["role"] == r


def test_token_protection():
    # Attempting to access protected scope endpoint without token
    response = client.get("/api/v1/users/me/scope")
    assert response.status_code == 401


def test_rbac_institution_scoping():
    # Login as Institution user (Apex Kanpur)
    login_resp = client.post("/api/v1/auth/demo-login", json={"role": "INSTITUTION_USER", "email": "principal@apexkanpur.edu"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch institutions
    inst_resp = client.get("/api/v1/institutions", headers=headers)
    assert inst_resp.status_code == 200
    institutions = inst_resp.json()
    
    # Institution user MUST only see their own institution
    assert len(institutions) == 1
    assert institutions[0]["name"] == "Apex Institute of Technology, Kanpur"


def test_rbac_regional_head_scoping():
    # Login as Regional Head North
    login_resp = client.post("/api/v1/auth/demo-login", json={"role": "REGIONAL_HEAD", "email": "ro.north@aicte.gov.in"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch institutions
    inst_resp = client.get("/api/v1/institutions", headers=headers)
    assert inst_resp.status_code == 200
    institutions = inst_resp.json()
    
    # Northern region has exactly 3 institutions in seed
    assert len(institutions) == 3
    for inst in institutions:
        assert inst["state"] in ["Uttar Pradesh", "Uttarakhand"]


def test_rbac_admin_scope():
    # Login as Admin
    login_resp = client.post("/api/v1/auth/demo-login", json={"role": "ADMIN"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch institutions
    inst_resp = client.get("/api/v1/institutions", headers=headers)
    assert inst_resp.status_code == 200
    institutions = inst_resp.json()
    
    # Admin sees all 15 institutions across all regions
    assert len(institutions) == 15


def test_audit_log_written_on_login():
    db: Session = SessionLocal()
    initial_count = db.query(AuditLog).filter(AuditLog.action.in_(["LOGIN_PASSWORD", "DEMO_LOGIN"])).count()
    
    # Perform a login
    client.post("/api/v1/auth/login", json={
        "email": "admin@aicte.gov.in",
        "password": "Password@123"
    })
    
    new_count = db.query(AuditLog).filter(AuditLog.action.in_(["LOGIN_PASSWORD", "DEMO_LOGIN"])).count()
    assert new_count > initial_count
    
    latest_entry = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert latest_entry.table_name == "users"
    db.close()


def test_config_endpoints():
    login_resp = client.post("/api/v1/auth/demo-login", json={"role": "ADMIN"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    paths_resp = client.get("/api/v1/config/stage-paths", headers=headers)
    assert paths_resp.status_code == 200
    assert len(paths_resp.json()) == 5

    stages_resp = client.get("/api/v1/config/stages", headers=headers)
    assert stages_resp.status_code == 200
    assert len(stages_resp.json()) == 9

    rules_resp = client.get("/api/v1/config/rules", headers=headers)
    assert rules_resp.status_code == 200
    assert "alert_rules" in rules_resp.json()
    assert len(rules_resp.json()["alert_rules"]) == 8
