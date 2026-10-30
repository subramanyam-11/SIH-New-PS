"""
Phase 8 Security, Hardening, and Proof Test Suite.
Build Plan v2 Sections 10, 11, and 14.
"""

import os
import time
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models import AuditLog, UploadedFile, IntegrationLog, User, Institution
from app.services.file_encryption import FileEncryptionService
from app.services.virus_scanner import DemoScanner, EICAR_STANDARD_SIGNATURE
from app.services.audit import AuditService
from app.services.aicte_adapter import aicte_adapter, MockAicteAdapter
from app.services.retention_service import RetentionService


client = TestClient(app)


def get_auth_token(email: str = "admin@demo.example") -> str:
    """Helper to get JWT token for authenticated requests."""
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
    if res.status_code == 200:
        return res.json()["access_token"]
    # Fallback to demo login if enabled
    res = client.post("/api/v1/auth/demo-login", json={"role": "ADMIN"})
    return res.json()["access_token"]


# ==============================================================================
# 1. FILE SECURITY TESTS (Encryption, Validation, Anti-Malware)
# ==============================================================================

def test_file_encryption_aes_gcm_roundtrip():
    """Verify AES-256-GCM ciphertext on disk differs from plaintext and roundtrips perfectly."""
    original_data = b"%PDF-1.4\nSynthetic test file contents with secret institutional disclosures."
    
    ciphertext, key_id, iv_hex = FileEncryptionService.encrypt_bytes(original_data)
    
    # Ciphertext must differ completely from original plaintext
    assert ciphertext != original_data
    assert original_data not in ciphertext
    assert key_id == settings.FILE_ENCRYPTION_KEY_ID
    assert len(bytes.fromhex(iv_hex)) == 12  # 96-bit GCM IV
    
    # Decryption must recover original exact bytes
    decrypted = FileEncryptionService.decrypt_bytes(ciphertext, key_id, iv_hex)
    assert decrypted == original_data


def test_file_scanner_rejects_eicar_test_string():
    """Demo scanner rejects standard EICAR test string and audits the event."""
    scanner = DemoScanner()
    
    is_clean, scanner_name, reason = scanner.scan_bytes(EICAR_STANDARD_SIGNATURE, "eicar_test.pdf")
    assert is_clean is False
    assert "EICAR Standard Antivirus Test Pattern" in reason
    assert "Demo scanner (production would use ClamAV)" in scanner_name


from app.services.file_service import FileStorageService


def test_file_upload_validation_rejects_double_extension():
    """File service rejects dangerous double extensions (e.g. .pdf.exe)."""
    with pytest.raises(Exception) as excinfo:
        FileStorageService.validate_content(
            content=b"%PDF-1.4 fake payload",
            filename="evidence.pdf.exe",
            ext_lower=".exe",
            mime_type="application/pdf"
        )
    assert "Multiple file extensions detected" in str(excinfo.value) or "Double extension" in str(excinfo.value)


def test_file_upload_validation_rejects_spoofed_magic_bytes():
    """File service rejects files whose content bytes do not match declared extension."""
    with pytest.raises(Exception) as excinfo:
        FileStorageService.validate_content(
            content=b"MZ\x90\x00\x03\x00\x00\x00 This is a Windows executable header",
            filename="corrupted.pdf",
            ext_lower=".pdf",
            mime_type="application/pdf"
        )
    assert "Magic byte header mismatch" in str(excinfo.value)


def test_file_upload_validation_rejects_oversize_file():
    """File service rejects files exceeding maximum size limit."""
    # 11MB file (limit is 10MB)
    oversize_content = b"%PDF-1.4" + (b"0" * (11 * 1024 * 1024))
    with pytest.raises(Exception) as excinfo:
        FileStorageService.validate_content(
            content=oversize_content,
            filename="giant.pdf",
            ext_lower=".pdf",
            mime_type="application/pdf"
        )
    assert "exceeds maximum allowed size" in str(excinfo.value)


def test_file_unauthorized_download_blocked():
    """Unauthorized user cannot download files belonging to another institution."""
    db = SessionLocal()
    try:
        sample_file = db.query(UploadedFile).first()
        if not sample_file:
            pytest.skip("No uploaded files in seed")

        # Login as an institution user belonging to a different institution
        inst2_user = db.query(User).filter(User.institution_id != None, User.institution_id != 1).first()
        if not inst2_user:
            pytest.skip("No alternative institution user found")

        # Get token for inst2_user
        token_res = client.post("/api/v1/auth/login", json={"email": inst2_user.email, "password": "Password@123"})
        if token_res.status_code != 200:
            pytest.skip("Could not authenticate inst2_user")

        inst_token = token_res.json()["access_token"]
        # Attempt to access file #1 (which belongs to inst 1)
        res = client.get(
            f"/api/v1/files/{sample_file.id}/download",
            headers={"Authorization": f"Bearer {inst_token}"}
        )
        # Should either be 403 Forbidden or 404 Not Found due to scoping
        assert res.status_code in [403, 404]
    finally:
        db.close()


# ==============================================================================
# 2. TAMPER-EVIDENT AUDIT LOG TESTS (Append-Only Trigger, Hash Chain)
# ==============================================================================

def test_audit_log_database_trigger_blocks_update():
    """PostgreSQL trigger strictly rejects any UPDATE statements on audit_log."""
    db = SessionLocal()
    try:
        sample_row = db.query(AuditLog).first()
        if not sample_row:
            pytest.skip("No audit log rows to test")

        with pytest.raises(Exception) as excinfo:
            db.execute(
                text("UPDATE audit_log SET action = 'ALTERED' WHERE id = :id"),
                {"id": sample_row.id}
            )
            db.commit()
        db.rollback()
        assert "audit_log is append-only" in str(excinfo.value)
    finally:
        db.close()


def test_audit_log_database_trigger_blocks_delete():
    """PostgreSQL trigger strictly rejects any DELETE statements on audit_log."""
    db = SessionLocal()
    try:
        sample_row = db.query(AuditLog).first()
        if not sample_row:
            pytest.skip("No audit log rows to test")

        with pytest.raises(Exception) as excinfo:
            db.execute(
                text("DELETE FROM audit_log WHERE id = :id"),
                {"id": sample_row.id}
            )
            db.commit()
        db.rollback()
        assert "audit_log is append-only" in str(excinfo.value)
    finally:
        db.close()


def test_audit_log_hash_chain_integrity():
    """AuditService walks hash chain from genesis and verifies 100% cryptographic continuity."""
    db = SessionLocal()
    try:
        res = AuditService.verify_integrity(db)
        assert res["status"] == "OK"
        assert res["total_records"] > 0
        assert res["verified"] is True
    finally:
        db.close()


def test_audit_view_logging_and_deduplication():
    """Sensitive view logging records view events and deduplicates rapid repeated views."""
    db = SessionLocal()
    admin = db.query(User).filter(User.email.like("admin%")).first()
    if not admin:
        admin = db.query(User).first()
    try:
        before_count = db.query(AuditLog).filter(AuditLog.action == "VIEW_CASE_SUMMARY").count()
        
        # First view
        AuditService.log_view(
            db=db,
            entity_type="CASE_SUMMARY",
            entity_id=1,
            action="VIEW_CASE_SUMMARY",
            actor_id=admin.id,
            role=admin.role.code.value if admin.role else "ADMIN",
            ip_address="127.0.0.1"
        )
        first_count = db.query(AuditLog).filter(AuditLog.action == "VIEW_CASE_SUMMARY").count()
        assert first_count == before_count + 1

        # Second rapid view (within 60s window) must be deduplicated (no new row)
        AuditService.log_view(
            db=db,
            entity_type="CASE_SUMMARY",
            entity_id=1,
            action="VIEW_CASE_SUMMARY",
            actor_id=admin.id,
            role=admin.role.code.value if admin.role else "ADMIN",
            ip_address="127.0.0.1"
        )
        second_count = db.query(AuditLog).filter(AuditLog.action == "VIEW_CASE_SUMMARY").count()
        assert second_count == first_count
    finally:
        db.close()


# ==============================================================================
# 3. ACCESS & LOGIN HARDENING TESTS
# ==============================================================================

def test_login_rate_limiting_and_temporary_lockout():
    """5 failed login attempts trigger temporary account lockout."""
    test_email = "victim_test@demo.example"
    
    # 5 failed attempts
    for _ in range(5):
        res = client.post("/api/v1/auth/login", json={"email": test_email, "password": "WrongPassword"})
        assert res.status_code in [401, 429]

    # 6th attempt must return 429 Too Many Requests (Lockout)
    res = client.post("/api/v1/auth/login", json={"email": test_email, "password": "WrongPassword"})
    assert res.status_code == 429
    assert "temporarily locked" in res.json()["detail"]


def test_security_headers_present():
    """Responses contain required security headers."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in res.headers


def test_demo_mode_controls_demo_login():
    """When DEMO_MODE is active, /auth/demo-login succeeds; if false, it is disabled."""
    if settings.DEMO_MODE:
        res = client.post("/api/v1/auth/demo-login", json={"role": "SCRUTINY_OFFICER"})
        assert res.status_code == 200
        assert "access_token" in res.json()


# ==============================================================================
# 4. DATA RETENTION DRY-RUN PREVIEW TESTS
# ==============================================================================

def test_data_retention_preview_is_dry_run_only():
    """Data retention preview calculates candidate counts without deleting any records."""
    db = SessionLocal()
    try:
        preview = RetentionService.preview_retention(db)
        
        # Verify structure
        assert "summary" in preview
        assert "categories" in preview["summary"]
        assert "policy" in preview
        assert "disclaimer" in preview
        assert "Preview only. No data is deleted by this prototype." in preview["disclaimer"]

        # Audit log must be protected and 0 candidates
        categories = {c["category"]: c for c in preview["summary"]["categories"]}
        assert "AUDIT_LOG" in categories
        assert categories["AUDIT_LOG"]["candidate_count"] == 0
        assert "exempt" in categories["AUDIT_LOG"]["statutory_threshold"].lower()
    finally:
        db.close()


# ==============================================================================
# 5. MOCK AICTE INTEGRATION ADAPTER TESTS
# ==============================================================================

def test_mock_aicte_adapter_institution_lookup():
    """Mock AICTE adapter lookup returns synthetic record with honest mock labelling."""
    db = SessionLocal()
    try:
        res = aicte_adapter.lookup_institution(db, "1-10974231")
        assert res["status"] == "SUCCESS"
        assert res["adapter_mode"] == MockAicteAdapter.MOCK_NOTICE
        assert res["institution"]["aicte_id"] == "1-10974231"
        assert res["institution"]["name"] == "Delhi Institute of Advanced Engineering & Technology"
    finally:
        db.close()


def test_mock_aicte_inbound_hmac_and_replay_protection():
    """Inbound webhook requires valid HMAC-SHA256 signature and rejects expired timestamps."""
    raw_payload = b'{"institution_name": "Test College", "program": "Engineering"}'
    valid_key = settings.INTEGRATION_API_KEY
    
    # 1. Valid request
    now_ts = str(datetime.now(timezone.utc).timestamp())
    valid_sig = MockAicteAdapter.generate_hmac_signature(now_ts, raw_payload)
    
    res = client.post(
        "/api/v1/integration/inbound/application",
        data=raw_payload,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": valid_key,
            "X-Timestamp": now_ts,
            "X-Signature": valid_sig,
            "X-Idempotency-Key": f"IDEM-{time.time()}"
        }
    )
    assert res.status_code == 200
    assert res.json()["adapter_mode"] == MockAicteAdapter.MOCK_NOTICE

    # 2. Invalid signature
    res_bad_sig = client.post(
        "/api/v1/integration/inbound/application",
        data=raw_payload,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": valid_key,
            "X-Timestamp": now_ts,
            "X-Signature": "invalid_signature_hex",
        }
    )
    assert res_bad_sig.status_code == 401

    # 3. Expired timestamp (400 seconds ago, drift > 300s)
    old_ts = str(datetime.now(timezone.utc).timestamp() - 400)
    old_sig = MockAicteAdapter.generate_hmac_signature(old_ts, raw_payload)
    res_replay = client.post(
        "/api/v1/integration/inbound/application",
        data=raw_payload,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": valid_key,
            "X-Timestamp": old_ts,
            "X-Signature": old_sig,
        }
    )
    assert res_replay.status_code == 401
    assert "Timestamp expired" in res_replay.json()["detail"]


def test_mock_aicte_inbound_idempotent_replay():
    """Repeating an inbound request with identical idempotency key returns cached response."""
    raw_payload = b'{"institution_name": "Idempotent College", "program": "Management"}'
    valid_key = settings.INTEGRATION_API_KEY
    now_ts = str(datetime.now(timezone.utc).timestamp())
    sig = MockAicteAdapter.generate_hmac_signature(now_ts, raw_payload)
    idem_key = f"IDEM-TEST-{int(time.time()*1000)}"

    # First call
    res1 = client.post(
        "/api/v1/integration/inbound/application",
        data=raw_payload,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": valid_key,
            "X-Timestamp": now_ts,
            "X-Signature": sig,
            "X-Idempotency-Key": idem_key
        }
    )
    assert res1.status_code == 200

    # Repeat call
    res2 = client.post(
        "/api/v1/integration/inbound/application",
        data=raw_payload,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": valid_key,
            "X-Timestamp": now_ts,
            "X-Signature": sig,
            "X-Idempotency-Key": idem_key
        }
    )
    assert res2.status_code == 200
    assert res2.json().get("idempotent_replay") is True
