from typing import List, Optional, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import get_current_user, UserScope, get_user_scope
from app.models import Undertaking, UndertakingStatusEnum, UndertakingEvidence, UndertakingHistory, Application, Institution, User
from app.schemas import UndertakingOut, UndertakingEvidenceOut, UndertakingHistoryOut, UndertakingVerifyRequest
from app.services.undertaking_service import UndertakingService
from app.services.file_service import FileStorageService
from app.services.clock import ClockService

router = APIRouter(prefix="/undertakings", tags=["Undertakings"])


def enrich_undertaking(ut: Undertaking) -> Dict[str, Any]:
    inst = ut.institution
    app = ut.application
    reg = inst.region if inst else (app.region if app else None)
    
    now = ClockService.get_now().date()
    days_left = (ut.due_date - now).days
    is_overdue = days_left < 0 and ut.status in [
        UndertakingStatusEnum.PENDING,
        UndertakingStatusEnum.SUBMITTED,
        UndertakingStatusEnum.NEEDS_MORE_EVIDENCE,
        UndertakingStatusEnum.OVERDUE,
        UndertakingStatusEnum.ESCALATED,
    ]

    evidences_out = []
    for ev in ut.evidence_items:
        evidences_out.append({
            "id": ev.id,
            "undertaking_id": ev.undertaking_id,
            "file_id": ev.file_id,
            "file_name": ev.file_name,
            "file_url": ev.file_url,
            "comments": ev.comments,
            "uploaded_by": ev.submitted_by,
            "uploaded_by_name": ev.submitter.full_name if ev.submitter else None,
            "uploaded_at": ev.submitted_at,
        })

    history_out = []
    for h in ut.history:
        history_out.append({
            "id": h.id,
            "undertaking_id": h.undertaking_id,
            "from_status": h.from_status,
            "to_status": h.to_status,
            "action": h.to_status,
            "remarks": h.remarks,
            "actor_id": h.action_by or 0,
            "actor_name": h.actor.full_name if h.actor else None,
            "actor_role": h.action_role,
            "created_at": h.created_at,
        })

    return {
        "id": ut.id,
        "application_id": ut.application_id,
        "application_number": app.application_number if app else None,
        "institution_id": ut.institution_id,
        "institution_name": inst.name if inst else None,
        "region_id": reg.id if reg else None,
        "region_name": reg.name if reg else None,
        "clause_number": getattr(ut, "clause_number", "Clause 4.1"),
        "title": ut.condition_title,
        "description": ut.description,
        "due_date": ut.due_date,
        "status": ut.status.value if hasattr(ut.status, "value") else str(ut.status),
        "is_overdue": is_overdue,
        "days_until_due": days_left,
        "compliance_evidence_url": ut.evidence_items[0].file_url if ut.evidence_items else None,
        "remarks": ut.verification_remarks,
        "rejection_count": ut.rejection_count,
        "escalated_to_tier": ut.escalated_to_tier,
        "escalation_reason": ut.escalation_reason,
        "created_at": ut.created_at,
        "evidences": evidences_out,
        "history": history_out,
    }


@router.get("")
def list_undertakings(
    status_filter: Optional[str] = Query(None, alias="status"),
    region_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    is_overdue: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    List undertakings with strict scoping:
    - Institution user sees only their own institution's undertakings.
    - Regional officers see their region's undertakings.
    - Competent Authority only sees escalated undertakings (overdue or rejected >= 2 times).
    - Admin sees all.
    """
    query = db.query(Undertaking).join(Institution, Undertaking.institution_id == Institution.id)

    if scope.is_institution:
        query = query.filter(Undertaking.institution_id == scope.institution_id)
    elif current_user.role and current_user.role.code == "COMPETENT_AUTHORITY":
        # Competent Authority only reviews escalated undertakings
        query = query.filter(Undertaking.status == UndertakingStatusEnum.ESCALATED)
    elif scope.is_regional and scope.region_id:
        query = query.filter(Institution.region_id == scope.region_id)

    if region_id and scope.is_national:
        query = query.filter(Institution.region_id == region_id)

    if institution_id and not scope.is_institution:
        query = query.filter(Undertaking.institution_id == institution_id)

    if status_filter:
        query = query.filter(Undertaking.status == status_filter)

    now = ClockService.get_now().date()
    if is_overdue is True:
        query = query.filter(
            Undertaking.due_date < now,
            Undertaking.status.in_([
                UndertakingStatusEnum.PENDING,
                UndertakingStatusEnum.SUBMITTED,
                UndertakingStatusEnum.NEEDS_MORE_EVIDENCE,
                UndertakingStatusEnum.OVERDUE,
                UndertakingStatusEnum.ESCALATED,
            ])
        )

    items = query.order_by(Undertaking.due_date.asc()).all()
    return [enrich_undertaking(u) for u in items]


@router.get("/{undertaking_id}")
def get_undertaking(
    undertaking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    ut = db.query(Undertaking).filter(Undertaking.id == undertaking_id).first()
    if not ut:
        raise HTTPException(status_code=404, detail="Undertaking not found")

    if scope.is_institution and ut.institution_id != scope.institution_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot view another institution's undertaking")

    return enrich_undertaking(ut)


@router.post("/{undertaking_id}/upload-evidence")
def upload_evidence(
    undertaking_id: int,
    file: Optional[UploadFile] = File(None),
    comments: Optional[str] = Form(None),
    file_id: Optional[int] = Form(None),
    file_name: Optional[str] = Form(None),
    file_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload evidence artifact for compliance with an undertaking.
    Transitions status to SUBMITTED.
    """
    if file:
        uploaded = FileStorageService.save_file(
            db=db,
            file=file,
            uploaded_by=current_user,
            entity_type="UNDERTAKING_EVIDENCE",
            entity_id=undertaking_id
        )
        final_file_id = uploaded.id
        final_file_name = uploaded.original_filename
        final_file_url = f"/api/v1/files/{uploaded.id}/download"
    elif file_id:
        final_file_id = file_id
        final_file_name = file_name or f"Evidence_{file_id}"
        final_file_url = file_url or f"/api/v1/files/{file_id}/download"
    else:
        raise HTTPException(status_code=400, detail="Either a file upload or an existing file_id is required.")

    evidence = UndertakingService.submit_evidence(
        db=db,
        undertaking_id=undertaking_id,
        file_name=final_file_name,
        file_url=final_file_url,
        file_id=final_file_id,
        comments=comments,
        actor=current_user
    )

    ut = db.query(Undertaking).filter(Undertaking.id == undertaking_id).first()
    return enrich_undertaking(ut)


@router.post("/{undertaking_id}/verify")
def verify_undertaking(
    undertaking_id: int,
    payload: UndertakingVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Scrutiny Officer verification of undertaking evidence:
    - VERIFIED: marks compliant, resolves linked alerts.
    - REJECTED: increments rejection counter; escalates to Competent Authority if threshold met.
    - NEEDS_MORE_EVIDENCE: prompts institution for further documentation.
    Institution users cannot call this endpoint.
    """
    ut = UndertakingService.verify_undertaking(
        db=db,
        undertaking_id=undertaking_id,
        decision=payload.action,
        remarks=payload.remarks or "Verification completed",
        actor=current_user
    )
    return enrich_undertaking(ut)
