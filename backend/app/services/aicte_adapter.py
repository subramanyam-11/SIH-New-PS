"""
AICTE System Adapter Interface and Mock Implementation.
Follows Build Plan v2 Sections 10 and 11.

NOTE: All responses are synthetic demonstrations.
Label: "MOCK ADAPTER. No real AICTE system is contacted."
"""

import hmac
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import IntegrationLog


class AicteSystemAdapter(ABC):
    """Abstract interface for external AICTE portal integration."""

    @abstractmethod
    def lookup_institution(self, db: Session, aicte_id: str) -> Dict[str, Any]:
        """Look up an institution record by AICTE Permanent ID."""
        pass

    @abstractmethod
    def fetch_intake_and_eoa(self, db: Session, aicte_id: str) -> Dict[str, Any]:
        """Fetch previously approved intake and last Extension of Approval (EoA)."""
        pass

    @abstractmethod
    def push_status_update(
        self, db: Session, application_number: str, new_status: str, remarks: str = ""
    ) -> Dict[str, Any]:
        """Push internal application status updates to external portal."""
        pass

    @abstractmethod
    def receive_external_application(
        self, db: Session, payload: Dict[str, Any], idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Receive a new application submitted via external national portal."""
        pass


class MockAicteAdapter(AicteSystemAdapter):
    """
    Mock implementation of AICTE System Adapter for demonstrations and testing.
    Clearly labelled: 'MOCK ADAPTER. No real AICTE system is contacted'.
    """

    MOCK_NOTICE = "MOCK ADAPTER. No real AICTE system is contacted"

    # Known synthetic mock records
    SYNTHETIC_INSTITUTIONS = {
        "1-10974231": {
            "aicte_id": "1-10974231",
            "name": "Delhi Institute of Advanced Engineering & Technology",
            "region": "Northern",
            "state": "Delhi",
            "district": "New Delhi",
            "address": "Sector 14, Dwarka, Institutional Area",
            "pin": "110078",
            "established_year": 2004,
            "institution_type": "Private-Self Financed",
            "current_status": "APPROVED",
            "last_eoa_academic_year": "2025-2026",
            "approved_intake": 420,
            "programs": ["UG Engineering", "PG Management"],
        },
        "1-4328901": {
            "aicte_id": "1-4328901",
            "name": "Maharashtra Institute of Technology & Research",
            "region": "Western",
            "state": "Maharashtra",
            "district": "Pune",
            "address": "Paud Road, Kothrud",
            "pin": "411038",
            "established_year": 1998,
            "institution_type": "Government-Aided",
            "current_status": "APPROVED",
            "last_eoa_academic_year": "2025-2026",
            "approved_intake": 600,
            "programs": ["UG Engineering", "PG Engineering", "MCA"],
        },
        "1-9876543": {
            "aicte_id": "1-9876543",
            "name": "Bangalore Polytechnic & Vocational Institute",
            "region": "South-Western",
            "state": "Karnataka",
            "district": "Bengaluru Urban",
            "address": "Outer Ring Road, Marathahalli",
            "pin": "560037",
            "established_year": 2012,
            "institution_type": "Private-Self Financed",
            "current_status": "APPROVED",
            "last_eoa_academic_year": "2025-2026",
            "approved_intake": 240,
            "programs": ["Diploma Engineering"],
        },
    }

    @staticmethod
    def verify_inbound_hmac(
        timestamp_str: str, raw_body: bytes, provided_signature: str
    ) -> Tuple[bool, str]:
        """
        Verify HMAC-SHA256 signature and timestamp to prevent replay attacks.
        Max drift: 300 seconds.
        """
        if not timestamp_str:
            return False, "Missing X-Timestamp header"

        try:
            ts = float(timestamp_str)
            now = datetime.now(timezone.utc).timestamp()
            if abs(now - ts) > 300:
                return False, f"Timestamp expired or out of allowed window (drift: {abs(now - ts):.1f}s > 300s)"
        except (ValueError, TypeError):
            return False, "Invalid X-Timestamp header format"

        # Message = f"{timestamp_str}.{raw_body.decode('utf-8')}"
        message = timestamp_str.encode("utf-8") + b"." + raw_body
        expected_sig = hmac.new(
            settings.INTEGRATION_HMAC_SECRET.encode("utf-8"),
            message,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, provided_signature):
            return False, "Invalid HMAC signature"

        return True, "Valid"

    @staticmethod
    def generate_hmac_signature(timestamp_str: str, raw_body: bytes) -> str:
        """Utility for test suites or client requests to generate valid signatures."""
        message = timestamp_str.encode("utf-8") + b"." + raw_body
        return hmac.new(
            settings.INTEGRATION_HMAC_SECRET.encode("utf-8"),
            message,
            hashlib.sha256
        ).hexdigest()

    def lookup_institution(self, db: Session, aicte_id: str) -> Dict[str, Any]:
        """Simulate external AICTE portal institution lookup."""
        inst = self.SYNTHETIC_INSTITUTIONS.get(aicte_id)
        if not inst:
            # Generate deterministic synthetic data for any unknown AICTE ID
            inst = {
                "aicte_id": aicte_id,
                "name": f"Synthetic Technical Institute ({aicte_id})",
                "region": "Northern",
                "state": "Uttar Pradesh",
                "district": "Lucknow",
                "address": "Plot 101, Knowledge Park III",
                "pin": "226001",
                "established_year": 2010,
                "institution_type": "Private-Self Financed",
                "current_status": "APPROVED",
                "last_eoa_academic_year": "2025-2026",
                "approved_intake": 300,
                "programs": ["UG Engineering"],
            }

        result = {
            "adapter_mode": self.MOCK_NOTICE,
            "status": "SUCCESS",
            "institution": inst,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        # Outbound log
        log = IntegrationLog(
            direction="OUTBOUND",
            operation="LOOKUP_INSTITUTION",
            adapter_type="MOCK_AICTE",
            status="SUCCESS",
            request_summary={"aicte_id": aicte_id},
            response_summary={"institution_name": inst["name"], "status": inst["current_status"]},
            completed_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()

        return result

    def fetch_intake_and_eoa(self, db: Session, aicte_id: str) -> Dict[str, Any]:
        """Fetch previously approved intake and EoA synthetic history."""
        inst = self.lookup_institution(db, aicte_id)["institution"]
        eoa_history = [
            {"academic_year": "2023-2024", "status": "APPROVED", "intake": inst["approved_intake"] - 60},
            {"academic_year": "2024-2025", "status": "APPROVED", "intake": inst["approved_intake"]},
            {"academic_year": "2025-2026", "status": "APPROVED", "intake": inst["approved_intake"]},
        ]

        result = {
            "adapter_mode": self.MOCK_NOTICE,
            "status": "SUCCESS",
            "aicte_id": aicte_id,
            "current_approved_intake": inst["approved_intake"],
            "last_eoa_academic_year": inst["last_eoa_academic_year"],
            "eoa_history": eoa_history,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        log = IntegrationLog(
            direction="OUTBOUND",
            operation="FETCH_INTAKE_AND_EOA",
            adapter_type="MOCK_AICTE",
            status="SUCCESS",
            request_summary={"aicte_id": aicte_id},
            response_summary={"approved_intake": inst["approved_intake"], "years": len(eoa_history)},
            completed_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()

        return result

    def push_status_update(
        self, db: Session, application_number: str, new_status: str, remarks: str = ""
    ) -> Dict[str, Any]:
        """Simulate pushing status updates back to the national portal."""
        result = {
            "adapter_mode": self.MOCK_NOTICE,
            "status": "SUCCESS",
            "ack_id": f"ACK-{int(time.time())}-{application_number[:8]}",
            "application_number": application_number,
            "pushed_status": new_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        log = IntegrationLog(
            direction="OUTBOUND",
            operation="PUSH_STATUS_UPDATE",
            adapter_type="MOCK_AICTE",
            status="SUCCESS",
            request_summary={
                "application_number": application_number,
                "new_status": new_status,
                "remarks": remarks,
            },
            response_summary=result,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()

        return result

    def receive_external_application(
        self, db: Session, payload: Dict[str, Any], idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle inbound webhook/API call from external portal to ingest an application.
        Supports idempotency check.
        """
        # Check idempotency
        if idempotency_key:
            existing = (
                db.query(IntegrationLog)
                .filter(
                    IntegrationLog.idempotency_key == idempotency_key,
                    IntegrationLog.direction == "INBOUND",
                    IntegrationLog.status == "SUCCESS",
                )
                .first()
            )
            if existing and existing.response_summary:
                cached = dict(existing.response_summary)
                cached["idempotent_replay"] = True
                return cached

        app_num = payload.get("application_number") or f"APP-EXT-{int(time.time())}"
        inst_name = payload.get("institution_name", "External Applicant Institute")

        result = {
            "adapter_mode": self.MOCK_NOTICE,
            "status": "SUCCESS",
            "ingestion_id": f"INGEST-{int(time.time())}",
            "application_number": app_num,
            "message": f"Successfully ingested application for {inst_name}",
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        log = IntegrationLog(
            direction="INBOUND",
            operation="RECEIVE_EXTERNAL_APPLICATION",
            adapter_type="MOCK_AICTE",
            status="SUCCESS",
            idempotency_key=idempotency_key,
            request_summary={"institution_name": inst_name, "application_number": app_num},
            response_summary=result,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()

        return result


# Singleton instance
aicte_adapter = MockAicteAdapter()
