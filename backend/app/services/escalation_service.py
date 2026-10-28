"""
Escalation Ladder Service for SIH26262.
Handles 3-tier escalation (L1 Scrutiny Officer -> L2 Regional Head -> L3 Competent Authority),
acknowledgements, snoozing with caps, and statutory resolution.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import (
    Alert, AlertStatusEnum, User, UserRoleEnum,
    EscalationRule, EscalationHistory, Notification, NotificationChannelEnum,
    SystemConfig, Application
)
from app.services.clock import ClockService, normalize_dt
from app.services.email_service import EmailService
from app.services.audit import AuditService


class EscalationService:
    @staticmethod
    def evaluate_escalations(db: Session) -> int:
        """
        Scans all open alerts and escalates those exceeding threshold delays.
        L1 -> L2 -> L3 ladder.
        Returns count of escalated alerts.
        """
        now = ClockService.get_now()
        escalated_count = 0

        # Unresolved alerts
        open_alerts = db.query(Alert).filter(
            Alert.status.in_([
                AlertStatusEnum.ACTIVE,
                AlertStatusEnum.ACKNOWLEDGED,
                AlertStatusEnum.SNOOZED,
                AlertStatusEnum.ESCALATED,
            ])
        ).all()

        for alert in open_alerts:
            current_tier = alert.escalation_tier or 1
            if current_tier >= 3:
                continue  # Already at maximum level (L3 Competent Authority)

            next_tier = current_tier + 1
            esc_rule = db.query(EscalationRule).filter(
                EscalationRule.alert_rule_id == alert.alert_rule_id,
                EscalationRule.tier_level == next_tier
            ).first()

            if not esc_rule:
                continue

            # Calculate days elapsed since creation
            created_at = normalize_dt(alert.created_at)
            days_open = (now - created_at).total_seconds() / 86400.0

            # Trigger condition: days open >= trigger_delay_days
            # Note: snoozing does NOT hide an alert from escalating if trigger_delay_days is reached
            if days_open >= esc_rule.trigger_delay_days:
                target_user_id, target_role = EscalationService._find_target_officer(db, alert, esc_rule.target_role)

                old_tier = current_tier
                alert.escalation_tier = next_tier
                alert.escalated_at = now
                alert.status = AlertStatusEnum.ESCALATED
                alert.recipient_role = target_role
                alert.recipient_user_id = target_user_id

                reason = esc_rule.action_required or f"Open for {round(days_open, 1)} days without resolution. Escalated to Tier {next_tier} ({target_role.value})."

                # Write EscalationHistory row
                history_row = EscalationHistory(
                    alert_id=alert.id,
                    from_tier=old_tier,
                    to_tier=next_tier,
                    target_role=target_role.value,
                    recipient_user_id=target_user_id,
                    reason=reason,
                    created_at=now,
                )
                db.add(history_row)
                db.flush()

                # In-app notification for new tier officer
                if target_user_id:
                    notif = Notification(
                        alert_id=alert.id,
                        recipient_user_id=target_user_id,
                        channel=NotificationChannelEnum.IN_APP,
                        title=f"[AICTE Escalation Tier {next_tier}] {alert.title}",
                        body=f"Regulatory alert escalated to your level ({target_role.value}). Action: {reason}",
                        is_read=False,
                        sent_at=now,
                    )
                    db.add(notif)

                    target_user = db.query(User).filter(User.id == target_user_id).first()
                    if target_user and target_user.email:
                        EmailService.queue_from_template(
                            db=db,
                            template_code="ALERT_ESCALATION",
                            recipient_email=target_user.email,
                            recipient_user_id=target_user.id,
                            context={
                                "alert_title": alert.title,
                                "tier": next_tier,
                                "role": target_role.value,
                                "reason": reason,
                            },
                            default_subject=f"[AICTE Escalation Tier {next_tier}] {alert.title}",
                            default_body=f"Dear Officer,\n\nAlert '{alert.title}' has been escalated to Tier {next_tier}.\nReason: {reason}\n\nAll India Council for Technical Education",
                            entity_type="ALERT",
                            entity_id=alert.id,
                        )

                AuditService.log(
                    db=db,
                    table_name="alerts",
                    record_id=alert.id,
                    action="ALERT_ESCALATED",
                    old_values={"tier": old_tier},
                    new_values={"tier": next_tier, "target_role": target_role.value, "reason": reason},
                )

                escalated_count += 1

        db.commit()
        return escalated_count

    @staticmethod
    def _find_target_officer(db: Session, alert: Alert, target_role: UserRoleEnum) -> Tuple[Optional[int], UserRoleEnum]:
        """
        Resolves the user ID for an escalated role based on region or national scope.
        """
        region_id = 1
        if alert.application_id:
            app = db.query(Application).filter(Application.id == alert.application_id).first()
            if app:
                region_id = app.region_id
        elif alert.institution_id:
            from app.models import Institution
            inst = db.query(Institution).filter(Institution.id == alert.institution_id).first()
            if inst:
                region_id = inst.region_id

        if target_role == UserRoleEnum.REGIONAL_HEAD:
            user = db.query(User).filter(
                User.role.has(code="REGIONAL_HEAD"),
                User.region_id == region_id,
                User.is_active == True
            ).first()
            if user:
                return user.id, UserRoleEnum.REGIONAL_HEAD

        elif target_role == UserRoleEnum.COMPETENT_AUTHORITY:
            user = db.query(User).filter(
                User.role.has(code="COMPETENT_AUTHORITY"),
                User.is_active == True
            ).first()
            if user:
                return user.id, UserRoleEnum.COMPETENT_AUTHORITY

        # Fallback to Admin or primary officer
        admin = db.query(User).filter(User.role.has(code="ADMIN"), User.is_active == True).first()
        return admin.id if admin else None, target_role

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: int, user: User, remarks: Optional[str] = None) -> Alert:
        """
        Officer acknowledges receipt and responsibility of an alert.
        """
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        now = ClockService.get_now()
        alert.status = AlertStatusEnum.ACKNOWLEDGED
        alert.acknowledged_at = now
        alert.acknowledged_by = user.id
        alert.acknowledgement_remarks = remarks or "Acknowledged by assigned officer."

        AuditService.log(
            db=db,
            table_name="alerts",
            record_id=alert.id,
            action="ALERT_ACKNOWLEDGED",
            actor_id=user.id,
            new_values={"acknowledged_by": user.id, "remarks": alert.acknowledgement_remarks},
        )
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def snooze_alert(db: Session, alert_id: int, user: User, hours: float, reason: str) -> Alert:
        """
        Snoozes an alert for a specified duration with mandatory reason.
        Enforces maximum snooze count from system config (default: 2).
        """
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        if not reason or len(reason.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A substantive written reason (at least 5 characters) is required to snooze an alert."
            )

        # Get max snooze limit
        config_row = db.query(SystemConfig).filter(SystemConfig.config_key == "max_snooze_limit").first()
        max_snooze = int(config_row.config_value) if config_row and isinstance(config_row.config_value, (int, str)) else 2

        if alert.snooze_count >= max_snooze:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum permitted snooze limit ({max_snooze}) reached for this alert. Escalation or resolution is required."
            )

        now = ClockService.get_now()
        alert.status = AlertStatusEnum.SNOOZED
        alert.snoozed_until = now + timedelta(hours=hours)
        alert.snooze_count += 1
        alert.snooze_reason = reason

        AuditService.log(
            db=db,
            table_name="alerts",
            record_id=alert.id,
            action="ALERT_SNOOZED",
            actor_id=user.id,
            new_values={"snooze_count": alert.snooze_count, "snoozed_until": alert.snoozed_until.isoformat(), "reason": reason},
        )
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def resolve_alert(db: Session, alert_id: int, user: User, remarks: str) -> Alert:
        """
        Resolves an alert with mandatory remarks.
        Restricted to Competent Authority, Regional Head (in region), or Admin.
        """
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        role_code = user.role.code if user.role else ""
        if role_code not in ["ADMIN", "COMPETENT_AUTHORITY", "REGIONAL_HEAD"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the Competent Authority, Regional Head, or System Admin can mark an alert as resolved."
            )

        if not remarks or len(remarks.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A substantive written remark (at least 5 characters) is required to resolve an alert."
            )

        now = ClockService.get_now()
        alert.status = AlertStatusEnum.RESOLVED
        alert.resolved_at = now
        alert.resolved_by = user.id
        alert.resolution_remarks = remarks

        AuditService.log(
            db=db,
            table_name="alerts",
            record_id=alert.id,
            action="ALERT_RESOLVED",
            actor_id=user.id,
            new_values={"resolved_by": user.id, "remarks": remarks},
        )
        db.commit()
        db.refresh(alert)
        return alert
