from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.core.rbac import get_current_user, require_role
from app.models import User, Role, UserRoleEnum
from app.schemas import Token, LoginRequest, DemoLoginRequest, UserOut
from app.services.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])

_LOGIN_ATTEMPTS: Dict[str, List[datetime]] = {}
_LOGIN_LOCKOUTS: Dict[str, datetime] = {}


def validate_password_strength(password: str, email: str = ""):
    """Password policy for non-demo user accounts: minimum 8 chars, not identical to email."""
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )
    if email and password.lower().strip() == email.lower().strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be identical to email address."
        )


@router.post("/login", response_model=Token)
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    global _LOGIN_ATTEMPTS, _LOGIN_LOCKOUTS
    now = datetime.utcnow()
    email_key = login_data.email.lower().strip()
    client_ip = request.client.host if request.client else None

    # 1. Check if account is in temporary lockout
    locked_until = _LOGIN_LOCKOUTS.get(email_key)
    if locked_until and now < locked_until:
        remaining_secs = int((locked_until - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked due to repeated failed login attempts. Try again in {remaining_secs // 60 + 1} minutes."
        )

    user = db.query(User).filter(User.email == login_data.email).first()

    # 2. Check credentials
    if not user or not verify_password(login_data.password, user.password_hash):
        # Record failed attempt
        attempts = _LOGIN_ATTEMPTS.get(email_key, [])
        # Filter attempts within last 15 mins
        attempts = [t for t in attempts if (now - t).total_seconds() < (settings.LOGIN_LOCKOUT_MINUTES * 60)]
        attempts.append(now)
        _LOGIN_ATTEMPTS[email_key] = attempts

        # Audit failed login attempt
        log_audit_event(
            db=db,
            table_name="users",
            record_id=user.id if user else 0,
            action="LOGIN_FAILED",
            actor_id=user.id if user else None,
            new_values={"email": login_data.email, "attempt_count": len(attempts)},
            ip_address=client_ip
        )

        if len(attempts) >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            lock_duration = timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
            _LOGIN_LOCKOUTS[email_key] = now + lock_duration
            # Audit lockout
            log_audit_event(
                db=db,
                table_name="users",
                record_id=user.id if user else 0,
                action="ACCOUNT_LOCKED_TEMPORARY",
                actor_id=user.id if user else None,
                new_values={"email": login_data.email, "duration_minutes": settings.LOGIN_LOCKOUT_MINUTES},
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked: {settings.LOGIN_MAX_FAILED_ATTEMPTS} consecutive failed attempts. Locked for {settings.LOGIN_LOCKOUT_MINUTES} minutes."
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is disabled")

    # Clear failed attempts on successful authentication
    if email_key in _LOGIN_ATTEMPTS:
        del _LOGIN_ATTEMPTS[email_key]
    if email_key in _LOGIN_LOCKOUTS:
        del _LOGIN_LOCKOUTS[email_key]

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

    # Ensure demo chips are never blocked by prior failed manual attempts
    email_key = user.email.lower().strip()
    if email_key in _LOGIN_ATTEMPTS:
        del _LOGIN_ATTEMPTS[email_key]
    if email_key in _LOGIN_LOCKOUTS:
        del _LOGIN_LOCKOUTS[email_key]

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


@router.post("/unlock/{user_id}")
def unlock_user_account(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Admin action to manually unlock a locked user account.
    Clears failed attempt history and lockout timer. Audited.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    email_key = target_user.email.lower().strip()
    was_locked = email_key in _LOGIN_LOCKOUTS
    if email_key in _LOGIN_ATTEMPTS:
        del _LOGIN_ATTEMPTS[email_key]
    if email_key in _LOGIN_LOCKOUTS:
        del _LOGIN_LOCKOUTS[email_key]

    client_ip = request.client.host if request.client else None
    log_audit_event(
        db=db,
        table_name="users",
        record_id=target_user.id,
        action="ACCOUNT_UNLOCKED",
        actor_id=current_user.id,
        new_values={"unlocked_user_id": target_user.id, "email": target_user.email, "was_locked": was_locked},
        ip_address=client_ip
    )

    return {
        "status": "UNLOCKED",
        "user_id": target_user.id,
        "email": target_user.email,
        "message": f"Account for {target_user.email} successfully unlocked."
    }


@router.post("/unlock-demo-accounts")
def unlock_all_demo_accounts(request: Request):
    """
    Reset all lockout timers across all demo accounts.
    Available via API or make unlock-demo-accounts.
    """
    count = len(_LOGIN_LOCKOUTS)
    _LOGIN_ATTEMPTS.clear()
    _LOGIN_LOCKOUTS.clear()
    return {
        "status": "ALL_DEMO_ACCOUNTS_UNLOCKED",
        "lockouts_cleared": count,
        "message": "All account lockouts have been reset."
    }


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
