from typing import List, Optional, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import get_current_user, UserScope, get_user_scope
from app.models import EvcVisit, EvcExpert, EvcStatusEnum, Application, Institution, User
from app.schemas import (
    EvcVisitOut, EvcExpertOut, SuggestedExpertOut,
    EvcPanelAssignRequest, EvcScheduleRequest, EvcVisitDoneRequest, EvcCloseRequest
)
from app.services.evc_service import EvcService
from app.services.clock import ClockService, normalize_dt

router = APIRouter(prefix="/evc", tags=["EVC Scheduling"])


def enrich_evc_visit(visit: EvcVisit) -> Dict[str, Any]:
    app = visit.application
    inst = app.institution if app else None
    reg = app.region if app else None
    
    # Calculate days waiting
    now = normalize_dt(ClockService.get_now())
    created_dt = normalize_dt(visit.created_at) if visit.created_at else now
    days_waiting = max(0.0, round((now - created_dt).total_seconds() / 86400, 1))

    is_new = False
    if inst:
        is_new = (getattr(inst, "is_new", False) or getattr(inst, "year_established", 2000) >= 2024 or "New" in inst.name)

    return {
        "id": visit.id,
        "application_id": visit.application_id,
        "application_number": app.application_number if app else None,
        "institution_id": inst.id if inst else None,
        "institution_name": inst.name if inst else None,
        "institution_city": inst.city if inst else None,
        "region_id": reg.id if reg else None,
        "region_name": reg.name if reg else None,
        "is_new_institution": is_new,
        "stage_id": app.current_stage_id if app else None,
        "status": visit.status.value if hasattr(visit.status, "value") else str(visit.status),
        "assigned_experts": visit.assigned_experts or [],
        "scheduled_date": visit.scheduled_date,
        "scheduled_time": visit.scheduled_time,
        "completed_at": visit.visit_completed_at,
        "visit_summary": visit.visit_summary,
        "report_file_id": visit.report_file_id,
        "closed_at": visit.closed_at,
        "closed_by": visit.closed_by,
        "days_waiting": days_waiting,
        "created_at": visit.created_at,
    }


@router.get("/visits")
def list_evc_visits(
    status_filter: Optional[str] = Query(None, alias="status"),
    region_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    List EVC visits according to user scope and optional status/region filters.
    """
    query = db.query(EvcVisit).join(Application, EvcVisit.application_id == Application.id)

    if scope.is_institution:
        query = query.filter(Application.institution_id == scope.institution_id)
    elif scope.is_regional and scope.region_id:
        query = query.filter(Application.region_id == scope.region_id)

    if region_id and scope.is_national:
        query = query.filter(Application.region_id == region_id)

    if status_filter:
        query = query.filter(EvcVisit.status == status_filter)

    visits = query.order_by(EvcVisit.created_at.desc()).all()
    return [enrich_evc_visit(v) for v in visits]


@router.get("/visits/{visit_id}")
def get_evc_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    visit = db.query(EvcVisit).filter(EvcVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="EVC visit not found")

    app = visit.application
    if scope.is_institution and app.institution_id != scope.institution_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return enrich_evc_visit(visit)


@router.get("/experts")
def list_experts(
    region: Optional[str] = None,
    discipline: Optional[str] = None,
    available_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List synthetic EVC experts pool for panel selection.
    """
    query = db.query(EvcExpert)
    if region:
        query = query.filter(EvcExpert.region.ilike(f"%{region}%"))
    if discipline:
        query = query.filter(EvcExpert.discipline.ilike(f"%{discipline}%"))
    if available_only:
        query = query.filter(EvcExpert.is_available == True)

    experts = query.order_by(EvcExpert.name.asc()).all()
    
    # Calculate active visits for each expert
    active_visits = db.query(EvcVisit).filter(
        EvcVisit.status.in_([
            EvcStatusEnum.ASSIGNED,
            EvcStatusEnum.SCHEDULED,
            EvcStatusEnum.VISIT_DONE,
        ])
    ).all()

    results = []
    for exp in experts:
        count = 0
        for v in active_visits:
            if v.assigned_experts and isinstance(v.assigned_experts, list):
                for a in v.assigned_experts:
                    if isinstance(a, dict) and a.get("id") == exp.id:
                        count += 1
        results.append({
            "id": exp.id,
            "name": exp.name,
            "designation": exp.designation,
            "discipline": exp.discipline,
            "region": exp.region,
            "home_institution": exp.home_institution,
            "home_city": exp.home_city,
            "max_concurrent_visits": exp.max_concurrent_visits,
            "active_visits_count": count,
            "is_available": exp.is_available,
        })
    return results


@router.get("/visits/{visit_id}/suggested-experts")
def get_suggested_experts(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns decision-support ranking of candidate experts for a given visit with conflict detection.
    """
    return EvcService.get_suggested_experts(db, visit_id)


@router.post("/visits/{visit_id}/assign-panel")
def assign_panel(
    visit_id: int,
    payload: EvcPanelAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assigns exactly 3 members to an EVC inspection panel.
    Checks conflicts (home institution, city, concurrency max 2).
    """
    visit = EvcService.assign_panel(
        db=db,
        visit_id=visit_id,
        expert_ids=payload.expert_ids,
        actor=current_user
    )
    return enrich_evc_visit(visit)


@router.post("/visits/{visit_id}/schedule")
def schedule_visit(
    visit_id: int,
    payload: EvcScheduleRequest,
    visit_type: Optional[str] = "PHYSICAL",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Schedules inspection date and time.
    Auto-resolves RULE_EVC_UNSCHEDULED alerts.
    """
    visit = EvcService.schedule_visit(
        db=db,
        visit_id=visit_id,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time or "10:00 AM",
        visit_type=visit_type,
        actor=current_user
    )
    return enrich_evc_visit(visit)


@router.post("/visits/{visit_id}/complete-visit")
def complete_visit(
    visit_id: int,
    payload: EvcVisitDoneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks physical visit completed by the committee.
    Transitions status to VISIT_DONE.
    """
    visit = EvcService.mark_visit_done(
        db=db,
        visit_id=visit_id,
        visit_summary=payload.visit_summary,
        actor=current_user
    )
    return enrich_evc_visit(visit)


@router.post("/visits/{visit_id}/upload-report")
def upload_report(
    visit_id: int,
    outcome_recommendation: str = "RECOMMENDED",
    remarks: str = "Report submitted by EVC Committee",
    report_file_id: Optional[int] = None,
    report_file_url: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads inspection report and outcome recommendation.
    Transitions status to REPORT_RECEIVED. Auto-resolves RULE_EVC_VISIT_OVERDUE alerts.
    """
    visit = EvcService.upload_report(
        db=db,
        visit_id=visit_id,
        outcome_recommendation=outcome_recommendation,
        remarks=remarks,
        report_file_id=report_file_id,
        report_file_url=report_file_url,
        actor=current_user
    )
    return enrich_evc_visit(visit)


@router.post("/visits/{visit_id}/close")
def close_visit(
    visit_id: int,
    payload: Optional[EvcCloseRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Closes out the EVC visit.
    Transitions status to CLOSED.
    """
    visit = EvcService.close_visit(
        db=db,
        visit_id=visit_id,
        actor=current_user
    )
    return enrich_evc_visit(visit)
