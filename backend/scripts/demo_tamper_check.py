#!/usr/bin/env python3
"""
Demonstration script for tamper-evident audit log detection.
Inside a transactional savepoint / rollback block:
1. Temporarily bypasses DB trigger
2. Modifies an action string in an audit row
3. Runs the verifier, demonstrating immediate detection of the broken link
4. Rolls back the transaction completely, preserving real data integrity
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.models import AuditLog
from app.services.audit import AuditService

def main():
    print("=== TAMPER-EVIDENT AUDIT LOG DETECTION DEMO ===")
    print("1. Running pre-check on unaltered database...")
    db = SessionLocal()
    try:
        initial = AuditService.verify_integrity(db)
        print(f"   Pre-check result: {initial['status']} ({initial['total_records']} records intact)")
        assert initial["verified"] is True, "Database already has broken audit chain!"

        # Pick a target row to tamper with
        target_row = db.query(AuditLog).filter(AuditLog.id > 10).order_by(AuditLog.id.asc()).first()
        target_id = target_row.id
        orig_action = target_row.action
        print(f"\n2. Simulating unauthorized database tampering on Record ID {target_id}...")
        print(f"   Original Action: '{orig_action}'")

        # Start simulated tamper inside transaction
        # Drop trigger temporarily inside transaction
        db.execute(text("DROP TRIGGER IF EXISTS trg_audit_log_prevent_modify ON audit_log"))
        db.execute(
            text("UPDATE audit_log SET action = :tampered WHERE id = :id"),
            {"tampered": "TAMPERED_UNAUTHORIZED_CHANGE", "id": target_id}
        )
        print(f"   Altered Action:  'TAMPERED_UNAUTHORIZED_CHANGE' (without updating cryptographic SHA-256 hash)")

        print("\n3. Running cryptographic integrity verifier against tampered state...")
        tamper_report = AuditService.verify_integrity(db)

        if not tamper_report["verified"]:
            print(f"   ✓ DETECTION CONFIRMED! Status: {tamper_report['status']}")
            print(f"   ✓ Broken at Record ID:        {tamper_report.get('broken_at_id')}")
            print(f"   ✓ Detection Rationale:        {tamper_report.get('reason')}")
        else:
            print("   ✗ ERROR: Verifier failed to catch tampered row!")
            sys.exit(1)

        print("\n4. Rolling back transaction to restore pristine audit chain...")
        db.rollback()

        # Re-ensure trigger exists
        db.execute(text("""
            CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE statements are strictly blocked at the database level.';
            END;
            $$ LANGUAGE plpgsql;
            DROP TRIGGER IF EXISTS trg_audit_log_prevent_modify ON audit_log;
            CREATE TRIGGER trg_audit_log_prevent_modify
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_modification();
        """))
        db.commit()

        post = AuditService.verify_integrity(db)
        print(f"   Post-rollback result: {post['status']} ({post['total_records']} records intact)")
        print("\n✓ Tamper detection demo completed successfully.")

    finally:
        db.close()

if __name__ == "__main__":
    main()
