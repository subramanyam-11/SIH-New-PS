"""
Smart Alert Ranking & Priority Scoring Service for SIH26262 (Phase 7 Innovation Layer).
Computes explainable composite priority scores (0-100) for active regulatory alerts
based on:
1. Severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)
2. Days overdue in regulatory violation
3. Escalation tier (Tier 1 -> Tier 2 -> Tier 3)
4. Regulatory impact (linked application delay risk score, new institution flag)

Decision support only: Alerts rank supervisory attention; they never automate decisions.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import (
    Alert, AlertPriorityScore, AlertStatusEnum, AlertSeverityEnum,
    User, UserRoleEnum, Role, Application, Institution, SystemConfig, EmailOutbox
)
from app.services.clock import ClockService, normalize_dt
from app.services.email_service import EmailService

# Default Priority Scoring Weights (must total 100)
DEFAULT_PRIORITY_WEIGHTS = {
    "severity": 35,
    "days_overdue": 30,
    "escalation_level": 20,
    "impact": 15,
}

SEVERITY_RATIOS = {
    AlertSeverityEnum.CRITICAL: 1.0,
    AlertSeverityEnum.HIGH: 0.75,
    AlertSeverityEnum.MEDIUM: 0.45,
    AlertSeverityEnum.LOW: 0.25,
    AlertSeverityEnum.INFO: 0.10,
}

TIER_RATIOS = {
    3: 1.0,
    2: 0.6,
    1: 0.25,
}


class AlertRankingService:
    """
    Ranks open alerts by urgency and regulatory impact.
    Stores factor snapshots and generates human-readable ranking rationales.
    """

    @staticmethod
    def get_weights(db: Session) -> Dict[str, int]:
        """Fetch alert priority weights from system_config or return defaults."""
        cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "alert_priority_weights").first()
        if cfg and isinstance(cfg.config_value, dict):
            return cfg.config_value
        return dict(DEFAULT_PRIORITY_WEIGHTS)

    @staticmethod
    def compute_alert_priority(
        db: Session,
        alert: Alert,
        weights: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Computes the priority score (0-100) for a single alert.
        Returns factors, raw values, and plain explanation.
        """
        if weights is None:
            weights = AlertRankingService.get_weights(db)

        w_sev = weights.get("severity", 35)
        w_overdue = weights.get("days_overdue", 30)
        w_tier = weights.get("escalation_level", 20)
        w_impact = weights.get("impact", 15)

        now = normalize_dt(ClockService.get_now())

        # 1. Severity points
        sev_ratio = SEVERITY_RATIOS.get(alert.severity, 0.4)
        points_sev = round(sev_ratio * w_sev, 1)

        # 2. Overdue days points (cap at 10 days)
        # Parse from explanation_meta or calculate from created_at
        overdue_days = 0.0
        meta = alert.explanation_meta or {}
        actual_val = str(meta.get("actual_value", ""))
        if "days overdue" in actual_val:
            try:
                overdue_days = float(actual_val.split("days overdue")[0].strip().split()[-1])
            except Exception:
                overdue_days = 0.0
        elif "days ago" in actual_val:
            try:
                overdue_days = float(actual_val.split("days ago")[0].strip().split()[-1])
            except Exception:
                overdue_days = 0.0
        else:
            age_h = (now - normalize_dt(alert.created_at)).total_seconds() / 3600.0
            overdue_days = max(0.0, (age_h - 48.0) / 24.0)

        overdue_ratio = min(max(0.0, overdue_days) / 10.0, 1.0)
        points_overdue = round(overdue_ratio * w_overdue, 1)

        # 3. Escalation Tier points
        tier = alert.escalation_tier or 1
        tier_ratio = TIER_RATIOS.get(tier, 0.25)
        points_tier = round(tier_ratio * w_tier, 1)

        # 4. Impact points (linked application risk score + new institution check)
        impact_score = 0.0
        app_risk_score = 0.0
        is_new_inst = False

        if alert.application:
            app_risk_score = alert.application.delay_risk_score or 0.0
            if alert.application.institution:
                is_new_inst = "NEW" in (alert.application.institution.name or "").upper() or "NEW" in (alert.application.category.code if alert.application.category else "").upper()
        elif alert.institution:
            is_new_inst = "NEW" in (alert.institution.name or "").upper()

        impact_ratio = (app_risk_score / 100.0) * 0.8 + (0.2 if is_new_inst else 0.0)
        impact_ratio = min(impact_ratio, 1.0)
        points_impact = round(impact_ratio * w_impact, 1)

        total_priority = round(min(100.0, points_sev + points_overdue + points_tier + points_impact), 1)

        # Compose plain human-readable explanation
        reasons = []
        reasons.append(f"{alert.severity.value} severity ({points_sev}/{w_sev} pts)")
        if overdue_days > 0:
            reasons.append(f"{round(overdue_days, 1)}d overdue ({points_overdue}/{w_overdue} pts)")
        if tier > 1:
            reasons.append(f"Tier {tier} escalation ({points_tier}/{w_tier} pts)")
        if app_risk_score > 0:
            reasons.append(f"linked case risk {app_risk_score} ({points_impact}/{w_impact} pts)")

        explanation = f"Priority {total_priority}: " + ", ".join(reasons)

        return {
            "priority_score": total_priority,
            "factor_severity": points_sev,
            "factor_overdue_days": points_overdue,
            "factor_escalation": points_tier,
            "factor_risk_impact": points_impact,
            "raw_overdue_days": round(overdue_days, 1),
            "raw_tier": tier,
            "raw_app_risk": app_risk_score,
            "explanation": explanation,
        }

    @staticmethod
    def sync_alert_priorities(db: Session) -> int:
        """
        Computes and updates priority scores for all open alerts.
        """
        open_alerts = db.query(Alert).filter(
            Alert.status.in_([
                AlertStatusEnum.ACTIVE,
                AlertStatusEnum.ACKNOWLEDGED,
                AlertStatusEnum.SNOOZED,
                AlertStatusEnum.ESCALATED,
            ])
        ).all()

        weights = AlertRankingService.get_weights(db)
        now = normalize_dt(ClockService.get_now())
        count = 0

        for a in open_alerts:
            res = AlertRankingService.compute_alert_priority(db, a, weights)

            score_record = db.query(AlertPriorityScore).filter(
                AlertPriorityScore.alert_id == a.id
            ).first()

            if not score_record:
                score_record = AlertPriorityScore(alert_id=a.id)
                db.add(score_record)

            score_record.priority_score = res["priority_score"]
            score_record.factor_severity = res["factor_severity"]
            score_record.factor_overdue_days = res["factor_overdue_days"]
            score_record.factor_escalation = res["factor_escalation"]
            score_record.factor_risk_impact = res["factor_risk_impact"]
            score_record.explanation = res["explanation"]
            score_record.computed_at = now
            count += 1

        db.commit()
        return count

    @staticmethod
    def get_needs_attention_today(
        db: Session,
        user: User,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Top 10 highest-priority open alerts for the current user's role and region.
        """
        # Ensure priority scores are computed
        AlertRankingService.sync_alert_priorities(db)

        query = db.query(Alert, AlertPriorityScore).join(
            AlertPriorityScore, Alert.id == AlertPriorityScore.alert_id
        ).filter(
            Alert.status.in_([AlertStatusEnum.ACTIVE, AlertStatusEnum.ESCALATED])
        )

        role_code = user.role.code if user.role else ""
        if role_code == "INSTITUTION_USER":
            query = query.filter(Alert.institution_id == user.institution_id)
        elif role_code in ["SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_HEAD"] and user.region_id:
            query = query.outerjoin(Application, Alert.application_id == Application.id)\
                         .outerjoin(Institution, Alert.institution_id == Institution.id)\
                         .filter(
                             (Application.region_id == user.region_id) |
                             (Institution.region_id == user.region_id) |
                             (Alert.recipient_user_id == user.id)
                         )

        items = query.order_by(desc(AlertPriorityScore.priority_score)).limit(limit).all()

        results = []
        for alert, score in items:
            results.append({
                "alert_id": alert.id,
                "title": alert.title,
                "rule_code": alert.rule.code if alert.rule else "",
                "rule_name": alert.rule.name if alert.rule else "",
                "severity": alert.severity.value,
                "status": alert.status.value,
                "escalation_tier": alert.escalation_tier,
                "priority_score": score.priority_score,
                "priority_explanation": score.explanation,
                "application_id": alert.application_id,
                "application_number": alert.application.application_number if alert.application else None,
                "institution_name": alert.institution.name if alert.institution else (alert.application.institution.name if alert.application and alert.application.institution else None),
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            })

        return results

    @staticmethod
    def generate_officer_daily_digests(db: Session) -> int:
        """
        Drafts a daily digest into the email outbox per officer, combining their top
        priority alerts into one consolidated message.
        """
        AlertRankingService.sync_alert_priorities(db)
        now = normalize_dt(ClockService.get_now())

        # Find officers with active open alerts
        officers = db.query(User).filter(
            User.is_active == True,
            User.role.has(Role.code.in_([
                "SCRUTINY_OFFICER", "REGIONAL_HEAD", "EVC_COORDINATOR", "COMPETENT_AUTHORITY"
            ]))
        ).all()

        drafts_created = 0

        for officer in officers:
            top_alerts = AlertRankingService.get_needs_attention_today(db, officer, limit=5)
            if not top_alerts:
                continue

            # Build consolidated digest text
            lines = [
                f"Dear {officer.full_name},",
                "",
                f"This is your daily AICTE regulatory compliance alert digest for {now.strftime('%d-%b-%Y')}.",
                f"You have {len(top_alerts)} priority action item(s) requiring desk review today:",
                "",
            ]

            for i, a in enumerate(top_alerts, 1):
                app_ref = f" [App: {a['application_number']}]" if a['application_number'] else ""
                lines.append(f"{i}. [{a['severity']}] {a['rule_name']}{app_ref} - Priority {a['priority_score']}/100")
                lines.append(f"   Why: {a['priority_explanation']}")
                lines.append("")

            lines.extend([
                "Please log in to the AICTE Approvals portal to review these dossiers.",
                "",
                "Note: Automation assists officers. Regulatory compliance verification and decisions remain with authorized officers.",
                "",
                "All India Council for Technical Education (AICTE)",
            ])

            body = "\n".join(lines)
            subject = f"[AICTE Digest] {len(top_alerts)} Priority Alerts for Today ({now.strftime('%d-%b-%Y')})"

            outbox = EmailOutbox(
                template_code="ALERT_DAILY_DIGEST",
                recipient_email=officer.email,
                recipient_user_id=officer.id,
                subject=subject,
                body=body,
                status="PENDING",
                created_at=now,
            )
            db.add(outbox)
            drafts_created += 1

        db.commit()
        return drafts_created
