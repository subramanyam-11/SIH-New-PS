from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, Role, UserRoleEnum

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def require_roles(*allowed_roles: UserRoleEnum):
    """
    Dependency factory checking if current user's role is in allowed_roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.code if current_user.role else None
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}, but user has role: {user_role.value if user_role else 'None'}"
            )
        return current_user
    return role_checker


def require_role(roles):
    """
    Dependency factory accepting list of role codes or a single role string.
    """
    if isinstance(roles, str):
        roles = [roles]
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.code if current_user.role else ""
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {roles}, but user has role: {user_role}"
            )
        return current_user
    return role_checker


class UserScope:
    """Helper to inspect and apply data scoping to queries"""
    def __init__(self, user: User):
        self.user = user
        self.role_code = user.role.code if user.role else None
        self.region_id = user.region_id
        self.institution_id = user.institution_id

    @property
    def role(self):
        return self.role_code

    @property
    def is_national(self) -> bool:
        return self.role_code in [UserRoleEnum.ADMIN, UserRoleEnum.COMPETENT_AUTHORITY, UserRoleEnum.BUREAU_OFFICER]

    @property
    def is_bureau(self) -> bool:
        return self.role_code == UserRoleEnum.BUREAU_OFFICER

    @property
    def is_committee(self) -> bool:
        return self.role_code == UserRoleEnum.COMMITTEE_MEMBER

    @property
    def is_regional(self) -> bool:
        return self.role_code in [UserRoleEnum.REGIONAL_HEAD, UserRoleEnum.SCRUTINY_OFFICER, UserRoleEnum.EVC_COORDINATOR]

    @property
    def is_institution(self) -> bool:
        return self.role_code == UserRoleEnum.INSTITUTION_USER

    def can_access_institution(self, target_institution_id: int) -> bool:
        if self.is_national:
            return True
        if self.is_institution:
            return self.institution_id == target_institution_id
        return True  # Regional officers can see institutions within region (checked via DB)

    def can_modify_case(self) -> bool:
        """Bureau Officer and Committee Member have strictly read-focused or recommendation-only roles."""
        return self.role_code not in [UserRoleEnum.BUREAU_OFFICER, UserRoleEnum.COMMITTEE_MEMBER, UserRoleEnum.INSTITUTION_USER]

    def can_verify_compliance(self) -> bool:
        return self.role_code in [UserRoleEnum.SCRUTINY_OFFICER, UserRoleEnum.REGIONAL_HEAD, UserRoleEnum.ADMIN]

    def can_render_decision(self) -> bool:
        return self.role_code in [UserRoleEnum.COMPETENT_AUTHORITY, UserRoleEnum.ADMIN]

    def can_close_case(self) -> bool:
        return self.role_code in [UserRoleEnum.COMPETENT_AUTHORITY, UserRoleEnum.REGIONAL_HEAD, UserRoleEnum.ADMIN]


def get_user_scope(current_user: User = Depends(get_current_user)) -> UserScope:
    return UserScope(current_user)
