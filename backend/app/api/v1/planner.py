"""
EVC What-If Capacity Planner API Endpoints for SIH26262 (Phase 7 Innovation Layer).
Provides counterfactual backlog, dwell time, and avoided alerts projections.
Strictly read-only: NEVER modifies any records.
Decision support only: All results are estimates labeled as decision support only.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_role, get_user_scope, UserScope
from app.models import User, UserRoleEnum
from app.schemas import WhatIfSimulateRequest
from app.services.whatif_service import WhatIfPlannerService

router = APIRouter(prefix="", tags=["What-If Capacity Planner"])


@router.post("/planner/simulate")
def simulate_evc_capacity_post(
    payload: WhatIfSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
):
    """
    Run EVC capacity simulation based on counterfactual throughput inputs.
    Visible to: EVC Coordinator, Regional Head, Bureau Officer, Competent Authority, and Admin.
    """
    allowed_roles = [
        UserRoleEnum.ADMIN,
        UserRoleEnum.COMPETENT_AUTHORITY,
        UserRoleEnum.BUREAU_OFFICER,
        UserRoleEnum.REGIONAL_HEAD,
        UserRoleEnum.EVC_COORDINATOR,
    ]
    if current_user.role.code not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="What-If planner access is restricted to EVC Coordinators, Regional Heads, Bureau Officers, Competent Authority, and Admin."
        )

    # Scoping
    target_region_id = payload.region_id
    if current_user.role.code in [UserRoleEnum.REGIONAL_HEAD, UserRoleEnum.EVC_COORDINATOR] and current_user.region_id:
        target_region_id = current_user.region_id

    result = WhatIfPlannerService.simulate_evc_capacity(
        db=db,
        region_id=target_region_id,
        extra_visits_per_week=payload.extra_visits_per_week,
        extra_staffing_capacity=payload.extra_staffing_capacity,
        horizon_weeks=payload.horizon_weeks,
    )
    return result


@router.get("/planner/simulate")
def simulate_evc_capacity_get(
    region_id: Optional[int] = None,
    extra_visits_per_week: int = Query(0, ge=0, le=10),
    extra_staffing_capacity: int = Query(0, ge=0, le=5),
    horizon_weeks: int = Query(4, ge=1, le=8),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
):
    """
    GET convenience endpoint for browser queries and fast UI slider interactions.
    """
    payload = WhatIfSimulateRequest(
        region_id=region_id,
        extra_visits_per_week=extra_visits_per_week,
        extra_staffing_capacity=extra_staffing_capacity,
        horizon_weeks=horizon_weeks,
    )
    return simulate_evc_capacity_post(payload=payload, db=db, current_user=current_user, scope=scope)
