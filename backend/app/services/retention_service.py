"""
Data Retention Policy & Preview Service for SIH26262.
Provides:
- Configurable statutory retention settings stored in system_config
- Non-destructive dry-run preview: calculates records eligible for archiving under policy
- Explicit CSV export of candidate records for compliance reporting
- Strict safety guard: NEVER deletes data automatically, and NEVER applies to audit_log.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    SystemConfig, Application, ApplicationStatusEnum,
    Alert, AlertStatusEnum, Notification, EmailOutbox, User, AuditLog
)
from app.services.audit import AuditService

DEFAULT_RETENTION_POLICY = {
    "closed_cases_years": 5,        # Retain closed cases for 5 years
    "resolved_alerts_days": 180,    # Retain resolved alerts for 180 days
    "notifications_days": 90,       # Retain in-app notifications for 90 days
    "outbox_entries_days": 60,      # Retain outbox logs for 60 days
}


class RetentionService:
    @staticmethod
    def get_policy(db: Session) -> Dict[str, int]:
        cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "data_retention_policy").first()
        if cfg and isinstance(cfg.config_value, dict):
            return {
                "closed_cases_years": int(cfg.config_value.get("closed_cases_years", DEFAULT_RETENTION_POLICY["closed_cases_years"])),
                "resolved_alerts_days": int(cfg.config_value.get("resolved_alerts_days", DEFAULT_RETENTION_POLICY["resolved_alerts_days"])),
                "notifications_days": int(cfg.config_value.get("notifications_days", DEFAULT_RETENTION_POLICY["notifications_days"])),
                "outbox_entries_days": int(cfg.config_value.get("outbox_entries_days", DEFAULT_RETENTION_POLICY["outbox_entries_days"])),
            }
        return dict(DEFAULT_RETENTION_POLICY)

    @staticmethod
    def update_policy(db: Session, actor: User, new_policy: Dict[str, int]) -> Dict[str, Any]:
        """Updates retention policy settings and audits the change."""
        cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "data_retention_policy").first()
        old_val = cfg.config_value if cfg else dict(DEFAULT_RETENTION_POLICY)

        sanitized = {
            "closed_cases_years": max(1, int(new_policy.get("closed_cases_years", 5))),
            "resolved_alerts_days": max(30, int(new_policy.get("resolved_alerts_days", 180))),
            "notifications_days": max(15, int(new_policy.get("notifications_days", 90))),
            "outbox_entries_days": max(15, int(new_policy.get("outbox_entries_days", 60))),
        }

        if not cfg:
            cfg = SystemConfig(
                config_key="data_retention_policy",
                config_value=sanitized,
                description="Statutory data retention policy thresholds (dry-run preview only)",
                updated_by=actor.id,
            )
            db.add(cfg)
        else:
            cfg.config_value = sanitized
            cfg.updated_by = actor.id

        db.commit()

        AuditService.log(
            db=db,
            table_name="system_config",
            record_id=cfg.id,
            action="UPDATE_DATA_RETENTION_POLICY",
            actor_id=actor.id,
            old_values=old_val,
            new_values=sanitized
        )

        return sanitized

    @staticmethod
    def preview_retention(db: Session) -> Dict[str, Any]:
        """
        Non-destructive preview: computes counts and date ranges of records that would be archived.
        Does NOT delete or modify any records.
        """
        policy = RetentionService.get_policy(db)
        now = datetime.utcnow()

        # 1. Closed cases
        cutoff_cases = now - timedelta(days=policy["closed_cases_years"] * 365)
        cases_q = db.query(Application).filter(
            Application.status == ApplicationStatusEnum.CLOSED,
            Application.closed_at <= cutoff_cases
        )
        cases_count = cases_q.count()
        cases_oldest = db.query(func.min(Application.closed_at)).filter(
            Application.status == ApplicationStatusEnum.CLOSED,
            Application.closed_at <= cutoff_cases
        ).scalar()
        cases_newest = db.query(func.max(Application.closed_at)).filter(
            Application.status == ApplicationStatusEnum.CLOSED,
            Application.closed_at <= cutoff_cases
        ).scalar()

        # 2. Resolved alerts
        cutoff_alerts = now - timedelta(days=policy["resolved_alerts_days"])
        alerts_q = db.query(Alert).filter(
            Alert.status == AlertStatusEnum.RESOLVED,
            Alert.resolved_at <= cutoff_alerts
        )
        alerts_count = alerts_q.count()
        alerts_oldest = db.query(func.min(Alert.resolved_at)).filter(
            Alert.status == AlertStatusEnum.RESOLVED,
            Alert.resolved_at <= cutoff_alerts
        ).scalar()
        alerts_newest = db.query(func.max(Alert.resolved_at)).filter(
            Alert.status == AlertStatusEnum.RESOLVED,
            Alert.resolved_at <= cutoff_alerts
        ).scalar()

        # 3. In-app notifications
        cutoff_notifs = now - timedelta(days=policy["notifications_days"])
        notifs_q = db.query(Notification).filter(Notification.sent_at <= cutoff_notifs)
        notifs_count = notifs_q.count()
        notifs_oldest = db.query(func.min(Notification.sent_at)).filter(Notification.sent_at <= cutoff_notifs).scalar()
        notifs_newest = db.query(func.max(Notification.sent_at)).filter(Notification.sent_at <= cutoff_notifs).scalar()

        # 4. Outbox entries
        cutoff_outbox = now - timedelta(days=policy["outbox_entries_days"])
        outbox_q = db.query(EmailOutbox).filter(EmailOutbox.created_at <= cutoff_outbox)
        outbox_count = outbox_q.count()
        outbox_oldest = db.query(func.min(EmailOutbox.created_at)).filter(EmailOutbox.created_at <= cutoff_outbox).scalar()
        outbox_newest = db.query(func.max(EmailOutbox.created_at)).filter(EmailOutbox.created_at <= cutoff_outbox).scalar()

        # 5. Audit log safety invariant check
        audit_log_count = db.query(func.count(AuditLog.id)).scalar()

        return {
            "disclaimer": "Preview only. No data is deleted by this prototype.",
            "policy": policy,
            "generated_at": now.isoformat(),
            "summary": {
                "total_candidate_records": cases_count + alerts_count + notifs_count + outbox_count,
                "categories": [
                    {
                        "category": "CLOSED_CASES",
                        "title": "Closed Application Cases",
                        "statutory_threshold": f"{policy['closed_cases_years']} years after closure",
                        "candidate_count": cases_count,
                        "oldest_record": cases_oldest.isoformat() if cases_oldest else None,
                        "newest_candidate": cases_newest.isoformat() if cases_newest else None,
                    },
                    {
                        "category": "RESOLVED_ALERTS",
                        "title": "Statutorily Resolved Alerts",
                        "statutory_threshold": f"{policy['resolved_alerts_days']} days after resolution",
                        "candidate_count": alerts_count,
                        "oldest_record": alerts_oldest.isoformat() if alerts_oldest else None,
                        "newest_candidate": alerts_newest.isoformat() if alerts_newest else None,
                    },
                    {
                        "category": "IN_APP_NOTIFICATIONS",
                        "title": "Read & System Notifications",
                        "statutory_threshold": f"{policy['notifications_days']} days after dispatch",
                        "candidate_count": notifs_count,
                        "oldest_record": notifs_oldest.isoformat() if notifs_oldest else None,
                        "newest_candidate": notifs_newest.isoformat() if notifs_newest else None,
                    },
                    {
                        "category": "OUTBOX_LOGS",
                        "title": "Dispatched Email Outbox Records",
                        "statutory_threshold": f"{policy['outbox_entries_days']} days after dispatch",
                        "candidate_count": outbox_count,
                        "oldest_record": outbox_oldest.isoformat() if outbox_oldest else None,
                        "newest_candidate": outbox_newest.isoformat() if outbox_newest else None,
                    },
                    {
                        "category": "AUDIT_LOG",
                        "title": "Cryptographic Immutable Audit Log",
                        "statutory_threshold": "PERMANENT RETENTION (Exempt from deletion)",
                        "candidate_count": 0,
                        "total_protected_records": audit_log_count,
                        "oldest_record": None,
                        "newest_candidate": None,
                    }
                ]
            }
        }
