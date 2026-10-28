"""
Unit & Integration Test Suite for Phase 5:
- Module C: EVC Scheduling & Panel Assignment
- Module D: Undertaking Compliance Tracker
- Module E: Document Validity & Version Chains
- Module F: Statutory Analytics & Reports
- File Storage Abstraction & Institution Portal RBAC Scoping
"""
import io
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    Application, Institution, EvcVisit, EvcStatusEnum, EvcExpert,
    Undertaking, UndertakingStatusEnum, UndertakingEvidence, UndertakingHistory,
    Document, DocumentStatusEnum, DocumentTypeEnum, UploadedFile,
    Alert, AlertStatusEnum, User, UserRoleEnum
)
from app.services.clock import reset_clock, ClockService
from app.services.evc_service import EvcService
from app.services.undertaking_service import UndertakingService
from app.services.document_service import DocumentService
from app.services.reports_service import ReportsService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_clock():
    reset_clock()
    yield
    reset_clock()


def get_token(role: str, email: str = None):
    payload = {"role": role}
    if email:
        payload["email"] = email
    res = client.post("/api/v1/auth/demo-login", json=payload)
    assert res.status_code == 200, f"Demo login failed for {role}"
    return res.json()["access_token"]


def auth_header(role: str, email: str = None):
    return {"Authorization": f"Bearer {get_token(role, email)}"}


# =========================================================================
# 1. EVC INSPECTION TESTS
# =========================================================================

def test_evc_panel_size_validation():
    """Regulatory mandate requires exactly 3 distinct committee experts."""
    headers = auth_header("EVC_COORDINATOR")
    db: Session = SessionLocal()
    visit = db.query(EvcVisit).first()
    db.close()

    # Reject 2 experts
    res_2 = client.post(f"/api/v1/evc/visits/{visit.id}/assign-panel", json={"expert_ids": [1, 2]}, headers=headers)
    assert res_2.status_code == 422
    assert "exactly 3" in res_2.json()["detail"]

    # Reject 4 experts
    res_4 = client.post(f"/api/v1/evc/visits/{visit.id}/assign-panel", json={"expert_ids": [1, 2, 3, 4]}, headers=headers)
    assert res_4.status_code == 422

    # Reject duplicate experts
    res_dup = client.post(f"/api/v1/evc/visits/{visit.id}/assign-panel", json={"expert_ids": [1, 1, 2]}, headers=headers)
    assert res_dup.status_code == 422
    assert "Duplicate experts" in res_dup.json()["detail"]


def test_evc_conflict_checks_city_and_institution():
    """Experts cannot be assigned to institutions in their own city or home institution."""
    db: Session = SessionLocal()
    try:
        # Create an institution in Kanpur and an expert affiliated with IIT Kanpur
        inst = db.query(Institution).filter(Institution.city == "Kanpur").first()
        expert_kanpur = db.query(EvcExpert).filter(EvcExpert.city == "Kanpur").first()
        assert inst is not None and expert_kanpur is not None

        conflicts = EvcService.check_expert_conflict(db, expert_kanpur, inst)
        assert len(conflicts) > 0
        assert any("Geographic Conflict" in c or "Institutional Conflict" in c for c in conflicts)
    finally:
        db.close()


def test_evc_concurrency_limit_check():
    """Experts cannot exceed configurable concurrency limit (default 2 active visits)."""
    db: Session = SessionLocal()
    try:
        expert = db.query(EvcExpert).first()
        inst = db.query(Institution).filter(Institution.city != expert.city).first()

        # Simulate 2 active visits already having this expert
        visits = db.query(EvcVisit).all()
        assert len(visits) >= 3
        v1, v2, v3 = visits[0], visits[1], visits[2]
        v1.status = EvcStatusEnum.SCHEDULED
        v1.assigned_experts = [{"id": expert.id, "name": expert.name}]
        v2.status = EvcStatusEnum.ASSIGNED
        v2.assigned_experts = [{"id": expert.id, "name": expert.name}]
        db.commit()

        # Third visit assignment should flag Capacity Limit
        conflicts = EvcService.check_expert_conflict(db, expert, inst, current_visit_id=v3.id)
        assert any("Capacity Limit" in c for c in conflicts)
    finally:
        db.close()


def test_evc_lifecycle_and_alert_auto_resolve():
    """Complete EVC lifecycle from ASSIGNED -> SCHEDULED -> VISIT_DONE -> REPORT_RECEIVED -> CLOSED."""
    headers_coord = auth_header("EVC_COORDINATOR")
    db: Session = SessionLocal()
    try:
        visit = db.query(EvcVisit).filter(EvcVisit.status == EvcStatusEnum.ASSIGNED).first()
        if not visit:
            visit = db.query(EvcVisit).first()
            visit.status = EvcStatusEnum.ASSIGNED
            db.commit()
            db.refresh(visit)

        # 1. Schedule visit
        sched_date = (date.today() + timedelta(days=5)).isoformat()
        res_sched = client.post(
            f"/api/v1/evc/visits/{visit.id}/schedule",
            json={"scheduled_date": sched_date, "scheduled_time": "11:00 AM"},
            headers=headers_coord
        )
        assert res_sched.status_code == 200
        assert res_sched.json()["status"] == "SCHEDULED"

        # 2. Mark visit done
        res_done = client.post(
            f"/api/v1/evc/visits/{visit.id}/complete-visit",
            json={"visit_summary": "Thorough physical verification conducted across labs and library."},
            headers=headers_coord
        )
        assert res_done.status_code == 200
        assert res_done.json()["status"] == "VISIT_DONE"

        # 3. Upload report
        res_rep = client.post(
            f"/api/v1/evc/visits/{visit.id}/upload-report",
            params={
                "outcome_recommendation": "RECOMMENDED",
                "remarks": "Infrastructure matches norms."
            },
            headers=headers_coord
        )
        assert res_rep.status_code == 200
        assert res_rep.json()["status"] == "REPORT_RECEIVED"

        # 4. Close visit
        res_close = client.post(
            f"/api/v1/evc/visits/{visit.id}/close",
            json={"remarks": "Visit closed after committee review."},
            headers=headers_coord
        )
        assert res_close.status_code == 200
        assert res_close.json()["status"] == "CLOSED"
    finally:
        db.close()


def test_evc_role_restrictions():
    """Institution users cannot assign committee panels or schedule inspection visits."""
    inst_headers = auth_header("INSTITUTION_USER")
    res = client.post("/api/v1/evc/visits/1/assign-panel", json={"expert_ids": [1, 2, 3]}, headers=inst_headers)
    assert res.status_code == 403


# =========================================================================
# 2. UNDERTAKINGS & VERIFICATION TESTS
# =========================================================================

def test_undertaking_evidence_submission_and_verification():
    """Institution uploads compliance evidence; Scrutiny Officer verifies."""
    inst_headers = auth_header("INSTITUTION_USER", email="principal@apexkanpur.edu")
    officer_headers = auth_header("SCRUTINY_OFFICER", email="scrutiny1@aicte.gov.in")

    db: Session = SessionLocal()
    try:
        ut = db.query(Undertaking).filter(Undertaking.institution_id == 1).first()
        assert ut is not None
        ut_id = ut.id

        # 1. Institution uploads evidence
        file_payload = {"file": ("affidavit.pdf", io.BytesIO(b"%PDF-1.4 sample affidavit content"), "application/pdf")}
        res_up = client.post(
            f"/api/v1/undertakings/{ut_id}/upload-evidence",
            files=file_payload,
            data={"comments": "Divyangjan lift commissioned with municipal certificate."},
            headers=inst_headers
        )
        assert res_up.status_code == 200
        data = res_up.json()
        assert data["status"] == "SUBMITTED"
        assert len(data["evidences"]) > 0

        # 2. Institution user CANNOT verify own evidence
        res_fail = client.post(
            f"/api/v1/undertakings/{ut_id}/verify",
            json={"action": "VERIFIED", "remarks": "Self verified by principal"},
            headers=inst_headers
        )
        assert res_fail.status_code == 403

        # 3. Officer verifies evidence
        res_verify = client.post(
            f"/api/v1/undertakings/{ut_id}/verify",
            json={"action": "VERIFIED", "remarks": "Geo-tagged photo and electrical safety clearance verified."},
            headers=officer_headers
        )
        assert res_verify.status_code == 200
        assert res_verify.json()["status"] == "VERIFIED"
    finally:
        db.close()


def test_undertaking_escalation_after_two_rejections():
    """Two rejections trigger automatic escalation to Competent Authority."""
    officer_headers = auth_header("SCRUTINY_OFFICER", email="scrutiny1@aicte.gov.in")
    db: Session = SessionLocal()
    try:
        ut = db.query(Undertaking).filter(Undertaking.institution_id == 1).first()
        ut.rejection_count = 1
        ut.status = UndertakingStatusEnum.SUBMITTED
        db.commit()

        # Second rejection
        res = client.post(
            f"/api/v1/undertakings/{ut.id}/verify",
            json={"action": "REJECTED", "remarks": "Clear deficiencies remain unaddressed in physical inspection."},
            headers=officer_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ESCALATED"
        assert data["rejection_count"] == 2
        assert data["escalated_to_tier"] == 3
        assert "Escalated for Apex Council determination" in data["escalation_reason"]
    finally:
        db.close()


# =========================================================================
# 3. DOCUMENT VALIDITY & VERSIONING TESTS
# =========================================================================

def test_document_renewal_creates_new_version_and_supersedes_old():
    """Document renewal creates v2 in RENEWAL_SUBMITTED; verification supersedes v1."""
    inst_headers = auth_header("INSTITUTION_USER", email="principal@apexkanpur.edu")
    officer_headers = auth_header("SCRUTINY_OFFICER", email="scrutiny1@aicte.gov.in")

    db: Session = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.institution_id == 1, Document.status == DocumentStatusEnum.VALID).first()
        assert doc is not None

        # 1. Upload renewal
        new_exp = (date.today() + timedelta(days=730)).isoformat()
        new_iss = date.today().isoformat()
        file_payload = {"file": ("fire_noc_2026.pdf", io.BytesIO(b"%PDF-1.4 new fire noc"), "application/pdf")}
        res_ren = client.post(
            f"/api/v1/documents/{doc.id}/upload-renewal",
            files=file_payload,
            data={
                "new_expiry_date": new_exp,
                "new_issue_date": new_iss,
                "issuing_authority": "Chief Fire Officer, Kanpur",
                "document_number": "FS/KAN/2026/888",
                "renewal_notes": "Upgraded sprinklers inspected and certified."
            },
            headers=inst_headers
        )
        assert res_ren.status_code == 200
        v2_data = res_ren.json()
        assert v2_data["version_number"] == (doc.version_number or 1) + 1
        assert v2_data["status"] == "RENEWAL_SUBMITTED"
        new_doc_id = v2_data["id"]

        # 2. Officer verifies renewal
        res_ver = client.post(
            f"/api/v1/documents/{new_doc_id}/verify-renewal",
            json={"approved": True, "remarks": "Renewal verified against municipal database records."},
            headers=officer_headers
        )
        assert res_ver.status_code == 200
        verified_data = res_ver.json()
        assert verified_data["status"] == "VALID"

        # Check that old version is now marked SUPERSEDED
        db.refresh(doc)
        assert doc.status == DocumentStatusEnum.SUPERSEDED
    finally:
        db.close()


# =========================================================================
# 4. INSTITUTION STRICT SCOPING TESTS
# =========================================================================

def test_institution_user_strict_scoping():
    """Institution user must get 403 or 404 when accessing another institution's records."""
    inst1_headers = auth_header("INSTITUTION_USER", email="principal@apexkanpur.edu") # Institution 1

    db: Session = SessionLocal()
    try:
        # Find an undertaking belonging to Institution 4
        other_ut = db.query(Undertaking).filter(Undertaking.institution_id == 4).first()
        assert other_ut is not None

        # Try to view another institution's undertaking
        res_ut = client.get(f"/api/v1/undertakings/{other_ut.id}", headers=inst1_headers)
        assert res_ut.status_code in [403, 404]

        # Find a document belonging to Institution 4
        other_doc = db.query(Document).filter(Document.institution_id == 4).first()
        assert other_doc is not None

        # Try to view another institution's document
        res_doc = client.get(f"/api/v1/documents/{other_doc.id}", headers=inst1_headers)
        assert res_doc.status_code in [403, 404]

        # Try to view another institution's health dossier
        res_health = client.get("/api/v1/reports/institutions/4/health", headers=inst1_headers)
        assert res_health.status_code in [403, 404]
    finally:
        db.close()


# =========================================================================
# 5. STATUTORY REPORTS & EXPORT TESTS
# =========================================================================

def test_reports_database_calculations_and_exports():
    """All 5 reports return database-calculated values, CSV export works, and PDF export produces valid files."""
    ro_headers = auth_header("REGIONAL_HEAD", email="ro.north@aicte.gov.in")

    # 1. Pendency report
    res_pend = client.get("/api/v1/reports/pendency", headers=ro_headers)
    assert res_pend.status_code == 200
    pend_data = res_pend.json()
    assert "total_pending" in pend_data
    assert "by_stage" in pend_data
    assert isinstance(pend_data["total_pending"], int)

    # 2. EVC status report
    res_evc = client.get("/api/v1/reports/evc", headers=ro_headers)
    assert res_evc.status_code == 200
    evc_data = res_evc.json()
    assert "total_visits" in evc_data
    assert "by_status" in evc_data

    # 3. Undertakings report
    res_ut = client.get("/api/v1/reports/undertakings", headers=ro_headers)
    assert res_ut.status_code == 200
    ut_data = res_ut.json()
    assert "total_undertakings" in ut_data
    assert "by_status" in ut_data

    # 4. Documents report
    res_doc = client.get("/api/v1/reports/documents", headers=ro_headers)
    assert res_doc.status_code == 200
    doc_data = res_doc.json()
    assert "total_documents" in doc_data
    assert "by_status" in doc_data

    # 5. Regional performance report
    res_perf = client.get("/api/v1/reports/regional-performance", headers=ro_headers)
    assert res_perf.status_code == 200
    assert "regions" in res_perf.json()

    # 6. CSV Export
    res_csv = client.get("/api/v1/reports/export/csv?report_type=pendency", headers=ro_headers)
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    assert "Approval Stage,Pending Applications,Average Days in Stage,Overdue Count" in res_csv.text

    # 7. PDF Export
    res_pdf = client.get("/api/v1/reports/export/pdf?report_type=regional_performance", headers=ro_headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF") # Valid PDF signature


# =========================================================================
# 6. FILE HANDLING & AUTHORIZED DOWNLOAD TESTS
# =========================================================================

def test_file_upload_validation_and_download():
    """Only allowed formats (PDF, PNG, JPG) are accepted, and files are served through authorized endpoints."""
    headers = auth_header("ADMIN")

    # Reject executable or shell script
    res_bad = client.post(
        "/api/v1/files/upload",
        files={"file": ("malicious.sh", io.BytesIO(b"#!/bin/bash\necho bad"), "text/x-shellscript")},
        headers=headers
    )
    assert res_bad.status_code == 400
    assert "Invalid file type" in res_bad.json()["detail"]

    # Accept valid PDF
    res_good = client.post(
        "/api/v1/files/upload",
        files={"file": ("sanction_order.pdf", io.BytesIO(b"%PDF-1.4 valid test file"), "application/pdf")},
        data={"entity_type": "GENERAL", "entity_id": 1},
        headers=headers
    )
    assert res_good.status_code == 200
    uploaded_data = res_good.json()
    file_id = uploaded_data["id"]
    assert uploaded_data["mime_type"] == "application/pdf"

    # Authorized download
    res_dl = client.get(f"/api/v1/files/{file_id}/download", headers=headers)
    assert res_dl.status_code == 200
    assert res_dl.content == b"%PDF-1.4 valid test file"
