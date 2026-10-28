from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import AuditLog


def log_audit_event(
    db: Session,
    table_name: str,
    record_id: int,
    action: str,
    actor_id: Optional[int] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """
    Creates an immutable audit log record for write actions, logins, logouts, etc.
    """
    audit_entry = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
        actor_id=actor_id,
        ip_address=ip_address
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry


class AuditService:
    @staticmethod
    def log(
        db: Session,
        table_name: str,
        record_id: int,
        action: str,
        actor_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        return log_audit_event(
            db=db,
            table_name=table_name,
            record_id=record_id,
            action=action,
            actor_id=actor_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
        )

