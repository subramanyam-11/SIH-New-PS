import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models import AuditLog


AUDIT_ADVISORY_LOCK_ID = 987654321
_VIEW_CACHE: Dict[Tuple[int, str, int], datetime] = {}
VIEW_DEDUPE_WINDOW_SECONDS = 60


def compute_audit_hash(
    row_id: int,
    table_name: str,
    record_id: int,
    action: str,
    actor_id: Optional[int],
    created_at: datetime,
    prev_hash: str
) -> str:
    actor_str = str(actor_id) if actor_id is not None else "NONE"
    iso_dt = created_at.isoformat() if created_at else ""
    content = f"{row_id}:{table_name}:{record_id}:{action}:{actor_str}:{iso_dt}:{prev_hash}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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
    Creates an immutable audit log record with serialized cryptographic hash chaining.
    Uses PostgreSQL advisory locks to guarantee strict chain seriality under concurrency.
    """
    # Acquire session-level advisory lock
    db.execute(text(f"SELECT pg_advisory_xact_lock({AUDIT_ADVISORY_LOCK_ID})"))

    # Fetch latest entry to link hash chain
    last_entry = db.query(AuditLog.id, AuditLog.hash).order_by(AuditLog.id.desc()).first()
    prev_hash = last_entry.hash if (last_entry and last_entry.hash) else "GENESIS"

    # Pre-allocate ID from PostgreSQL sequence and fetch DB server timestamp so we can compute the hash before INSERT
    row_info = db.execute(text("SELECT nextval('public.audit_log_id_seq'), NOW()")).fetchone()
    row_id = row_info[0]
    now = row_info[1]

    # Deterministic SHA-256 hash computed before insertion
    row_hash = compute_audit_hash(
        row_id=row_id,
        table_name=table_name,
        record_id=record_id,
        action=action,
        actor_id=actor_id,
        created_at=now,
        prev_hash=prev_hash
    )

    audit_entry = AuditLog(
        id=row_id,
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
        actor_id=actor_id,
        ip_address=ip_address,
        prev_hash=prev_hash,
        hash=row_hash,
        created_at=now,
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

    @staticmethod
    def log_view(
        db: Session,
        entity_type: str,
        entity_id: int,
        action: str,
        actor_id: Optional[int],
        role: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLog]:
        """
        Logs access to sensitive records (file downloads, case briefs, approval letters, dossiers, audit export).
        Deduplicates repeated views by the same actor within a configurable window (60 seconds).
        """
        global _VIEW_CACHE
        now = datetime.utcnow()
        cache_key = (actor_id or 0, entity_type, entity_id)

        # Check in-memory cache to prevent spamming
        last_view_time = _VIEW_CACHE.get(cache_key)
        if last_view_time and (now - last_view_time).total_seconds() < VIEW_DEDUPE_WINDOW_SECONDS:
            return None

        _VIEW_CACHE[cache_key] = now

        meta = {"role": role, "viewed_entity": entity_type}
        if details:
            meta.update(details)

        return log_audit_event(
            db=db,
            table_name=entity_type.lower(),
            record_id=entity_id,
            action=action,
            actor_id=actor_id,
            new_values=meta,
            ip_address=ip_address
        )

    @staticmethod
    def verify_integrity(db: Session) -> Dict[str, Any]:
        """
        Walks the entire audit log hash chain from id 1 to N.
        Reports OK or details of the first broken row (tamper detected).
        """
        rows = db.query(
            AuditLog.id,
            AuditLog.table_name,
            AuditLog.record_id,
            AuditLog.action,
            AuditLog.actor_id,
            AuditLog.created_at,
            AuditLog.prev_hash,
            AuditLog.hash
        ).order_by(AuditLog.id.asc()).all()

        total = len(rows)
        if total == 0:
            return {"status": "OK", "total_records": 0, "verified": True, "message": "Audit log is empty"}

        expected_prev = "GENESIS"
        for r in rows:
            # 1. Check prev_hash linkage
            if r.prev_hash != expected_prev:
                return {
                    "status": "TAMPER_DETECTED",
                    "verified": False,
                    "broken_at_id": r.id,
                    "reason": f"Broken prev_hash link at record {r.id}: expected {expected_prev[:12]}..., got {r.prev_hash[:12] if r.prev_hash else 'NONE'}",
                    "total_records": total
                }

            # 2. Recompute expected hash
            computed = compute_audit_hash(
                row_id=r.id,
                table_name=r.table_name,
                record_id=r.record_id,
                action=r.action,
                actor_id=r.actor_id,
                created_at=r.created_at,
                prev_hash=expected_prev
            )

            if r.hash != computed:
                return {
                    "status": "TAMPER_DETECTED",
                    "verified": False,
                    "broken_at_id": r.id,
                    "reason": f"Hash mismatch at record {r.id}: expected {computed[:12]}..., found {r.hash[:12] if r.hash else 'NONE'}",
                    "total_records": total
                }

            expected_prev = computed

        return {
            "status": "OK",
            "verified": True,
            "total_records": total,
            "latest_hash": expected_prev,
            "message": f"All {total} audit records verified intact with valid cryptographic hash chain"
        }

