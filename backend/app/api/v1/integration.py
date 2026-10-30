"""
AICTE National Portal Integration Endpoints (Mock Adapter).
Follows Build Plan v2 Sections 10 and 11.

NOTE: All responses are synthetic demonstrations.
Label: "MOCK ADAPTER. No real AICTE system is contacted."
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.rbac import get_current_user
from app.models import User, IntegrationLog
from app.services.aicte_adapter import aicte_adapter, MockAicteAdapter


router = APIRouter(
    prefix="/integration",
    tags=["AICTE National Portal Integration (Mock Adapter)"]
)


class StatusPushRequest(BaseModel):
    application_number: str = Field(..., description="Application identifier, e.g. APP-2026-0001")
    new_status: str = Field(..., description="Target status, e.g. SCRUTINY_PASSED, EOA_ISSUED")
    remarks: Optional[str] = Field("", description="Optional remarks for audit sync")


class InboundApplicationPayload(BaseModel):
    application_number: Optional[str] = None
    aicte_id: Optional[str] = None
    institution_name: str
    program: str
    academic_year: str = "2026-2027"
    applied_intake: int = 120
    contact_email: Optional[str] = None


@router.get("/status")
def get_adapter_status():
    """Returns adapter operational health and mock operational notice."""
    return {
        "adapter_name": "AICTE National Portal Adapter",
        "implementation": "MockAicteAdapter",
        "adapter_mode": MockAicteAdapter.MOCK_NOTICE,
        "is_mock": True,
        "hmac_auth_enabled": True,
        "replay_window_seconds": 300,
        "supported_operations": [
            "LOOKUP_INSTITUTION",
            "FETCH_INTAKE_AND_EOA",
            "PUSH_STATUS_UPDATE",
            "RECEIVE_EXTERNAL_APPLICATION"
        ],
        "secondary_adapters": [
            {
                "name": "SMTP Notification Adapter",
                "status": "CONFIGURED" if settings.EMAIL_SEND_ENABLED else "STANDBY",
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT
            }
        ]
    }


@router.get("/institution/{aicte_id}")
def lookup_institution_by_aicte_id(
    aicte_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Look up an institution record by AICTE Permanent ID.
    Used during application drafting to pre-fill verified details.
    """
    return aicte_adapter.lookup_institution(db, aicte_id)


@router.get("/institution/{aicte_id}/intake-history")
def get_intake_and_eoa_history(
    aicte_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch previously approved intake and last Extension of Approval history."""
    return aicte_adapter.fetch_intake_and_eoa(db, aicte_id)


@router.post("/sync/status")
def push_status_update(
    body: StatusPushRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Push application status updates to external portal.
    Simulated by MockAicteAdapter with audit integration log.
    """
    return aicte_adapter.push_status_update(
        db,
        application_number=body.application_number,
        new_status=body.new_status,
        remarks=body.remarks or ""
    )


@router.post("/inbound/application")
async def receive_inbound_application(
    request: Request,
    payload: InboundApplicationPayload,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
):
    """
    Inbound webhook/API for receiving an application from an external national portal.
    Requires:
      - X-API-Key matching configured secret
      - X-Timestamp (drift <= 300 seconds)
      - X-Signature (HMAC-SHA256 signature of timestamp.raw_body)
      - Optional X-Idempotency-Key for replay prevention
    """
    # 1. API Key validation
    if not x_api_key or x_api_key != settings.INTEGRATION_API_KEY:
        # Log rejected attempt
        log = IntegrationLog(
            direction="INBOUND",
            operation="RECEIVE_EXTERNAL_APPLICATION",
            adapter_type="MOCK_AICTE",
            status="REJECTED",
            error_message="Invalid or missing X-API-Key",
            idempotency_key=x_idempotency_key
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header"
        )

    # 2. Raw body and signature check
    raw_body = await request.body()
    is_valid, reason = MockAicteAdapter.verify_inbound_hmac(
        timestamp_str=x_timestamp or "",
        raw_body=raw_body,
        provided_signature=x_signature or ""
    )

    if not is_valid:
        log = IntegrationLog(
            direction="INBOUND",
            operation="RECEIVE_EXTERNAL_APPLICATION",
            adapter_type="MOCK_AICTE",
            status="REJECTED",
            error_message=f"HMAC/Replay verification failed: {reason}",
            idempotency_key=x_idempotency_key
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Security verification failed: {reason}"
        )

    # 3. Process ingestion through adapter
    return aicte_adapter.receive_external_application(
        db=db,
        payload=payload.dict(),
        idempotency_key=x_idempotency_key
    )


@router.get("/logs")
def get_integration_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve recent integration sync log entries."""
    logs = (
        db.query(IntegrationLog)
        .order_by(IntegrationLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "adapter_mode": MockAicteAdapter.MOCK_NOTICE,
        "total": len(logs),
        "items": [
            {
                "id": log.id,
                "direction": log.direction,
                "operation": log.operation,
                "adapter_type": log.adapter_type,
                "status": log.status,
                "idempotency_key": log.idempotency_key,
                "request_summary": log.request_summary,
                "response_summary": log.response_summary,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None
            }
            for log in logs
        ]
    }
