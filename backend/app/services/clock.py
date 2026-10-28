from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# Global in-memory clock offset in seconds (for presentation time travel & tests)
_CLOCK_OFFSET_SECONDS: float = 0.0
_FIXED_TEST_TIME: Optional[datetime] = None


def normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures consistent offset-naive UTC datetime for arithmetic."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def get_system_time() -> datetime:
    """
    Returns the current simulated system time.
    Supports time travel in demo mode and deterministic freezing in unit tests.
    """
    if _FIXED_TEST_TIME is not None:
        return normalize_dt(_FIXED_TEST_TIME)
    return normalize_dt(datetime.utcnow() + timedelta(seconds=_CLOCK_OFFSET_SECONDS))


def advance_clock(hours: float) -> datetime:
    """Advances simulated system time by given hours."""
    global _CLOCK_OFFSET_SECONDS
    _CLOCK_OFFSET_SECONDS += (hours * 3600.0)
    return get_system_time()


def reset_clock() -> datetime:
    """Resets simulated system time to actual real-time UTC."""
    global _CLOCK_OFFSET_SECONDS, _FIXED_TEST_TIME
    _CLOCK_OFFSET_SECONDS = 0.0
    _FIXED_TEST_TIME = None
    return get_system_time()


def set_test_time(dt: Optional[datetime]) -> None:
    """Sets a fixed datetime for testing purposes."""
    global _FIXED_TEST_TIME
    _FIXED_TEST_TIME = normalize_dt(dt)


def compute_stage_due_date(stage_entered_at: datetime, default_sla_days: int) -> datetime:
    """Calculates statutory deadline given entry timestamp and SLA days."""
    return normalize_dt(stage_entered_at) + timedelta(days=default_sla_days)


def calculate_sla_status(
    stage_entered_at: datetime,
    stage_due_date: datetime,
    default_sla_days: int,
    thresholds: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Computes real-time days in stage, days remaining, percentage elapsed,
    and the regulatory ageing bucket (ON_TIME, NEAR_DUE, OVERDUE).
    """
    now = normalize_dt(get_system_time())
    t_entered = normalize_dt(stage_entered_at)
    t_due = normalize_dt(stage_due_date)
    
    # Dwell time
    elapsed_seconds = (now - t_entered).total_seconds()
    days_in_stage = max(0.0, round(elapsed_seconds / 86400.0, 1))

    # Remaining time
    remaining_seconds = (t_due - now).total_seconds()
    days_remaining = round(remaining_seconds / 86400.0, 1)

    # Percentage elapsed of SLA
    total_sla_seconds = max(1.0, (t_due - t_entered).total_seconds())
    percentage_elapsed = min(999.0, round((elapsed_seconds / total_sla_seconds) * 100.0, 1))

    # Thresholds from config (default: near breach at 80% SLA or <= 2 days remaining)
    near_breach_percent = 80.0
    near_breach_min_days = 2.0
    if thresholds:
        near_breach_percent = float(thresholds.get("near_breach_percent", 80.0))
        near_breach_min_days = float(thresholds.get("near_breach_min_days", 2.0))

    if days_remaining < 0:
        ageing_bucket = "OVERDUE"
    elif percentage_elapsed >= near_breach_percent or days_remaining <= near_breach_min_days:
        ageing_bucket = "NEAR_DUE"
    else:
        ageing_bucket = "ON_TIME"

    return {
        "days_in_stage": days_in_stage,
        "days_remaining": days_remaining,
        "percentage_elapsed": percentage_elapsed,
        "ageing_bucket": ageing_bucket,
        "evaluated_at": now.isoformat()
    }
