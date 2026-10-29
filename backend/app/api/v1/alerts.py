"""
Alert, Escalation, Notification, and Outbox API Endpoints for SIH26262.
Follows role-based and regional scoping rules.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.core.rbac import get_current_user, require_role, get_user_scope
from app.models import (
    User, UserRoleEnum, Alert, AlertRule, AlertStatusEnum, AlertSeverityEnum,
    EscalationRule, EscalationHistory, Notification, NotificationChannelEnum,
    EmailOutbox, Region, Application, Institution, Document, Undertaking,
    SystemConfig
)
from app.schemas import (
    AlertOut, AlertDetailOut, AlertAcknowledgeRequest, AlertSnoozeRequest,
    AlertResolveRequest, AlertSummaryOut, NotificationOut, NotificationSummaryOut,
    EmailOutboxOut, EscalationRuleOut, EscalationRuleUpdate, AlertRuleOut,
    AlertRuleUpdate, EscalationMatrixOut, RegionEscalationItem, SchedulerRunOut,
    NeedsAttentionAlertOut
)
from app.services.alert_engine import AlertEngine
from app.services.escalation_service import EscalationService
from app.services.scheduler import run_checks_now
from app.services.clock import ClockService, normalize_dt
from app.services.audit import AuditService

router = APIRouter(tags=["Alerts & Notifications"])


# -----------------------------------------------------------------------------
# 1. ALERTS LIST & SUMMARY
# -----------------------------------------------------------------------------

@router.get("/alerts", response_model=List[AlertOut])
def list_alerts(
    severity: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    rule_code: Optional[str] = None,
    region_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    escalation_tier: Optional[int] = None,
    sort_by: str = Query("priority", pattern="^(priority|created_at|severity|escalation_tier)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List alerts filtered by criteria and strictly scoped by user role & regional jurisdiction.
    Defaults to explainable priority sorting.
    """
    query = db.query(Alert)

    # Scoping
    role_code = current_user.role.code if current_user.role else ""
    if role_code == "INSTITUTION_USER":
        query = query.filter(Alert.institution_id == current_user.institution_id)
    elif role_code in ["SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_HEAD"] and current_user.region_id:
        # Filter alerts belonging to institutions/applications in this officer's region
        query = query.outerjoin(Application, Alert.application_id == Application.id)\
                     .outerjoin(Institution, Alert.institution_id == Institution.id)\
                     .filter(
                         (Application.region_id == current_user.region_id) |
                         (Institution.region_id == current_user.region_id) |
                         (Alert.recipient_user_id == current_user.id)
                     )

    # Filters
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if status_filter:
        query = query.filter(Alert.status == status_filter.upper())
    if rule_code:
        query = query.join(AlertRule).filter(AlertRule.code == rule_code)
    if region_id:
        query = query.outerjoin(Application, Alert.application_id == Application.id)\
                     .outerjoin(Institution, Alert.institution_id == Institution.id)\
                     .filter((Application.region_id == region_id) | (Institution.region_id == region_id))
    if institution_id:
        query = query.filter(Alert.institution_id == institution_id)
    if escalation_tier:
        query = query.filter(Alert.escalation_tier == escalation_tier)

    # Sorting
    if sort_by == "priority":
        from app.models import AlertPriorityScore
        query = query.outerjoin(AlertPriorityScore, Alert.id == AlertPriorityScore.alert_id)
        if sort_order == "desc":
            query = query.order_by(
                desc(AlertPriorityScore.priority_score.isnot(None)),
                desc(AlertPriorityScore.priority_score),
                desc(Alert.created_at)
            )
        else:
            query = query.order_by(
                asc(AlertPriorityScore.priority_score),
                asc(Alert.created_at)
            )
    else:
        sort_col = getattr(Alert, sort_by, Alert.created_at)
        order_func = desc if sort_order == "desc" else asc
        query = query.order_by(order_func(sort_col))

    alerts = query.offset(offset).limit(limit).all()

    # Hydrate AlertOut schemas
    now = ClockService.get_now()
    output = []
    for a in alerts:
        age_hours = round(max(0.0, (now - normalize_dt(a.created_at)).total_seconds() / 3600.0), 1)
        p_score = a.priority_score.priority_score if a.priority_score else 0.0
        p_expl = a.priority_score.explanation if a.priority_score else None
        output.append(AlertOut(
            id=a.id,
            alert_rule_id=a.alert_rule_id,
            rule_code=a.rule.code if a.rule else "",
            rule_name=a.rule.name if a.rule else "",
            alert_type=a.alert_type.value,
            severity=a.severity.value,
            status=a.status.value,
            application_id=a.application_id,
            application_number=a.application.application_number if a.application else None,
            institution_id=a.institution_id,
            institution_name=a.institution.name if a.institution else None,
            document_id=a.document_id,
            undertaking_id=a.undertaking_id,
            recipient_user_id=a.recipient_user_id,
            recipient_user_name=a.recipient_user.full_name if a.recipient_user else None,
            recipient_role=a.recipient_role.value if a.recipient_role else "",
            title=a.title,
            message=a.message,
            explanation_meta=a.explanation_meta or {},
            escalation_tier=a.escalation_tier or 1,
            escalated_at=a.escalated_at,
            resolved_at=a.resolved_at,
            snoozed_until=a.snoozed_until,
            snooze_count=a.snooze_count or 0,
            snooze_reason=a.snooze_reason,
            acknowledged_at=a.acknowledged_at,
            acknowledged_by=a.acknowledged_by,
            acknowledged_by_name=a.acknowledged_user.full_name if a.acknowledged_user else None,
            acknowledgement_remarks=a.acknowledgement_remarks,
            resolved_by=a.resolved_by,
            resolved_by_name=a.resolved_user.full_name if a.resolved_user else None,
            resolution_remarks=a.resolution_remarks,
            created_at=a.created_at,
            age_hours=age_hours,
            priority_score=p_score,
            priority_explanation=p_expl,
        ))

    return output


@router.get("/alerts/needs-attention-today", response_model=List[NeedsAttentionAlertOut])
def get_needs_attention_today(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns top N highest-priority actionable open alerts for the current officer/role.
    Powers the 'Needs attention today' dashboard card.
    """
    from app.services.alert_ranking_service import AlertRankingService
    return AlertRankingService.get_needs_attention_today(db=db, user=current_user, limit=limit)


@router.post("/alerts/daily-digest/generate")
def generate_daily_digests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN])),
):
    """
    Triggers generation of consolidated daily digest drafts in the email outbox.
    """
    from app.services.alert_ranking_service import AlertRankingService
    count = AlertRankingService.generate_officer_daily_digests(db)
    return {"status": "SUCCESS", "digests_created": count}


@router.get("/alerts/summary", response_model=AlertSummaryOut)
def get_alerts_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns counts of open alerts broken down by severity, status, tier level, and region.
    """
    query = db.query(Alert).filter(
        Alert.status.in_([
            AlertStatusEnum.ACTIVE,
            AlertStatusEnum.ACKNOWLEDGED,
            AlertStatusEnum.SNOOZED,
            AlertStatusEnum.ESCALATED,
        ])
    )

    role_code = current_user.role.code if current_user.role else ""
    if role_code == "INSTITUTION_USER":
        query = query.filter(Alert.institution_id == current_user.institution_id)
    elif role_code in ["SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_HEAD"] and current_user.region_id:
        query = query.outerjoin(Application, Alert.application_id == Application.id)\
                     .outerjoin(Institution, Alert.institution_id == Institution.id)\
                     .filter(
                         (Application.region_id == current_user.region_id) |
                         (Institution.region_id == current_user.region_id) |
                         (Alert.recipient_user_id == current_user.id)
                     )

    open_alerts = query.all()

    by_severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    by_status = {"ACTIVE": 0, "ACKNOWLEDGED": 0, "SNOOZED": 0, "ESCALATED": 0}
    by_level = {"L1": 0, "L2": 0, "L3": 0}
    by_region: Dict[str, int] = {}

    for a in open_alerts:
        by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
        by_status[a.status.value] = by_status.get(a.status.value, 0) + 1
        tier_key = f"L{a.escalation_tier or 1}"
        by_level[tier_key] = by_level.get(tier_key, 0) + 1

        reg_name = "National / General"
        if a.application and a.application.region:
            reg_name = a.application.region.name
        elif a.institution and a.institution.region:
            reg_name = a.institution.region.name
        by_region[reg_name] = by_region.get(reg_name, 0) + 1

    return AlertSummaryOut(
        total_open=len(open_alerts),
        by_severity=by_severity,
        by_status=by_status,
        by_level=by_level,
        by_region=by_region,
    )


# -----------------------------------------------------------------------------
# 2. ALERT DETAIL & ACTIONS
# -----------------------------------------------------------------------------

@router.get("/alerts/{id}", response_model=AlertDetailOut)
def get_alert_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Detailed dossier for a specific alert, including explanation breakdown,
    escalation history trail, and rule configuration.
    """
    alert = db.query(Alert).filter(Alert.id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Scope check
    role_code = current_user.role.code if current_user.role else ""
    if role_code == "INSTITUTION_USER" and alert.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Access denied to alert outside institution scope")
    elif role_code in ["SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_HEAD"] and current_user.region_id:
        alert_region = None
        if alert.application:
            alert_region = alert.application.region_id
        elif alert.institution:
            alert_region = alert.institution.region_id
        if alert_region and alert_region != current_user.region_id and alert.recipient_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to alert outside your regional office")

    now = ClockService.get_now()
    age_hours = round(max(0.0, (now - normalize_dt(alert.created_at)).total_seconds() / 3600.0), 1)

    # Escalation history
    history_items = []
    for h in alert.escalation_history:
        history_items.append({
            "id": h.id,
            "alert_id": h.alert_id,
            "from_tier": h.from_tier,
            "to_tier": h.to_tier,
            "target_role": h.target_role,
            "recipient_user_id": h.recipient_user_id,
            "recipient_name": h.recipient_user.full_name if h.recipient_user else None,
            "reason": h.reason,
            "escalated_by": h.escalated_by,
            "escalated_by_name": h.escalated_by_user.full_name if h.escalated_by_user else None,
            "created_at": h.created_at,
        })

    return AlertDetailOut(
        id=alert.id,
        alert_rule_id=alert.alert_rule_id,
        rule_code=alert.rule.code if alert.rule else "",
        rule_name=alert.rule.name if alert.rule else "",
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        status=alert.status.value,
        application_id=alert.application_id,
        application_number=alert.application.application_number if alert.application else None,
        institution_id=alert.institution_id,
        institution_name=alert.institution.name if alert.institution else None,
        document_id=alert.document_id,
        undertaking_id=alert.undertaking_id,
        recipient_user_id=alert.recipient_user_id,
        recipient_user_name=alert.recipient_user.full_name if alert.recipient_user else None,
        recipient_role=alert.recipient_role.value if alert.recipient_role else "",
        title=alert.title,
        message=alert.message,
        explanation_meta=alert.explanation_meta or {},
        escalation_tier=alert.escalation_tier or 1,
        escalated_at=alert.escalated_at,
        resolved_at=alert.resolved_at,
        snoozed_until=alert.snoozed_until,
        snooze_count=alert.snooze_count or 0,
        snooze_reason=alert.snooze_reason,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_by_name=alert.acknowledged_user.full_name if alert.acknowledged_user else None,
        acknowledgement_remarks=alert.acknowledgement_remarks,
        resolved_by=alert.resolved_by,
        resolved_by_name=alert.resolved_user.full_name if alert.resolved_user else None,
        resolution_remarks=alert.resolution_remarks,
        created_at=alert.created_at,
        age_hours=age_hours,
        escalation_history=history_items,
        rule=alert.rule,
    )


@router.post("/alerts/{id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(
    id: int,
    payload: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Officer acknowledges an active alert.
    """
    alert = EscalationService.acknowledge_alert(
        db=db,
        alert_id=id,
        user=current_user,
        remarks=payload.remarks,
    )
    now = ClockService.get_now()
    age_hours = round(max(0.0, (now - normalize_dt(alert.created_at)).total_seconds() / 3600.0), 1)

    return AlertOut(
        id=alert.id,
        alert_rule_id=alert.alert_rule_id,
        rule_code=alert.rule.code if alert.rule else "",
        rule_name=alert.rule.name if alert.rule else "",
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        status=alert.status.value,
        application_id=alert.application_id,
        application_number=alert.application.application_number if alert.application else None,
        institution_id=alert.institution_id,
        institution_name=alert.institution.name if alert.institution else None,
        document_id=alert.document_id,
        undertaking_id=alert.undertaking_id,
        recipient_user_id=alert.recipient_user_id,
        recipient_user_name=alert.recipient_user.full_name if alert.recipient_user else None,
        recipient_role=alert.recipient_role.value if alert.recipient_role else "",
        title=alert.title,
        message=alert.message,
        explanation_meta=alert.explanation_meta or {},
        escalation_tier=alert.escalation_tier or 1,
        escalated_at=alert.escalated_at,
        resolved_at=alert.resolved_at,
        snoozed_until=alert.snoozed_until,
        snooze_count=alert.snooze_count or 0,
        snooze_reason=alert.snooze_reason,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_by_name=current_user.full_name,
        acknowledgement_remarks=alert.acknowledgement_remarks,
        resolved_by=alert.resolved_by,
        resolved_by_name=None,
        resolution_remarks=alert.resolution_remarks,
        created_at=alert.created_at,
        age_hours=age_hours,
    )


@router.post("/alerts/{id}/snooze", response_model=AlertOut)
def snooze_alert(
    id: int,
    payload: AlertSnoozeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Snoozes an alert for a specified duration with mandatory reason.
    Enforces maximum snooze limits.
    """
    alert = EscalationService.snooze_alert(
        db=db,
        alert_id=id,
        user=current_user,
        hours=payload.hours,
        reason=payload.reason,
    )
    now = ClockService.get_now()
    age_hours = round(max(0.0, (now - normalize_dt(alert.created_at)).total_seconds() / 3600.0), 1)

    return AlertOut(
        id=alert.id,
        alert_rule_id=alert.alert_rule_id,
        rule_code=alert.rule.code if alert.rule else "",
        rule_name=alert.rule.name if alert.rule else "",
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        status=alert.status.value,
        application_id=alert.application_id,
        application_number=alert.application.application_number if alert.application else None,
        institution_id=alert.institution_id,
        institution_name=alert.institution.name if alert.institution else None,
        document_id=alert.document_id,
        undertaking_id=alert.undertaking_id,
        recipient_user_id=alert.recipient_user_id,
        recipient_user_name=alert.recipient_user.full_name if alert.recipient_user else None,
        recipient_role=alert.recipient_role.value if alert.recipient_role else "",
        title=alert.title,
        message=alert.message,
        explanation_meta=alert.explanation_meta or {},
        escalation_tier=alert.escalation_tier or 1,
        escalated_at=alert.escalated_at,
        resolved_at=alert.resolved_at,
        snoozed_until=alert.snoozed_until,
        snooze_count=alert.snooze_count or 0,
        snooze_reason=alert.snooze_reason,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_by_name=alert.acknowledged_user.full_name if alert.acknowledged_user else None,
        acknowledgement_remarks=alert.acknowledgement_remarks,
        resolved_by=alert.resolved_by,
        resolved_by_name=None,
        resolution_remarks=alert.resolution_remarks,
        created_at=alert.created_at,
        age_hours=age_hours,
    )


@router.post("/alerts/{id}/resolve", response_model=AlertOut)
def resolve_alert(
    id: int,
    payload: AlertResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Statutory resolution of an alert.
    Restricted to Competent Authority, Regional Head (in region), or Admin.
    """
    alert = EscalationService.resolve_alert(
        db=db,
        alert_id=id,
        user=current_user,
        remarks=payload.remarks,
    )
    now = ClockService.get_now()
    age_hours = round(max(0.0, (now - normalize_dt(alert.created_at)).total_seconds() / 3600.0), 1)

    return AlertOut(
        id=alert.id,
        alert_rule_id=alert.alert_rule_id,
        rule_code=alert.rule.code if alert.rule else "",
        rule_name=alert.rule.name if alert.rule else "",
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        status=alert.status.value,
        application_id=alert.application_id,
        application_number=alert.application.application_number if alert.application else None,
        institution_id=alert.institution_id,
        institution_name=alert.institution.name if alert.institution else None,
        document_id=alert.document_id,
        undertaking_id=alert.undertaking_id,
        recipient_user_id=alert.recipient_user_id,
        recipient_user_name=alert.recipient_user.full_name if alert.recipient_user else None,
        recipient_role=alert.recipient_role.value if alert.recipient_role else "",
        title=alert.title,
        message=alert.message,
        explanation_meta=alert.explanation_meta or {},
        escalation_tier=alert.escalation_tier or 1,
        escalated_at=alert.escalated_at,
        resolved_at=alert.resolved_at,
        snoozed_until=alert.snoozed_until,
        snooze_count=alert.snooze_count or 0,
        snooze_reason=alert.snooze_reason,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_by_name=alert.acknowledged_user.full_name if alert.acknowledged_user else None,
        acknowledgement_remarks=alert.acknowledgement_remarks,
        resolved_by=alert.resolved_by,
        resolved_by_name=current_user.full_name,
        resolution_remarks=alert.resolution_remarks,
        created_at=alert.created_at,
        age_hours=age_hours,
    )


# -----------------------------------------------------------------------------
# 3. MANUAL RUN NOW (Admin & Evaluator Trigger)
# -----------------------------------------------------------------------------

@router.post("/alerts/run-now")
def run_alert_evaluation_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "REGIONAL_HEAD", "COMPETENT_AUTHORITY"])),
):
    """
    Manually triggers an immediate alert rule and escalation evaluation cycle.
    Logged in database table scheduler_runs.
    """
    result = run_checks_now(triggered_by=f"USER:{current_user.username}")
    return result


# -----------------------------------------------------------------------------
# 4. IN-APP NOTIFICATIONS
# -----------------------------------------------------------------------------

@router.get("/notifications", response_model=NotificationSummaryOut)
def list_notifications(
    is_read: Optional[bool] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List in-app notifications for the logged-in user, including unread count.
    """
    base_query = db.query(Notification).filter(Notification.recipient_user_id == current_user.id)
    unread_count = base_query.filter(Notification.is_read == False).count()

    query = base_query
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    notifications = query.order_by(desc(Notification.sent_at)).limit(limit).all()

    items = []
    now = ClockService.get_now()
    for n in notifications:
        alert_out = None
        if n.alert:
            alert_out = AlertOut(
                id=n.alert.id,
                alert_rule_id=n.alert.alert_rule_id,
                rule_code=n.alert.rule.code if n.alert.rule else "",
                rule_name=n.alert.rule.name if n.alert.rule else "",
                alert_type=n.alert.alert_type.value,
                severity=n.alert.severity.value,
                status=n.alert.status.value,
                application_id=n.alert.application_id,
                application_number=n.alert.application.application_number if n.alert.application else None,
                institution_id=n.alert.institution_id,
                institution_name=n.alert.institution.name if n.alert.institution else None,
                document_id=n.alert.document_id,
                undertaking_id=n.alert.undertaking_id,
                recipient_user_id=n.alert.recipient_user_id,
                recipient_user_name=current_user.full_name,
                recipient_role=n.alert.recipient_role.value if n.alert.recipient_role else "",
                title=n.alert.title,
                message=n.alert.message,
                explanation_meta=n.alert.explanation_meta or {},
                escalation_tier=n.alert.escalation_tier or 1,
                escalated_at=n.alert.escalated_at,
                resolved_at=n.alert.resolved_at,
                snoozed_until=n.alert.snoozed_until,
                snooze_count=n.alert.snooze_count or 0,
                snooze_reason=n.alert.snooze_reason,
                acknowledged_at=n.alert.acknowledged_at,
                acknowledged_by=n.alert.acknowledged_by,
                acknowledged_by_name=None,
                acknowledgement_remarks=n.alert.acknowledgement_remarks,
                resolved_by=n.alert.resolved_by,
                resolved_by_name=None,
                resolution_remarks=n.alert.resolution_remarks,
                created_at=n.alert.created_at,
                age_hours=round(max(0.0, (now - normalize_dt(n.alert.created_at)).total_seconds() / 3600.0), 1),
            )

        items.append(NotificationOut(
            id=n.id,
            alert_id=n.alert_id,
            title=n.title,
            body=n.body,
            is_read=n.is_read,
            read_at=n.read_at,
            sent_at=n.sent_at,
            alert=alert_out,
        ))

    return NotificationSummaryOut(
        unread_count=unread_count,
        notifications=items,
    )


@router.post("/notifications/{id}/read")
def mark_notification_read(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a single notification as read.
    """
    notif = db.query(Notification).filter(
        Notification.id == id,
        Notification.recipient_user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    notif.read_at = ClockService.get_now()
    db.commit()
    return {"status": "success", "id": id, "is_read": True}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark all unread notifications for current user as read.
    """
    now = ClockService.get_now()
    updated = db.query(Notification).filter(
        Notification.recipient_user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True, "read_at": now})
    db.commit()
    return {"status": "success", "count_marked_read": updated}


# -----------------------------------------------------------------------------
# 5. EMAIL OUTBOX (Admin)
# -----------------------------------------------------------------------------

@router.get("/outbox", response_model=List[EmailOutboxOut])
def list_email_outbox(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"])),
):
    """
    Admin-only endpoint to inspect the database email outbox queue.
    """
    query = db.query(EmailOutbox)
    if status_filter:
        query = query.filter(EmailOutbox.status == status_filter.upper())

    items = query.order_by(desc(EmailOutbox.created_at)).offset(offset).limit(limit).all()

    return [
        EmailOutboxOut(
            id=item.id,
            recipient_email=item.recipient_email,
            recipient_user_id=item.recipient_user_id,
            recipient_name=item.recipient.full_name if item.recipient else None,
            subject=item.subject,
            body=item.body,
            status=item.status,
            template_code=item.template_code,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            attempts=item.attempts,
            error_message=item.error_message,
            created_at=item.created_at,
            sent_at=item.sent_at,
        )
        for item in items
    ]


# -----------------------------------------------------------------------------
# 6. REGIONAL ESCALATION MATRIX
# -----------------------------------------------------------------------------

@router.get("/escalation/matrix", response_model=EscalationMatrixOut)
def get_escalation_matrix(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the real-time Escalation Matrix for all 5 regions:
    L1 (Scrutiny Officer), L2 (Regional Head), L3 (Competent Authority),
    including assigned officer names and open alert counts per level.
    """
    regions = db.query(Region).order_by(Region.id).all()
    matrix_items = []

    # Get national Competent Authority for L3
    ca_user = db.query(User).filter(
        User.role.has(code="COMPETENT_AUTHORITY"),
        User.is_active == True
    ).first()
    ca_name = ca_user.full_name if ca_user else "AICTE Member Secretary / Chairman"

    for reg in regions:
        # L1 Officer
        l1_user = db.query(User).filter(
            User.role.has(code="SCRUTINY_OFFICER"),
            User.region_id == reg.id,
            User.is_active == True
        ).first()
        l1_name = l1_user.full_name if l1_user else f"Desk Officer ({reg.name})"

        # L2 Regional Head
        l2_user = db.query(User).filter(
            User.role.has(code="REGIONAL_HEAD"),
            User.region_id == reg.id,
            User.is_active == True
        ).first()
        l2_name = l2_user.full_name if l2_user else f"Regional Director ({reg.headquarters})"

        # Open alerts counts for this region
        reg_alerts = db.query(Alert).outerjoin(Application, Alert.application_id == Application.id)\
                                    .outerjoin(Institution, Alert.institution_id == Institution.id)\
                                    .filter(
                                        (Application.region_id == reg.id) | (Institution.region_id == reg.id),
                                        Alert.status.in_([
                                            AlertStatusEnum.ACTIVE,
                                            AlertStatusEnum.ACKNOWLEDGED,
                                            AlertStatusEnum.SNOOZED,
                                            AlertStatusEnum.ESCALATED,
                                        ])
                                    ).all()

        l1_count = sum(1 for a in reg_alerts if (a.escalation_tier or 1) == 1)
        l2_count = sum(1 for a in reg_alerts if (a.escalation_tier or 1) == 2)
        l3_count = sum(1 for a in reg_alerts if (a.escalation_tier or 1) >= 3)

        matrix_items.append(RegionEscalationItem(
            region_id=reg.id,
            region_name=reg.name,
            l1_role="Scrutiny Officer",
            l1_officer=l1_name,
            l1_alerts_count=l1_count,
            l2_role="Regional Head",
            l2_officer=l2_name,
            l2_alerts_count=l2_count,
            l3_role="Competent Authority",
            l3_officer=ca_name,
            l3_alerts_count=l3_count,
        ))

    return EscalationMatrixOut(regions=matrix_items)


# -----------------------------------------------------------------------------
# 7. CONFIG EDITING (Admin Only, Validated, Audited)
# -----------------------------------------------------------------------------

@router.get("/config/alert-rules", response_model=List[AlertRuleOut])
def get_alert_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all 8 seeded alert rules.
    """
    rules = db.query(AlertRule).order_by(AlertRule.id).all()
    return rules


@router.put("/config/alert-rules/{id}", response_model=AlertRuleOut)
def update_alert_rule(
    id: int,
    payload: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"])),
):
    """
    Update alert rule parameters (thresholds, reminder values, severity, active state).
    Admin only, validated, audited.
    """
    rule = db.query(AlertRule).filter(AlertRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    old_data = {
        "condition_logic": rule.condition_logic,
        "severity": rule.severity.value,
        "is_active": rule.is_active,
        "template_message": rule.template_message,
    }

    if payload.name:
        rule.name = payload.name
    if payload.condition_logic is not None:
        rule.condition_logic = payload.condition_logic
    if payload.severity:
        rule.severity = AlertSeverityEnum(payload.severity.upper())
    if payload.is_active is not None:
        rule.is_active = payload.is_active
    if payload.template_message:
        rule.template_message = payload.template_message
    if payload.aph_reference_clause:
        rule.aph_reference_clause = payload.aph_reference_clause

    AuditService.log(
        db=db,
        table_name="alert_rules",
        record_id=rule.id,
        action="UPDATE_ALERT_RULE",
        actor_id=current_user.id,
        old_values=old_data,
        new_values={
            "condition_logic": rule.condition_logic,
            "severity": rule.severity.value,
            "is_active": rule.is_active,
            "template_message": rule.template_message,
        }
    )
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/config/escalation-rules", response_model=List[EscalationRuleOut])
def get_escalation_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all 3-tier escalation rules for alert types.
    """
    rules = db.query(EscalationRule).order_by(EscalationRule.id).all()
    output = []
    for r in rules:
        output.append(EscalationRuleOut(
            id=r.id,
            alert_rule_id=r.alert_rule_id,
            rule_code=r.alert_rule.code if r.alert_rule else None,
            rule_name=r.alert_rule.name if r.alert_rule else None,
            tier_level=r.tier_level,
            target_role=r.target_role.value,
            trigger_delay_days=r.trigger_delay_days,
            action_required=r.action_required,
            created_at=r.created_at,
        ))
    return output


@router.put("/config/escalation-rules/{id}", response_model=EscalationRuleOut)
def update_escalation_rule(
    id: int,
    payload: EscalationRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"])),
):
    """
    Update escalation threshold delay and required action.
    Admin only, validated, audited.
    """
    rule = db.query(EscalationRule).filter(EscalationRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Escalation rule not found")

    old_data = {
        "trigger_delay_days": rule.trigger_delay_days,
        "action_required": rule.action_required,
    }

    rule.trigger_delay_days = payload.trigger_delay_days
    if payload.action_required:
        rule.action_required = payload.action_required

    AuditService.log(
        db=db,
        table_name="escalation_rules",
        record_id=rule.id,
        action="UPDATE_ESCALATION_RULE",
        actor_id=current_user.id,
        old_values=old_data,
        new_values={
            "trigger_delay_days": rule.trigger_delay_days,
            "action_required": rule.action_required,
        }
    )
    db.commit()
    db.refresh(rule)

    return EscalationRuleOut(
        id=rule.id,
        alert_rule_id=rule.alert_rule_id,
        rule_code=rule.alert_rule.code if rule.alert_rule else None,
        rule_name=rule.alert_rule.name if rule.alert_rule else None,
        tier_level=rule.tier_level,
        target_role=rule.target_role.value,
        trigger_delay_days=rule.trigger_delay_days,
        action_required=rule.action_required,
        created_at=rule.created_at,
    )
