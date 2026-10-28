from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc
from app.core.database import get_db
from app.core.config import settings
from app.core.rbac import get_current_user, get_user_scope, UserScope
from app.models import (
    Application, StageHistory, Stage, StagePath, ApplicationCategory,
    Institution, User, UserRoleEnum, ApplicationStatusEnum,
    ApplicationCommunication, CaseSummary, SystemConfig
)
from app.schemas import (
    ApplicationOut, ApplicationDetailOut, ApplicationCreate,
    StageTransitionRequest, ApplicationReturnRequest, ApplicationDecisionRequest,
    StageHistoryOut, CommunicationOut, CaseSummaryOut, DeficiencyTagOut, AdvanceClockRequest
)
from app.services.clock import get_system_time, calculate_sla_status, advance_clock, reset_clock
from app.services.workflow_engine import WorkflowEngine, get_config_val
from app.services.audit import log_audit_event

router = APIRouter(prefix="", tags=["Applications"])


def enrich_app_out(app: Application, thresholds: Optional[dict] = None) -> ApplicationOut:
    """Enriches Application model into ApplicationOut with real-time computed SLA ageing."""
    sla_info = calculate_sla_status(
        stage_entered_at=app.stage_entered_at,
        stage_due_date=app.stage_due_date,
        default_sla_days=app.current_stage.default_sla_days if app.current_stage else 7,
        thresholds=thresholds
    )

    return ApplicationOut(
        id=app.id,
        application_number=app.application_number,
        academic_year=app.academic_year,
        institution_id=app.institution_id,
        institution_name=app.institution.name if app.institution else None,
        institution_aicte_id=app.institution.aicte_id if app.institution else None,
        category_id=app.category_id,
        category_title=app.category.title if app.category else None,
        stage_path_id=app.stage_path_id,
        stage_path_name=app.stage_path.name if app.stage_path else None,
        stage_path_code=app.stage_path.code if app.stage_path else None,
        current_stage_id=app.current_stage_id,
        current_stage_code=app.current_stage.code if app.current_stage else None,
        current_stage_name=app.current_stage.name if app.current_stage else None,
        responsible_role=app.current_stage.responsible_role.value if app.current_stage else None,
        status=app.status.value,
        region_id=app.region_id,
        region_name=app.region.name if app.region else None,
        assigned_officer_id=app.assigned_officer_id,
        assigned_officer_name=app.assigned_officer.full_name if app.assigned_officer else None,
        stage_entered_at=app.stage_entered_at,
        stage_due_date=app.stage_due_date,
        days_in_stage=sla_info["days_in_stage"],
        days_remaining=sla_info["days_remaining"],
        ageing_bucket=sla_info["ageing_bucket"],
        revert_count=app.revert_count,
        escalation_required=app.escalation_required,
        escalation_reason=app.escalation_reason,
        delay_risk_score=app.delay_risk_score,
        approval_letter_ref=app.approval_letter_ref
    )


@router.get("/applications", response_model=Dict[str, Any])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
    region_id: Optional[int] = Query(None),
    stage_id: Optional[int] = Query(None),
    stage_code: Optional[str] = Query(None),
    institution_id: Optional[int] = Query(None),
    officer_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    ageing_bucket: Optional[str] = Query(None),
    stage_path_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc")
):
    """
    List applications with multi-attribute filtering, search, pagination, and role-based data scoping.
    """
    query = db.query(Application).options(
        joinedload(Application.institution),
        joinedload(Application.current_stage),
        joinedload(Application.category),
        joinedload(Application.stage_path),
        joinedload(Application.region),
        joinedload(Application.assigned_officer)
    )

    # 1. Apply RBAC Scoping
    if scope.is_institution:
        query = query.filter(Application.institution_id == scope.institution_id)
    elif scope.is_regional and scope.region_id:
        query = query.filter(Application.region_id == scope.region_id)

    # 2. Filters
    if region_id and scope.is_national:
        query = query.filter(Application.region_id == region_id)
    if institution_id:
        query = query.filter(Application.institution_id == institution_id)
    if stage_id:
        query = query.filter(Application.current_stage_id == stage_id)
    if stage_code:
        query = query.join(Stage, Application.current_stage_id == Stage.id).filter(Stage.code == stage_code)
    if officer_id:
        query = query.filter(Application.assigned_officer_id == officer_id)
    if status_filter:
        query = query.filter(Application.status == status_filter.upper())
    if stage_path_id:
        query = query.filter(Application.stage_path_id == stage_path_id)
    if search:
        query = query.join(Institution, Application.institution_id == Institution.id).filter(
            (Application.application_number.ilike(f"%{search}%")) |
            (Institution.name.ilike(f"%{search}%")) |
            (Institution.aicte_id.ilike(f"%{search}%"))
        )

    # Sort
    order_func = desc if sort_order.lower() == "desc" else asc
    if sort_by == "due_date":
        query = query.order_by(order_func(Application.stage_due_date))
    elif sort_by == "created_at":
        query = query.order_by(order_func(Application.created_at))
    elif sort_by == "risk_score":
        query = query.order_by(desc(Application.delay_risk_score))
    else:
        query = query.order_by(order_func(Application.id))

    total = query.count()
    records = query.offset(skip).limit(limit).all()

    # Thresholds for SLA computation
    thresholds = get_config_val(db, "alert_thresholds", {})
    enriched = [enrich_app_out(app, thresholds) for app in records]

    # Post-filter on ageing_bucket if requested
    if ageing_bucket:
        bucket_upper = ageing_bucket.upper()
        enriched = [e for e in enriched if e.ageing_bucket == bucket_upper]
        total = len(enriched)

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "applications": enriched
    }


@router.get("/applications/{id}", response_model=ApplicationDetailOut)
def get_application_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """Full application dossier including current stage, SLA status, communications, and summary."""
    app = db.query(Application).options(
        joinedload(Application.institution),
        joinedload(Application.current_stage),
        joinedload(Application.category),
        joinedload(Application.stage_path),
        joinedload(Application.region),
        joinedload(Application.assigned_officer),
        joinedload(Application.communications),
        joinedload(Application.case_summary)
    ).filter(Application.id == id).first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # Scoping check
    if scope.is_institution and app.institution_id != scope.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this application")
    if scope.is_regional and scope.region_id and app.region_id != scope.region_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Application belongs to another regional office.")

    thresholds = get_config_val(db, "alert_thresholds", {})
    base = enrich_app_out(app, thresholds)

    comms = [
        CommunicationOut(
            id=c.id,
            application_id=c.application_id,
            template_code=c.template_code,
            subject=c.subject,
            body=c.body,
            recipient_email=c.recipient_email,
            status=c.status,
            created_at=c.created_at,
            sent_at=c.sent_at
        ) for c in (app.communications or [])
    ]

    case_summary = None
    if app.case_summary:
        case_summary = CaseSummaryOut(
            id=app.case_summary.id,
            application_id=app.case_summary.application_id,
            executive_summary=app.case_summary.executive_summary,
            key_findings=app.case_summary.key_findings or [],
            compliance_flags=app.case_summary.compliance_flags or [],
            risk_assessment=app.case_summary.risk_assessment,
            generated_by=app.case_summary.generated_by,
            last_generated_at=app.case_summary.last_generated_at
        )

    return ApplicationDetailOut(
        **base.model_dump(),
        institution=app.institution,
        category=app.category,
        stage_path=app.stage_path,
        current_stage=app.current_stage,
        approval_letter_data=app.approval_letter_data,
        communications=comms,
        case_summary=case_summary
    )


@router.get("/applications/{id}/timeline", response_model=List[StageHistoryOut])
def get_application_timeline(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """Returns chronological stage audit history with actors, deficiency reasons, and dwell time."""
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if scope.is_institution and app.institution_id != scope.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    history = db.query(StageHistory).options(
        joinedload(StageHistory.from_stage),
        joinedload(StageHistory.to_stage),
        joinedload(StageHistory.actor).joinedload(User.role)
    ).filter(StageHistory.application_id == id).order_by(StageHistory.entered_at.asc()).all()

    result = []
    for h in history:
        result.append(StageHistoryOut(
            id=h.id,
            application_id=h.application_id,
            from_stage_id=h.from_stage_id,
            to_stage_id=h.to_stage_id,
            from_stage_name=h.from_stage.name if h.from_stage else None,
            to_stage_name=h.to_stage.name if h.to_stage else None,
            action_taken=h.action_taken,
            actor_id=h.actor_id,
            actor_name=h.actor.full_name if h.actor else "System",
            actor_role=h.actor.role.code.value if (h.actor and h.actor.role) else None,
            status=h.status.value,
            reason=h.reason,
            deficiency_tags=h.deficiency_tags,
            entered_at=h.entered_at,
            completed_at=h.completed_at,
            duration_hours=h.duration_hours
        ))
    return result


@router.post("/applications", response_model=ApplicationDetailOut)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """Submits and dockets a new institutional approval application."""
    # Compute next sequence number
    count = db.query(Application).count()
    app_num = f"AICTE/2026/APP-{10001 + count:05d}"

    app = WorkflowEngine.submit_application(
        db=db,
        actor=current_user,
        institution_id=payload.institution_id,
        category_id=payload.category_id,
        application_number=app_num,
        stage_path_id=payload.stage_path_id,
        academic_year=payload.academic_year or "2026-2027"
    )

    return get_application_detail(id=app.id, db=db, current_user=current_user, scope=scope)


@router.post("/applications/{id}/complete-stage", response_model=ApplicationDetailOut)
def complete_stage(
    id: int,
    payload: StageTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Authorized officer marks current stage complete, auto-advancing to the next stage in path.
    Final decision cannot be completed here; requires /decision.
    """
    app, next_stage = WorkflowEngine.complete_stage(
        db=db,
        application_id=id,
        actor=current_user,
        remarks=payload.remarks
    )
    return get_application_detail(id=app.id, db=db, current_user=current_user, scope=scope)


@router.post("/applications/{id}/return", response_model=ApplicationDetailOut)
def return_application(
    id: int,
    payload: ApplicationReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Reverts application to RE_SCRUTINY citing mandatory deficiency tags and remarks.
    Enforces the configurable 2-cycle revert cap from system_config.
    """
    app = WorkflowEngine.return_application(
        db=db,
        application_id=id,
        actor=current_user,
        deficiency_tags=payload.deficiency_tags,
        reason=payload.reason
    )
    return get_application_detail(id=app.id, db=db, current_user=current_user, scope=scope)


@router.post("/applications/{id}/decision", response_model=ApplicationDetailOut)
def record_decision(
    id: int,
    payload: ApplicationDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Authorized Competent Authority records final statutory APPROVAL or REJECTION.
    System never decides; humans decide.
    Generates a formal mock Letter of Approval with sample watermark.
    """
    app = WorkflowEngine.record_decision(
        db=db,
        application_id=id,
        actor=current_user,
        decision=payload.decision,
        remarks=payload.remarks
    )
    return get_application_detail(id=app.id, db=db, current_user=current_user, scope=scope)


@router.get("/applications/{id}/communications", response_model=List[CommunicationOut])
def get_application_communications(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all drafted and dispatched routine communications for an application."""
    comms = db.query(ApplicationCommunication).filter(
        ApplicationCommunication.application_id == id
    ).order_by(ApplicationCommunication.created_at.desc()).all()
    return comms


@router.post("/applications/{id}/communications/{cid}/mark-sent", response_model=CommunicationOut)
def mark_communication_sent(
    id: int,
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Officer reviews a drafted routine message and formally marks it as dispatched."""
    comm = db.query(ApplicationCommunication).filter(
        ApplicationCommunication.id == cid,
        ApplicationCommunication.application_id == id
    ).first()
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Communication not found")

    comm.status = "SENT"
    comm.sent_at = get_system_time()
    comm.sent_by = current_user.id
    db.commit()
    db.refresh(comm)
    return comm


@router.get("/applications/{id}/summary", response_model=CaseSummaryOut)
def get_case_summary(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the executive case brief synthesized by deterministic template service."""
    summary = db.query(CaseSummary).filter(CaseSummary.application_id == id).first()
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")
    return summary


@router.get("/config/deficiency-tags", response_model=List[DeficiencyTagOut])
def get_deficiency_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the configured taxonomy of statutory deficiency tags from system_config."""
    raw_tags = get_config_val(db, "deficiency_tags", [])
    return [DeficiencyTagOut(**t) for t in raw_tags]


@router.get("/application-categories", response_model=List[Any])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns application categories for dropdown selection."""
    return db.query(ApplicationCategory).order_by(ApplicationCategory.id).all()


@router.post("/demo/advance-clock", response_model=Dict[str, Any])
def advance_system_clock(
    payload: AdvanceClockRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Demo/Presentation utility: moves simulated system time forward by N hours.
    Available ONLY in DEMO_MODE for ADMIN role.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clock time-travel is disabled in production")
    if current_user.role.code != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins can advance system clock")

    new_time = advance_clock(payload.hours)
    return {
        "status": "success",
        "advanced_hours": payload.hours,
        "simulated_time": new_time.isoformat(),
        "message": f"System clock advanced by {payload.hours} hours."
    }


@router.post("/demo/reset-clock", response_model=Dict[str, Any])
def reset_system_clock(
    current_user: User = Depends(get_current_user)
):
    """Resets system clock to actual real-time UTC."""
    if not settings.DEMO_MODE or current_user.role.code != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    curr = reset_clock()
    return {"status": "success", "simulated_time": curr.isoformat(), "message": "Clock reset to real-time UTC."}
