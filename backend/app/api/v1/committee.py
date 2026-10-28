from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.rbac import get_current_user, get_user_scope, UserScope
from app.models import (
    User, UserRoleEnum, Application, CommitteeAssignment, CommitteeObservation,
    CommitteeRecommendationEnum, CommitteeTypeEnum
)
from app.schemas import (
    CommitteeAssignmentOut, CommitteeObservationCreate, CommitteeObservationOut
)
from app.services.audit import log_audit_event
from app.services.clock import get_system_time

router = APIRouter(prefix="/committee", tags=["Committee Portal"])


@router.get("/my-cases", response_model=List[CommitteeAssignmentOut])
def get_my_committee_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Returns cases assigned to the authenticated COMMITTEE_MEMBER (EVC, SAC, or SHC).
    Shows the visit/meeting schedule and previous observations.
    """
    if current_user.role.code != UserRoleEnum.COMMITTEE_MEMBER and not scope.is_national:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only Committee Members can access their assigned committee cases."
        )

    query = db.query(CommitteeAssignment).options(
        joinedload(CommitteeAssignment.application).joinedload(Application.institution)
    )

    if current_user.role.code == UserRoleEnum.COMMITTEE_MEMBER:
        query = query.filter(CommitteeAssignment.user_id == current_user.id)

    assignments = query.order_by(CommitteeAssignment.assigned_at.desc()).all()

    results = []
    for a in assignments:
        obs = db.query(CommitteeObservation).filter(
            CommitteeObservation.application_id == a.application_id,
            CommitteeObservation.committee_type == a.committee_type
        ).order_by(CommitteeObservation.created_at.desc()).all()

        obs_out = [
            CommitteeObservationOut(
                id=o.id,
                application_id=o.application_id,
                committee_type=o.committee_type,
                user_id=o.user_id,
                member_name=o.member_name,
                observation_text=o.observation_text,
                recommendation=o.recommendation,
                created_at=o.created_at
            ) for o in obs
        ]

        results.append(
            CommitteeAssignmentOut(
                id=a.id,
                application_id=a.application_id,
                application_number=a.application.application_number if a.application else None,
                institution_name=a.application.institution.name if a.application and a.application.institution else None,
                committee_type=a.committee_type,
                user_id=a.user_id,
                assigned_at=a.assigned_at,
                status=a.status,
                notes=a.notes,
                observations=obs_out
            )
        )

    return results


@router.post("/cases/{application_id}/observations", response_model=CommitteeObservationOut)
def record_committee_observation(
    application_id: int,
    payload: CommitteeObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Committee member records observations and an expert recommendation.
    NOTE: A recommendation is decision support only; it NEVER moves, approves, or rejects a case.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # Verify assignment if role is COMMITTEE_MEMBER
    if current_user.role.code == UserRoleEnum.COMMITTEE_MEMBER:
        assignment = db.query(CommitteeAssignment).filter(
            CommitteeAssignment.application_id == application_id,
            CommitteeAssignment.user_id == current_user.id
        ).first()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not assigned to this case."
            )

    # Validate recommendation enum
    valid_recs = [r.value for r in CommitteeRecommendationEnum]
    if payload.recommendation not in valid_recs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid recommendation '{payload.recommendation}'. Allowed: {valid_recs}"
        )

    if not payload.observation_text or len(payload.observation_text.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Observation text must be at least 5 characters."
        )

    now = get_system_time()
    obs = CommitteeObservation(
        application_id=application_id,
        committee_type=payload.committee_type,
        user_id=current_user.id,
        member_name=current_user.full_name,
        observation_text=payload.observation_text.strip(),
        recommendation=payload.recommendation,
        created_at=now
    )
    db.add(obs)
    db.flush()

    # Log audit event
    log_audit_event(
        db=db,
        table_name="committee_observations",
        record_id=obs.id,
        action="RECORD_COMMITTEE_OBSERVATION",
        actor_id=current_user.id,
        new_values={
            "application_id": application_id,
            "committee_type": payload.committee_type,
            "recommendation": payload.recommendation,
            "member_name": current_user.full_name
        }
    )

    db.commit()
    db.refresh(obs)

    return CommitteeObservationOut(
        id=obs.id,
        application_id=obs.application_id,
        committee_type=obs.committee_type,
        user_id=obs.user_id,
        member_name=obs.member_name,
        observation_text=obs.observation_text,
        recommendation=obs.recommendation,
        created_at=obs.created_at
    )


@router.get("/cases/{application_id}/observations", response_model=List[CommitteeObservationOut])
def list_case_observations(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """List all recorded committee observations for an application."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if scope.is_institution and app.institution_id != scope.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    observations = db.query(CommitteeObservation).filter(
        CommitteeObservation.application_id == application_id
    ).order_by(CommitteeObservation.created_at.asc()).all()

    return [
        CommitteeObservationOut(
            id=o.id,
            application_id=o.application_id,
            committee_type=o.committee_type,
            user_id=o.user_id,
            member_name=o.member_name,
            observation_text=o.observation_text,
            recommendation=o.recommendation,
            created_at=o.created_at
        ) for o in observations
    ]
