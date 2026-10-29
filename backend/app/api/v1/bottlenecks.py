"""
Bottleneck Finder API Endpoints for SIH26262 (Phase 7 Innovation Layer).
Identifies stages, regions, and officer queues with the highest concentration of AICTE delay.
Decision support only: Automation assists officers; statutory scrutiny,
inspections, and final decisions stay with authorized humans.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import get_current_user, require_role, get_user_scope, UserScope
from app.models import User, UserRoleEnum
from app.services.bottleneck_service import BottleneckFinderService

router = APIRouter(prefix="", tags=["Bottleneck Finder"])


@router.get("/bottlenecks")
def get_bottleneck_analysis(
    region_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
):
    """
    Computes delay concentration across stages, regions, and officers.
    Role visibility: Bureau Officer, Regional Head (own region only), Competent Authority, and Admin.
    Reports AICTE-held working days only; WITH_INSTITUTION time reported separately.
    Flags groups with fewer than 3 cases as 'low sample'.
    """
    allowed_roles = [
        UserRoleEnum.ADMIN,
        UserRoleEnum.COMPETENT_AUTHORITY,
        UserRoleEnum.BUREAU_OFFICER,
        UserRoleEnum.REGIONAL_HEAD,
    ]
    if current_user.role.code not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bottleneck analysis is restricted to Bureau Officers, Regional Heads, Competent Authority, and Admin."
        )

    # Scoping: Regional Head can only see own region
    if current_user.role.code == UserRoleEnum.REGIONAL_HEAD:
        target_region_id = current_user.region_id
    else:
        target_region_id = region_id

    result = BottleneckFinderService.compute_bottlenecks(db, region_id=target_region_id)
    result["disclaimer"] = "Decision support only: Synthetic baseline data used for demonstration. Time WITH_INSTITUTION is tracked separately and excluded from AICTE officer delay metrics."
    return result
