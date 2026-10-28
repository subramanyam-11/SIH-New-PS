from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.core.rbac import get_current_user
from app.models import User, Role, UserRoleEnum
from app.schemas import Token, LoginRequest, DemoLoginRequest, UserOut
from app.services.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is disabled")

    user.last_login = datetime.utcnow()
    db.commit()

    token_str = create_access_token(
        subject=user.id,
        extra_claims={
            "role": user.role.code.value,
            "email": user.email,
            "region_id": user.region_id,
            "institution_id": user.institution_id
        }
    )

    # Log to audit_log
    client_ip = request.client.host if request.client else None
    log_audit_event(
        db=db,
        table_name="users",
        record_id=user.id,
        action="LOGIN_PASSWORD",
        actor_id=user.id,
        new_values={"email": user.email, "role": user.role.code.value},
        ip_address=client_ip
    )

    return Token(
        access_token=token_str,
        token_type="bearer",
        role=user.role.code.value,
        user_id=user.id,
        full_name=user.full_name,
        region_id=user.region_id,
        institution_id=user.institution_id
    )


@router.post("/demo-login", response_model=Token)
def demo_login(request: Request, demo_data: DemoLoginRequest, db: Session = Depends(get_db)):
    """
    Demo login endpoint: fast-switches to any demo persona without entering credentials.
    Allowed ONLY when DEMO_MODE=True.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is disabled in production mode."
        )

    # Find the target user by role or specific email
    query = db.query(User).join(Role).filter(Role.code == demo_data.role, User.is_active == True)
    if demo_data.email:
        query = query.filter(User.email == demo_data.email)
    
    user = query.first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No seed demo user found for role: {demo_data.role.value}"
        )

    user.last_login = datetime.utcnow()
    db.commit()

    token_str = create_access_token(
        subject=user.id,
        extra_claims={
            "role": user.role.code.value,
            "email": user.email,
            "region_id": user.region_id,
            "institution_id": user.institution_id,
            "is_demo": True
        }
    )

    client_ip = request.client.host if request.client else None
    log_audit_event(
        db=db,
        table_name="users",
        record_id=user.id,
        action="DEMO_LOGIN",
        actor_id=user.id,
        new_values={"email": user.email, "role": user.role.code.value},
        ip_address=client_ip
    )

    return Token(
        access_token=token_str,
        token_type="bearer",
        role=user.role.code.value,
        user_id=user.id,
        full_name=user.full_name,
        region_id=user.region_id,
        institution_id=user.institution_id
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else None
    log_audit_event(
        db=db,
        table_name="users",
        record_id=current_user.id,
        action="LOGOUT",
        actor_id=current_user.id,
        ip_address=client_ip
    )
    return {"status": "success", "message": "Logged out successfully"}
