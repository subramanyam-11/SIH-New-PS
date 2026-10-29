from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import get_current_user, get_user_scope, UserScope
from app.models import Institution, Region, User, UserRoleEnum
from app.schemas import InstitutionOut, RegionOut, UserScopeOut

router = APIRouter(prefix="", tags=["Lookups & Scope"])


# Screen mapping based on docs/03_roles_and_permissions.md
ROLE_SCREEN_PERMISSIONS = {
    UserRoleEnum.ADMIN: [
        "/dashboard", "/applications", "/alerts", "/escalation-matrix", "/notifications",
        "/admin/outbox", "/evc-queue", "/undertakings", "/document-validity", "/settings/rules", "/reports",
        "/bottlenecks", "/planner"
    ],
    UserRoleEnum.COMPETENT_AUTHORITY: [
        "/dashboard", "/applications", "/alerts", "/escalation-matrix", "/notifications",
        "/evc-queue", "/undertakings", "/document-validity", "/reports",
        "/bottlenecks", "/planner"
    ],
    UserRoleEnum.REGIONAL_HEAD: [
        "/dashboard", "/applications", "/alerts", "/escalation-matrix", "/notifications",
        "/evc-queue", "/undertakings", "/document-validity", "/reports",
        "/bottlenecks", "/planner"
    ],
    UserRoleEnum.SCRUTINY_OFFICER: [
        "/dashboard", "/applications", "/alerts", "/escalation-matrix", "/notifications",
        "/undertakings", "/document-validity"
    ],
    UserRoleEnum.EVC_COORDINATOR: [
        "/dashboard", "/applications", "/alerts", "/escalation-matrix", "/notifications",
        "/evc-queue", "/document-validity", "/planner"
    ],
    UserRoleEnum.BUREAU_OFFICER: [
        "/dashboard", "/applications", "/alerts", "/escalation-matrix", "/notifications", "/reports",
        "/bottlenecks", "/planner"
    ],
    UserRoleEnum.COMMITTEE_MEMBER: [
        "/committee/my-cases"
    ],
    UserRoleEnum.INSTITUTION_USER: [
        "/portal", "/portal/applications", "/portal/undertakings", "/portal/documents"
    ],
}


@router.get("/regions", response_model=List[RegionOut])
def list_regions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Region).order_by(Region.id).all()


@router.get("/institutions", response_model=List[InstitutionOut])
def list_institutions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    query = db.query(Institution)
    
    # Apply RBAC scoping
    if scope.is_institution:
        query = query.filter(Institution.id == scope.institution_id)
    elif scope.is_regional and scope.region_id:
        query = query.filter(Institution.region_id == scope.region_id)
    
    return query.order_by(Institution.id).all()


@router.get("/users/me/scope", response_model=UserScopeOut)
def get_my_scope(
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    user_role = current_user.role.code
    allowed_screens = ROLE_SCREEN_PERMISSIONS.get(user_role, ["/dashboard"])
    
    region_name = current_user.region.name if current_user.region else None
    institution_name = current_user.institution.name if current_user.institution else None

    return UserScopeOut(
        user_id=current_user.id,
        full_name=current_user.full_name,
        role=user_role.value,
        region_id=current_user.region_id,
        region_name=region_name,
        institution_id=current_user.institution_id,
        institution_name=institution_name,
        is_national=scope.is_national,
        is_regional=scope.is_regional,
        is_institution=scope.is_institution,
        allowed_screens=allowed_screens
    )
