"""
Scheduler Service for SIH26262.
Runs background periodic evaluation of alert rules and escalation ladders using APScheduler.
Ensures thread-safe, non-overlapping, idempotent job execution with full audit logging in scheduler_runs.
"""
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import SchedulerRun
from app.services.alert_engine import AlertEngine
from app.services.escalation_service import EscalationService
from app.services.email_service import EmailService
from app.services.clock import ClockService

# Global thread lock to prevent overlapping runs
_evaluation_lock = threading.Lock()
_scheduler: Optional[BackgroundScheduler] = None


def run_checks_now(triggered_by: str = "MANUAL") -> Dict[str, Any]:
    """
    Executes an evaluation cycle synchronously.
    Thread-safe and logged in database table scheduler_runs.
    """
    if not _evaluation_lock.acquire(blocking=False):
        return {
            "status": "SKIPPED",
            "message": "Another evaluation cycle is currently in progress. Please wait a moment.",
            "rules_evaluated": 0,
            "alerts_created": 0,
            "alerts_upgraded": 0,
            "alerts_resolved": 0,
        }

    start_time = time.time()
    now_started = ClockService.get_now()
    db: Session = SessionLocal()

    try:
        # 1. Evaluate Alert Rules
        rule_res = AlertEngine.evaluate_all_rules(db=db, triggered_by=triggered_by)

        # 2. Evaluate Escalation Ladder
        escalated_count = EscalationService.evaluate_escalations(db=db)

        # 3. Process Outbox
        outbox_res = EmailService.process_outbox(db=db)

        duration_ms = int((time.time() - start_time) * 1000)
        now_finished = ClockService.get_now()

        # Log into scheduler_runs table
        run_log = SchedulerRun(
            started_at=now_started,
            finished_at=now_finished,
            duration_ms=duration_ms,
            rules_evaluated=rule_res.get("rules_evaluated", 0),
            alerts_created=rule_res.get("alerts_created", 0),
            alerts_upgraded=rule_res.get("alerts_upgraded", 0),
            alerts_resolved=rule_res.get("alerts_resolved", 0),
            status="SUCCESS",
            triggered_by=triggered_by,
            details={
                "escalated_count": escalated_count,
                "outbox": outbox_res,
                "evaluated_at": rule_res.get("evaluated_at"),
            }
        )
        db.add(run_log)
        db.commit()

        return {
            "status": "SUCCESS",
            "duration_ms": duration_ms,
            "rules_evaluated": rule_res.get("rules_evaluated", 0),
            "alerts_created": rule_res.get("alerts_created", 0),
            "alerts_upgraded": rule_res.get("alerts_upgraded", 0),
            "alerts_resolved": rule_res.get("alerts_resolved", 0),
            "alerts_escalated": escalated_count,
            "outbox_processed": outbox_res,
            "started_at": now_started.isoformat(),
            "finished_at": now_finished.isoformat(),
        }

    except Exception as ex:
        db.rollback()
        duration_ms = int((time.time() - start_time) * 1000)
        now_finished = ClockService.get_now()

        run_log = SchedulerRun(
            started_at=now_started,
            finished_at=now_finished,
            duration_ms=duration_ms,
            rules_evaluated=0,
            alerts_created=0,
            alerts_upgraded=0,
            alerts_resolved=0,
            status="FAILED",
            triggered_by=triggered_by,
            details={"error": str(ex)}
        )
        db.add(run_log)
        db.commit()

        return {
            "status": "FAILED",
            "error": str(ex),
            "duration_ms": duration_ms,
        }

    finally:
        db.close()
        _evaluation_lock.release()


def _scheduled_job():
    run_checks_now(triggered_by="SCHEDULER")


def start_scheduler():
    """
    Initializes and starts the background scheduler on server startup.
    """
    global _scheduler
    if not settings.SCHEDULER_ENABLED:
        print("[Scheduler] Background scheduler disabled by configuration.")
        return

    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
        interval_minutes = settings.SCHEDULER_INTERVAL_MINUTES
        _scheduler.add_job(
            _scheduled_job,
            "interval",
            minutes=interval_minutes,
            id="alert_rules_evaluator",
            replace_existing=True,
        )
        _scheduler.start()
        print(f"[Scheduler] Background scheduler active (interval: every {interval_minutes}m).")


def stop_scheduler():
    """
    Gracefully shuts down the background scheduler.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("[Scheduler] Background scheduler stopped.")
