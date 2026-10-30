#!/usr/bin/env python3
"""
CLI utility to verify cryptographic hash chain integrity of the audit log.
Usage:
    PYTHONPATH=backend python scripts/verify_audit_chain.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.services.audit import AuditService

def main():
    print("=== AICTE AUDIT LOG INTEGRITY VERIFIER ===")
    print("Walking cryptographic SHA-256 hash chain...")
    db = SessionLocal()
    try:
        report = AuditService.verify_integrity(db)
        print(f"Total audit records examined: {report.get('total_records')}")
        if report.get("verified"):
            print(f"✓ Status: {report.get('status')}")
            print(f"✓ Latest chain hash: {report.get('latest_hash')}")
            print(f"✓ {report.get('message')}")
            sys.exit(0)
        else:
            print(f"✗ Status: {report.get('status')}")
            print(f"✗ Broken at record ID: {report.get('broken_at_id')}")
            print(f"✗ Reason: {report.get('reason')}")
            sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
