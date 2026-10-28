from datetime import date, datetime, timedelta, time
from typing import Optional, Set, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import Holiday, SystemConfig


class WorkingDayService:
    """
    Working Day Calendar Service for AICTE Approval Engine.
    Handles working days calculation, skipping configurable weekend days and national/regional holidays.
    Supports statutory expiry notes when due dates fall on weekends or holidays.
    """

    DEFAULT_WEEKEND_DAYS: Set[int] = {5, 6}  # Saturday (5), Sunday (6) in Python weekday()

    @classmethod
    def get_weekend_days(cls, db: Session) -> Set[int]:
        """Fetch weekend days from system_config or fallback to Saturday and Sunday."""
        try:
            cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "weekend_days").first()
            if cfg and isinstance(cfg.config_value, list):
                return set(cfg.config_value)
        except Exception:
            pass
        return set(cls.DEFAULT_WEEKEND_DAYS)

    @classmethod
    def get_holiday_dates(cls, db: Session, region_id: Optional[int] = None) -> dict[date, str]:
        """Fetch all relevant holidays as a dict of {date: holiday_name}."""
        query = db.query(Holiday)
        if region_id is not None:
            query = query.filter(or_(Holiday.region_id.is_(None), Holiday.region_id == region_id))
        else:
            query = query.filter(Holiday.region_id.is_(None))
        
        holidays = query.all()
        return {h.date: h.name for h in holidays}

    @classmethod
    def is_holiday_or_weekend(
        cls,
        db: Session,
        check_date: Union[date, datetime],
        region_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a given date is a holiday or a weekend day.
        Returns (is_non_working, reason).
        """
        d = check_date.date() if isinstance(check_date, datetime) else check_date
        weekends = cls.get_weekend_days(db)
        if d.weekday() in weekends:
            day_name = d.strftime("%A")
            return True, f"Weekend ({day_name})"

        holiday_map = cls.get_holiday_dates(db, region_id=region_id)
        if d in holiday_map:
            return True, f"Holiday: {holiday_map[d]}"

        return False, None

    @classmethod
    def is_working_day(
        cls,
        db: Session,
        check_date: Union[date, datetime],
        region_id: Optional[int] = None
    ) -> bool:
        """Returns True if check_date is a working day, False if weekend or holiday."""
        is_non_working, _ = cls.is_holiday_or_weekend(db, check_date, region_id)
        return not is_non_working

    @classmethod
    def add_working_days(
        cls,
        db: Session,
        start: Union[date, datetime],
        n_days: int,
        region_id: Optional[int] = None
    ) -> datetime:
        """
        Adds n_days working days to the start date/datetime.
        Skips weekends and holidays.
        Preserves the time component if start is datetime, otherwise defaults to 23:59:59.
        """
        is_dt = isinstance(start, datetime)
        cur_date = start.date() if is_dt else start
        base_time = start.time() if is_dt else time(23, 59, 59)

        if n_days <= 0:
            return datetime.combine(cur_date, base_time)

        added = 0
        while added < n_days:
            cur_date += timedelta(days=1)
            if cls.is_working_day(db, cur_date, region_id=region_id):
                added += 1

        return datetime.combine(cur_date, base_time)

    @classmethod
    def working_days_between(
        cls,
        db: Session,
        start: Union[date, datetime],
        end: Union[date, datetime],
        region_id: Optional[int] = None
    ) -> int:
        """
        Calculates number of working days between start and end (exclusive of start, inclusive of end if working day).
        If end < start, returns negative working days.
        """
        d_start = start.date() if isinstance(start, datetime) else start
        d_end = end.date() if isinstance(end, datetime) else end

        if d_start == d_end:
            return 0

        reverse = False
        if d_end < d_start:
            reverse = True
            d_start, d_end = d_end, d_start

        cur_date = d_start
        working_days = 0
        while cur_date < d_end:
            cur_date += timedelta(days=1)
            if cls.is_working_day(db, cur_date, region_id=region_id):
                working_days += 1

        return -working_days if reverse else working_days
