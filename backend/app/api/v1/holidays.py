from typing import List, Optional, Any, Dict
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.rbac import get_current_user, UserScope, get_user_scope
from app.models import Holiday, Region, User, UserRoleEnum, SystemConfig
from app.schemas import HolidayCreate, HolidayUpdate, HolidayOut
from app.services.audit import log_audit_event
from app.services.working_day_service import WorkingDayService

router = APIRouter(prefix="/holidays", tags=["Holidays & Working-Day Calendar"])


@router.get("", response_model=List[HolidayOut])
def list_holidays(
    region_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List configured working-day holidays with optional regional or year filtering.
    """
    query = db.query(Holiday).options(joinedload(Holiday.region))

    if region_id is not None:
        query = query.filter((Holiday.region_id.is_(None)) | (Holiday.region_id == region_id))

    if year is not None:
        start_d = date(year, 1, 1)
        end_d = date(year, 12, 31)
        query = query.filter(Holiday.date >= start_d, Holiday.date <= end_d)

    holidays = query.order_by(Holiday.date.asc()).all()

    return [
        HolidayOut(
            id=h.id,
            date=h.date,
            name=h.name,
            region_id=h.region_id,
            region_name=h.region.name if h.region else "All Regions (National)",
            holiday_type=h.holiday_type,
            created_at=h.created_at
        ) for h in holidays
    ]


@router.post("", response_model=HolidayOut)
def create_holiday(
    payload: HolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Admin adds a holiday to the working-day calendar.
    Logs audit trail event.
    """
    if current_user.role.code != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can modify the AICTE working-day calendar."
        )

    # Check if holiday on this date already exists for same region
    existing = db.query(Holiday).filter(
        Holiday.date == payload.date,
        Holiday.region_id == payload.region_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A holiday '{existing.name}' is already defined for {payload.date} in this jurisdiction."
        )

    holiday = Holiday(
        date=payload.date,
        name=payload.name.strip(),
        region_id=payload.region_id,
        holiday_type=payload.holiday_type or "NATIONAL"
    )
    db.add(holiday)
    db.flush()

    log_audit_event(
        db=db,
        table_name="holidays",
        record_id=holiday.id,
        action="CREATE_HOLIDAY",
        actor_id=current_user.id,
        new_values={
            "date": payload.date.isoformat(),
            "name": payload.name,
            "region_id": payload.region_id,
            "type": payload.holiday_type
        }
    )

    db.commit()
    db.refresh(holiday)

    return HolidayOut(
        id=holiday.id,
        date=holiday.date,
        name=holiday.name,
        region_id=holiday.region_id,
        region_name=holiday.region.name if holiday.region else "All Regions (National)",
        holiday_type=holiday.holiday_type,
        created_at=holiday.created_at
    )


@router.put("/{id}", response_model=HolidayOut)
def update_holiday(
    id: int,
    payload: HolidayUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin updates an existing holiday record with audit logging."""
    if current_user.role.code != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins can modify holidays.")

    holiday = db.query(Holiday).filter(Holiday.id == id).first()
    if not holiday:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")

    old_vals = {
        "date": holiday.date.isoformat(),
        "name": holiday.name,
        "region_id": holiday.region_id,
        "type": holiday.holiday_type
    }

    if payload.date is not None:
        holiday.date = payload.date
    if payload.name is not None:
        holiday.name = payload.name.strip()
    if payload.region_id is not None:
        holiday.region_id = payload.region_id
    if payload.holiday_type is not None:
        holiday.holiday_type = payload.holiday_type

    log_audit_event(
        db=db,
        table_name="holidays",
        record_id=holiday.id,
        action="UPDATE_HOLIDAY",
        actor_id=current_user.id,
        old_values=old_vals,
        new_values={
            "date": holiday.date.isoformat(),
            "name": holiday.name,
            "region_id": holiday.region_id,
            "type": holiday.holiday_type
        }
    )

    db.commit()
    db.refresh(holiday)

    return HolidayOut(
        id=holiday.id,
        date=holiday.date,
        name=holiday.name,
        region_id=holiday.region_id,
        region_name=holiday.region.name if holiday.region else "All Regions (National)",
        holiday_type=holiday.holiday_type,
        created_at=holiday.created_at
    )


@router.delete("/{id}")
def delete_holiday(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin removes a holiday with audit logging."""
    if current_user.role.code != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins can delete holidays.")

    holiday = db.query(Holiday).filter(Holiday.id == id).first()
    if not holiday:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")

    log_audit_event(
        db=db,
        table_name="holidays",
        record_id=holiday.id,
        action="DELETE_HOLIDAY",
        actor_id=current_user.id,
        old_values={"date": holiday.date.isoformat(), "name": holiday.name}
    )

    db.delete(holiday)
    db.commit()

    return {"message": f"Holiday '{holiday.name}' on {holiday.date} deleted successfully."}


@router.get("/config/weekend", response_model=Dict[str, Any])
def get_weekend_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the configured weekend days (0=Mon...5=Sat, 6=Sun)."""
    weekends = WorkingDayService.get_weekend_days(db)
    names = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
    return {
        "weekend_days": sorted(list(weekends)),
        "weekend_names": [names[d] for d in sorted(list(weekends))]
    }
