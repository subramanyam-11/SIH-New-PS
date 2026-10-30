"""
Audit Log Management and Verification Endpoints for SIH26262.
Provides:
- Searchable audit log querying with RBAC scoping and multi-attribute filters
- CSV export endpoint (audited access)
- Cryptographic hash chain integrity verification endpoint
"""
import io
import csv
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.rbac import get_current_user, require_role, UserScope, get_user_scope
from app.models import AuditLog, User, UserRoleEnum, Role
from app.services.audit import AuditService

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("/verify-integrity")
def verify_audit_integrity(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN, UserRoleEnum.COMPETENT_AUTHORITY])),
):
    """
    Walks the full cryptographic SHA-256 hash chain on audit_log.
    Returns verification status, total count, latest chain hash, or broken row details.
    Restricted to System Admin and Competent Authority.
    """
    report = AuditService.verify_integrity(db)
    return report


@router.get("")
def list_audit_logs(
    actor_id: Optional[int] = Query(None, description="Filter by actor ID"),
    role: Optional[str] = Query(None, description="Filter by user role code"),
    action: Optional[str] = Query(None, description="Filter by action keyword"),
    table_name: Optional[str] = Query(None, description="Filter by entity / table name"),
    record_id: Optional[int] = Query(None, description="Filter by record ID"),
    date_from: Optional[date] = Query(None, description="Filter records created on or after date"),
    date_to: Optional[date] = Query(None, description="Filter records created on or before date"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
):
    """
    Searchable audit trail.
    - System Admin and Competent Authority can query full history.
    - Regional Heads see audit logs for actions in their region.
    - Institution Users can only see their own institution's audit logs.
    """
    query = db.query(AuditLog)

    # Scoping
    if scope.role == UserRoleEnum.INSTITUTION_USER:
        query = query.filter(AuditLog.actor_id == current_user.id)
    elif scope.role == UserRoleEnum.REGIONAL_HEAD and scope.region_id:
        # Regional head sees own actions or users in region
        reg_user_ids = [u.id for u in db.query(User.id).filter(User.region_id == scope.region_id).all()]
        query = query.filter(AuditLog.actor_id.in_(reg_user_ids))

    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if role:
        role_user_ids = [u.id for u in db.query(User.id).join(Role).filter(Role.code == role).all()]
        query = query.filter(AuditLog.actor_id.in_(role_user_ids))
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if table_name:
        query = query.filter(AuditLog.table_name == table_name.lower())
    if record_id:
        query = query.filter(AuditLog.record_id == record_id)
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))

    total = query.count()
    rows = query.order_by(desc(AuditLog.id)).offset(offset).limit(limit).all()

    # Pre-fetch actor full names and roles
    actor_ids = list({r.actor_id for r in rows if r.actor_id})
    user_map = {}
    if actor_ids:
        users = db.query(User).filter(User.id.in_(actor_ids)).all()
        for u in users:
            user_map[u.id] = {
                "name": u.full_name,
                "role": u.role.code.value if u.role else "UNKNOWN",
                "email": u.email
            }

    items = []
    for r in rows:
        actor_info = user_map.get(r.actor_id, {"name": "System Engine", "role": "SYSTEM", "email": None})
        items.append({
            "id": r.id,
            "table_name": r.table_name,
            "record_id": r.record_id,
            "action": r.action,
            "actor_id": r.actor_id,
            "actor_name": actor_info["name"],
            "actor_role": actor_info["role"],
            "actor_email": actor_info["email"],
            "ip_address": r.ip_address,
            "prev_hash": r.prev_hash,
            "hash": r.hash,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "old_values": r.old_values,
            "new_values": r.new_values,
        })

    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/export-csv")
def export_audit_csv(
    request: Request,
    actor_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    record_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN, UserRoleEnum.COMPETENT_AUTHORITY])),
):
    """
    Exports filtered audit log as CSV with tamper-evident chain hashes.
    Audit log view/export is itself strictly recorded in the audit trail.
    """
    # Log sensitive view of audit export
    client_ip = request.client.host if request.client else None
    AuditService.log_view(
        db=db,
        entity_type="AUDIT_EXPORT",
        entity_id=0,
        action="EXPORT_AUDIT_LOG_CSV",
        actor_id=current_user.id,
        role=current_user.role.code.value if current_user.role else None,
        ip_address=client_ip,
        details={"filters": {"action": action, "table_name": table_name}}
    )

    query = db.query(AuditLog)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if role:
        role_user_ids = [u.id for u in db.query(User.id).join(Role).filter(Role.code == role).all()]
        query = query.filter(AuditLog.actor_id.in_(role_user_ids))
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if table_name:
        query = query.filter(AuditLog.table_name == table_name.lower())
    if record_id:
        query = query.filter(AuditLog.record_id == record_id)
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))

    rows = query.order_by(AuditLog.id.asc()).limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Record ID",
        "Timestamp (UTC)",
        "Table/Entity",
        "Entity Record ID",
        "Action",
        "Actor ID",
        "IP Address",
        "Cryptographic Hash (SHA-256)",
        "Previous Hash (SHA-256)",
    ])

    for r in rows:
        writer.writerow([
            r.id,
            r.created_at.isoformat() if r.created_at else "",
            r.table_name,
            r.record_id,
            r.action,
            r.actor_id or "SYSTEM",
            r.ip_address or "-",
            r.hash or "",
            r.prev_hash or "",
        ])

    output.seek(0)
    filename = f"aicte_audit_trail_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
