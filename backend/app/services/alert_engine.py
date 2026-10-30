"""
Alert Rules Engine Service for SIH26262.
Evaluates regulatory alert rules against active entities using the configurable clock.
NOTE: Automation only observes and notifies; it NEVER moves, approves, rejects, or reverts an application.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import (
    Alert, AlertRule, AlertTypeEnum, AlertSeverityEnum, AlertStatusEnum,
    Application, ApplicationStatusEnum, Stage, User, UserRoleEnum,
    Document, DocumentStatusEnum, DocumentTypeEnum,
    Undertaking, UndertakingStatusEnum,
    EvcVisit, EvcStatusEnum, Notification, NotificationChannelEnum,
    EscalationRule, EscalationHistory, SystemConfig
)
from app.services.clock import ClockService, normalize_dt
from app.services.email_service import EmailService
from app.services.audit import AuditService
from app.services.working_day_service import WorkingDayService


class AlertEngine:
    @staticmethod
    def evaluate_all_rules(db: Session, triggered_by: str = "MANUAL") -> Dict[str, Any]:
        """
        Main entry point for rule evaluation.
        1. Loads active alert rules.
        2. Evaluates each rule against matching entities.
        3. Creates new alerts (with deduplication).
        4. Upgrades worsening conditions.
        5. Auto-resolves alerts whose condition has cleared.
        6. Returns summary metrics.
        """
        now = ClockService.get_now()
        rules = db.query(AlertRule).filter(AlertRule.is_active == True).all()

        created_count = 0
        upgraded_count = 0
        resolved_count = 0

        # Track keys of current violations to identify cleared alerts for auto-resolution
        # Key: (rule_id, entity_type, entity_id)
        current_violations: Dict[Tuple[int, str, int], Dict[str, Any]] = {}

        for rule in rules:
            violations = AlertEngine._evaluate_single_rule(db, rule, now)
            for entity_id, v_meta in violations.items():
                current_violations[(rule.id, rule.entity_type, entity_id)] = v_meta

                # Process violation: create or upgrade
                action = AlertEngine._process_violation(db, rule, entity_id, v_meta, now)
                if action == "CREATED":
                    created_count += 1
                elif action == "UPGRADED":
                    upgraded_count += 1

        # Check existing open alerts for auto-resolution
        open_alerts = db.query(Alert).filter(
            Alert.status.in_([
                AlertStatusEnum.ACTIVE,
                AlertStatusEnum.ACKNOWLEDGED,
                AlertStatusEnum.SNOOZED,
                AlertStatusEnum.ESCALATED,
            ])
        ).all()

        for alert in open_alerts:
            # Determine entity ID
            entity_id = alert.application_id or alert.document_id or alert.undertaking_id
            if not entity_id:
                continue

            entity_type = alert.rule.entity_type if alert.rule else "APPLICATION"
            key = (alert.alert_rule_id, entity_type, entity_id)

            if key not in current_violations:
                # The condition has cleared! Auto-resolve
                alert.status = AlertStatusEnum.RESOLVED
                alert.resolved_at = now
                if alert.application and alert.application.case_holder == "WITH_INSTITUTION" and alert.alert_type in [AlertTypeEnum.NEAR_BREACH, AlertTypeEnum.OVERDUE]:
                    alert.resolution_remarks = "clock paused: with institution"
                else:
                    alert.resolution_remarks = "Condition cleared automatically: entity is no longer in regulatory violation."
                resolved_count += 1

                AuditService.log(
                    db=db,
                    table_name="alerts",
                    record_id=alert.id,
                    action="ALERT_AUTO_RESOLVED",
                    new_values={"status": "RESOLVED", "reason": alert.resolution_remarks},
                )

        db.commit()

        return {
            "rules_evaluated": len(rules),
            "alerts_created": created_count,
            "alerts_upgraded": upgraded_count,
            "alerts_resolved": resolved_count,
            "evaluated_at": now.isoformat(),
            "triggered_by": triggered_by,
        }

    @staticmethod
    def _evaluate_single_rule(db: Session, rule: AlertRule, now: datetime) -> Dict[int, Dict[str, Any]]:
        """
        Evaluates a specific rule and returns a mapping: {entity_id: explanation_meta}
        """
        results: Dict[int, Dict[str, Any]] = {}
        cond = rule.condition_logic or {}
        now_date = now.date()

        # -------------------------------------------------------------------------
        # APPLICATION RULES
        # -------------------------------------------------------------------------
        if rule.entity_type == "APPLICATION":
            active_apps = db.query(Application).filter(
                Application.status == ApplicationStatusEnum.IN_PROGRESS
            ).all()

            from app.services.workflow_engine import WorkflowEngine

            for app in active_apps:
                # If clock is paused (WITH_INSTITUTION), near-breach and overdue alerts must NOT fire
                if app.case_holder == "WITH_INSTITUTION" and rule.code in ["RULE_SCRUTINY_NEAR_BREACH", "RULE_SCRUTINY_OVERDUE"]:
                    continue

                pendency = WorkflowEngine.get_application_pendency(db, app)
                days_in_stage = pendency["current_stage_aicte_days"]
                sla_days = app.current_stage.default_sla_days if app.current_stage else 7
                days_remaining = sla_days - days_in_stage
                day_basis_str = getattr(rule, "day_basis", "WORKING") or "WORKING"

                # RULE 1: Near breach (e.g. <= 2 days remaining and > 0)
                if rule.code == "RULE_SCRUTINY_NEAR_BREACH":
                    threshold = float(cond.get("value", 2.0))
                    if 0 < days_remaining <= threshold:
                        results[app.id] = {
                            "rule_code": rule.code,
                            "entity_type": "APPLICATION",
                            "entity_id": app.id,
                            "entity_label": app.application_number,
                            "institution_id": app.institution_id,
                            "institution_name": app.institution.name if app.institution else "",
                            "region_id": app.region_id,
                            "actual_value": f"{round(days_remaining, 1)} days remaining",
                            "threshold_value": f"<= {threshold} days remaining",
                            "why_this_fired": f"Application {app.application_number} has {round(days_remaining, 1)} days remaining before the {sla_days}-day SLA for {app.current_stage.name} lapses (Evaluated on {day_basis_str} days basis; holder: {app.case_holder}).",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter II Clause 2.3",
                            "day_basis": day_basis_str,
                            "case_holder": app.case_holder,
                            "is_sample_reference": True,
                        }

                # RULE 2: Overdue (days_remaining <= 0)
                elif rule.code == "RULE_SCRUTINY_OVERDUE":
                    threshold = float(cond.get("value", 0.0))
                    if days_remaining <= -threshold:
                        days_overdue = abs(round(days_remaining, 1))
                        results[app.id] = {
                            "rule_code": rule.code,
                            "entity_type": "APPLICATION",
                            "entity_id": app.id,
                            "entity_label": app.application_number,
                            "institution_id": app.institution_id,
                            "institution_name": app.institution.name if app.institution else "",
                            "region_id": app.region_id,
                            "actual_value": f"{days_overdue} days overdue",
                            "threshold_value": f">= {threshold} days overdue",
                            "why_this_fired": f"Application {app.application_number} exceeded statutory scrutiny SLA by {days_overdue} days in stage {app.current_stage.name} (Evaluated on {day_basis_str} days basis; holder: {app.case_holder}).",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter II Clause 2.3",
                            "day_basis": day_basis_str,
                            "case_holder": app.case_holder,
                            "is_sample_reference": True,
                        }

                # RULE 3: EVC Unscheduled
                elif rule.code == "RULE_EVC_UNSCHEDULED":
                    threshold = float(cond.get("value", 3.0))
                    if app.current_stage and app.current_stage.code == "EVC_PENDING":
                        # Check if scheduled visit exists
                        scheduled_visit = db.query(EvcVisit).filter(
                            EvcVisit.application_id == app.id,
                            EvcVisit.status.in_([EvcStatusEnum.SCHEDULED, EvcStatusEnum.VISIT_COMPLETED, EvcStatusEnum.REPORT_SUBMITTED])
                        ).first()
                        if not scheduled_visit and days_in_stage >= threshold:
                            results[app.id] = {
                                "rule_code": rule.code,
                                "entity_type": "APPLICATION",
                                "entity_id": app.id,
                                "entity_label": app.application_number,
                                "institution_id": app.institution_id,
                                "institution_name": app.institution.name if app.institution else "",
                                "region_id": app.region_id,
                                "actual_value": f"{round(days_in_stage, 1)} days in queue",
                                "threshold_value": f">= {threshold} days without schedule",
                                "why_this_fired": f"Application {app.application_number} has waited in the EVC queue for {round(days_in_stage, 1)} days without inspection allotment ({day_basis_str} days).",
                                "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter II Clause 2.6",
                                "day_basis": day_basis_str,
                                "case_holder": app.case_holder,
                                "is_sample_reference": True,
                            }

                # RULE 8: Multiple Reverts
                elif rule.code == "RULE_MULTIPLE_REVERTS":
                    threshold = int(cond.get("value", 2))
                    if app.revert_count >= threshold:
                        results[app.id] = {
                            "rule_code": rule.code,
                            "entity_type": "APPLICATION",
                            "entity_id": app.id,
                            "entity_label": app.application_number,
                            "institution_id": app.institution_id,
                            "institution_name": app.institution.name if app.institution else "",
                            "region_id": app.region_id,
                            "actual_value": f"{app.revert_count} clarification cycles completed",
                            "threshold_value": f">= {threshold} reverts",
                            "why_this_fired": f"Application {app.application_number} has undergone {app.revert_count} deficiency returns, meeting supervisory intervention threshold.",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter II Clause 2.5",
                            "day_basis": "CALENDAR",
                            "case_holder": app.case_holder,
                            "is_sample_reference": True,
                        }

                # RULE 9: EVC Visit Overdue
                elif rule.code == "RULE_EVC_VISIT_OVERDUE":
                    threshold = float(cond.get("value", 0.0))
                    # Check for visits that were scheduled on or before now_date with no report submitted
                    scheduled_visit = db.query(EvcVisit).filter(
                        EvcVisit.application_id == app.id,
                        EvcVisit.status == EvcStatusEnum.SCHEDULED,
                    ).order_by(EvcVisit.scheduled_date.asc()).first()
                    if scheduled_visit and scheduled_visit.scheduled_date and scheduled_visit.scheduled_date < now_date:
                        working_days_overdue = WorkingDayService.working_days_between(
                            db, scheduled_visit.scheduled_date, now_date, app.region_id
                        )
                        if working_days_overdue > threshold:
                            results[app.id] = {
                                "rule_code": rule.code,
                                "entity_type": "APPLICATION",
                                "entity_id": app.id,
                                "entity_label": app.application_number,
                                "institution_id": app.institution_id,
                                "institution_name": app.institution.name if app.institution else "",
                                "region_id": app.region_id,
                                "actual_value": f"{working_days_overdue} working days overdue without report",
                                "threshold_value": f"> {threshold} working days past visit date",
                                "why_this_fired": (
                                    f"EVC visit for {app.application_number} was scheduled for {scheduled_visit.scheduled_date.isoformat()}, "
                                    f"which passed {working_days_overdue} working days ago with no inspection report received."
                                ),
                                "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter II Clause 2.7",
                                "day_basis": "WORKING",
                                "case_holder": app.case_holder,
                                "is_sample_reference": True,
                            }

                # RULE 10 (Advisory): High Delay Risk Early Warning
                elif rule.code == "RULE_RISK_HIGH":
                    # Early-warning notice that fires when risk score reaches HIGH band before overdue
                    from app.services.risk_score_service import RiskScoreService
                    risk_info = RiskScoreService.compute_score(db, app)
                    if risk_info.get("band") == "HIGH" and days_remaining > 0:
                        results[app.id] = {
                            "rule_code": rule.code,
                            "entity_type": "APPLICATION",
                            "entity_id": app.id,
                            "entity_label": app.application_number,
                            "institution_id": app.institution_id,
                            "institution_name": app.institution.name if app.institution else "",
                            "region_id": app.region_id,
                            "actual_value": f"Risk Score {risk_info['score']} (HIGH)",
                            "threshold_value": "Risk Band == HIGH (Advisory before SLA breach)",
                            "why_this_fired": (
                                f"Early Warning: Application {app.application_number} has accumulated high delay risk points "
                                f"({risk_info['score']}/100) while {round(days_remaining, 1)} days remain before SLA breach."
                            ),
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter II Clause 2.1 Advisory",
                            "day_basis": "WORKING",
                            "case_holder": app.case_holder,
                            "is_sample_reference": True,
                        }

        # -------------------------------------------------------------------------
        # DOCUMENT RULES
        # -------------------------------------------------------------------------
        elif rule.entity_type == "DOCUMENT":
            # For general expiry and critical rules, evaluate non-superseded documents
            active_docs = db.query(Document).filter(
                Document.status != DocumentStatusEnum.SUPERSEDED
            ).all()

            for doc in active_docs:
                days_until_expiry = (doc.expiry_date - now_date).days
                region_id = doc.institution.region_id if doc.institution else None
                is_non_working, nw_reason = WorkingDayService.is_holiday_or_weekend(db, doc.expiry_date, region_id)
                nw_note = f" Note: Expiry date falls on a {nw_reason}; manual verification deferred to next working day." if is_non_working else ""

                # RULE 4: Lease 90D Warning
                if rule.code == "RULE_LEASE_90D":
                    threshold = int(cond.get("value", 90))
                    if 30 < days_until_expiry <= threshold and doc.status not in [DocumentStatusEnum.RENEWAL_SUBMITTED]:
                        results[doc.id] = {
                            "rule_code": rule.code,
                            "entity_type": "DOCUMENT",
                            "entity_id": doc.id,
                            "entity_label": f"{doc.title} ({doc.document_number})",
                            "institution_id": doc.institution_id,
                            "institution_name": doc.institution.name if doc.institution else "",
                            "region_id": doc.institution.region_id if doc.institution else 1,
                            "actual_value": f"{days_until_expiry} days until expiry",
                            "threshold_value": f"<= {threshold} days",
                            "why_this_fired": f"Statutory document '{doc.title}' expires in {days_until_expiry} days on {doc.expiry_date.isoformat()} (CALENDAR days basis).{nw_note}",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter I Clause 1.4(e)",
                            "day_basis": "CALENDAR",
                            "non_working_day_note": nw_note.strip() if is_non_working else None,
                            "is_sample_reference": True,
                        }

                # RULE 5: Lease 30D Critical
                elif rule.code == "RULE_LEASE_30D":
                    threshold = int(cond.get("value", 30))
                    if 0 < days_until_expiry <= threshold and doc.status not in [DocumentStatusEnum.RENEWAL_SUBMITTED]:
                        results[doc.id] = {
                            "rule_code": rule.code,
                            "entity_type": "DOCUMENT",
                            "entity_id": doc.id,
                            "entity_label": f"{doc.title} ({doc.document_number})",
                            "institution_id": doc.institution_id,
                            "institution_name": doc.institution.name if doc.institution else "",
                            "region_id": doc.institution.region_id if doc.institution else 1,
                            "actual_value": f"{days_until_expiry} days until expiry (Critical)",
                            "threshold_value": f"<= {threshold} days",
                            "why_this_fired": f"CRITICAL: Statutory document '{doc.title}' expires in {days_until_expiry} days on {doc.expiry_date.isoformat()} (CALENDAR days basis). Renewal required immediately.{nw_note}",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter I Clause 1.4(e)",
                            "day_basis": "CALENDAR",
                            "non_working_day_note": nw_note.strip() if is_non_working else None,
                            "is_sample_reference": True,
                        }

                # RULE 6: Fire NOC Expired
                elif rule.code == "RULE_FIRE_NOC_EXPIRED":
                    is_fire = (
                        doc.document_type == DocumentTypeEnum.FIRE_SAFETY_NOC
                        or "FIRE" in str(getattr(doc, "document_type", "")).upper()
                        or "FIRE" in (doc.title or "").upper()
                    )
                    if is_fire and days_until_expiry <= 0:
                        days_expired = abs(days_until_expiry)
                        results[doc.id] = {
                            "rule_code": rule.code,
                            "entity_type": "DOCUMENT",
                            "entity_id": doc.id,
                            "entity_label": f"{doc.title} ({doc.document_number})",
                            "institution_id": doc.institution_id,
                            "institution_name": doc.institution.name if doc.institution else "",
                            "region_id": doc.institution.region_id if doc.institution else 1,
                            "actual_value": f"Expired {days_expired} days ago ({doc.expiry_date.isoformat()})",
                            "threshold_value": "Expired (<= 0 days)",
                            "why_this_fired": f"Statutory compliance failure: Document '{doc.title}' expired on {doc.expiry_date.isoformat()} and has not been renewed (CALENDAR days basis).{nw_note}",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter I Clause 1.4(g)",
                            "day_basis": "CALENDAR",
                            "non_working_day_note": nw_note.strip() if is_non_working else None,
                            "is_sample_reference": True,
                        }

                # RULE 11: General Prescribed Document Expired (Non-Fire NOC: Lease, FDR, etc.)
                elif rule.code == "RULE_DOCUMENT_EXPIRED":
                    is_fire = (
                        doc.document_type == DocumentTypeEnum.FIRE_SAFETY_NOC
                        or "FIRE" in str(getattr(doc, "document_type", "")).upper()
                        or "FIRE" in (doc.title or "").upper()
                    )
                    # Avoid duplicate alerts with RULE_FIRE_NOC_EXPIRED
                    if not is_fire and days_until_expiry <= 0:
                        # Auto-resolves only after an officer verifies a renewal (status becomes SUPERSEDED)
                        days_expired = abs(days_until_expiry)
                        results[doc.id] = {
                            "rule_code": rule.code,
                            "entity_type": "DOCUMENT",
                            "entity_id": doc.id,
                            "entity_label": f"{doc.title} ({doc.document_number})",
                            "institution_id": doc.institution_id,
                            "institution_name": doc.institution.name if doc.institution else "",
                            "region_id": doc.institution.region_id if doc.institution else 1,
                            "actual_value": f"Expired {days_expired} days ago ({doc.expiry_date.isoformat()})",
                            "threshold_value": "Expired (<= 0 days)",
                            "why_this_fired": (
                                f"Prescribed document '{doc.title}' expired on {doc.expiry_date.isoformat()} "
                                f"without a verified renewal on record (CALENDAR days basis).{nw_note}"
                            ),
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter I Clause 1.4(h)",
                            "day_basis": "CALENDAR",
                            "non_working_day_note": nw_note.strip() if is_non_working else None,
                            "is_sample_reference": True,
                        }

        # -------------------------------------------------------------------------
        # UNDERTAKING RULES
        # -------------------------------------------------------------------------
        elif rule.entity_type == "UNDERTAKING":
            active_undertakings = db.query(Undertaking).filter(
                Undertaking.status.notin_([UndertakingStatusEnum.COMPLIED, UndertakingStatusEnum.VERIFIED])
            ).all()

            for ut in active_undertakings:
                days_until_due = (ut.due_date - now_date).days
                region_id = ut.institution.region_id if ut.institution else None
                is_non_working, nw_reason = WorkingDayService.is_holiday_or_weekend(db, ut.due_date, region_id)
                nw_note = f" Note: Due date falls on a {nw_reason}; manual compliance verification deferred to next working day." if is_non_working else ""

                # RULE 7: Undertaking Due 15D
                if rule.code == "RULE_UNDERTAKING_DUE_15D":
                    threshold = int(cond.get("value", 15))
                    if 0 <= days_until_due <= threshold:
                        results[ut.id] = {
                            "rule_code": rule.code,
                            "entity_type": "UNDERTAKING",
                            "entity_id": ut.id,
                            "entity_label": ut.condition_title,
                            "institution_id": ut.institution_id,
                            "institution_name": ut.institution.name if ut.institution else "",
                            "region_id": ut.institution.region_id if ut.institution else 1,
                            "actual_value": f"{days_until_due} days remaining",
                            "threshold_value": f"<= {threshold} days",
                            "why_this_fired": f"Undertaking condition '{ut.condition_title}' is due in {days_until_due} days ({ut.due_date.isoformat()}) on CALENDAR days basis.{nw_note}",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter III Clause 3.2",
                            "day_basis": "CALENDAR",
                            "non_working_day_note": nw_note.strip() if is_non_working else None,
                            "is_sample_reference": True,
                        }

                # RULE 12: Undertaking Overdue
                elif rule.code == "RULE_UNDERTAKING_OVERDUE":
                    threshold = int(cond.get("value", 0))
                    if days_until_due <= -threshold:
                        days_overdue = abs(days_until_due)
                        results[ut.id] = {
                            "rule_code": rule.code,
                            "entity_type": "UNDERTAKING",
                            "entity_id": ut.id,
                            "entity_label": ut.condition_title,
                            "institution_id": ut.institution_id,
                            "institution_name": ut.institution.name if ut.institution else "",
                            "region_id": ut.institution.region_id if ut.institution else 1,
                            "actual_value": f"{days_overdue} days overdue",
                            "threshold_value": f">= {threshold} days overdue",
                            "why_this_fired": f"Conditional undertaking condition '{ut.condition_title}' is {days_overdue} days overdue ({ut.due_date.isoformat()}) and has not been verified (CALENDAR days basis).{nw_note}",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter III Clause 3.4",
                            "day_basis": "CALENDAR",
                            "non_working_day_note": nw_note.strip() if is_non_working else None,
                            "is_sample_reference": True,
                        }

        return results

    @staticmethod
    def _process_violation(
        db: Session,
        rule: AlertRule,
        entity_id: int,
        meta: Dict[str, Any],
        now: datetime
    ) -> str:
        """
        Deduplicates violations:
        - If an active alert exists: checks if severity or values require upgrade.
        - If none exists: creates a new alert, creates an in-app notification, and queues an outbox email.
        Returns: "NONE", "CREATED", or "UPGRADED"
        """
        # Look for existing open alert for this rule and entity
        filter_kwargs = {
            "alert_rule_id": rule.id,
        }
        if rule.entity_type == "APPLICATION":
            filter_kwargs["application_id"] = entity_id
        elif rule.entity_type == "DOCUMENT":
            filter_kwargs["document_id"] = entity_id
        elif rule.entity_type == "UNDERTAKING":
            filter_kwargs["undertaking_id"] = entity_id

        existing = db.query(Alert).filter_by(**filter_kwargs).filter(
            Alert.status.in_([
                AlertStatusEnum.ACTIVE,
                AlertStatusEnum.ACKNOWLEDGED,
                AlertStatusEnum.SNOOZED,
                AlertStatusEnum.ESCALATED,
            ])
        ).first()

        if existing:
            # Check if severity upgraded (e.g. from MEDIUM to HIGH or HIGH to CRITICAL)
            if rule.severity != existing.severity:
                old_sev = existing.severity
                existing.severity = rule.severity
                existing.explanation_meta = meta
                existing.message = meta["why_this_fired"]

                AuditService.log(
                    db=db,
                    table_name="alerts",
                    record_id=existing.id,
                    action="ALERT_SEVERITY_UPGRADE",
                    old_values={"severity": old_sev.value},
                    new_values={"severity": rule.severity.value, "explanation": meta},
                )
                return "UPGRADED"
            else:
                # Update current actual values without duplicate creation
                existing.explanation_meta = meta
                return "NONE"

        # Determine recipient role and officer
        recipient_user_id, recipient_role = AlertEngine._resolve_recipient(db, rule, meta)

        title = f"{rule.name}: {meta.get('entity_label', 'Regulatory Record')}"
        message = meta["why_this_fired"]

        new_alert = Alert(
            alert_rule_id=rule.id,
            alert_type=rule.alert_type,
            severity=rule.severity,
            status=AlertStatusEnum.ACTIVE,
            application_id=meta["entity_id"] if rule.entity_type == "APPLICATION" else None,
            document_id=meta["entity_id"] if rule.entity_type == "DOCUMENT" else None,
            undertaking_id=meta["entity_id"] if rule.entity_type == "UNDERTAKING" else None,
            institution_id=meta.get("institution_id"),
            recipient_user_id=recipient_user_id,
            recipient_role=recipient_role,
            title=title,
            message=message,
            explanation_meta=meta,
            escalation_tier=1,
            created_at=now,
        )
        db.add(new_alert)
        db.flush()

        # Create in-app notification for the assigned recipient
        if recipient_user_id:
            notif = Notification(
                alert_id=new_alert.id,
                recipient_user_id=recipient_user_id,
                channel=NotificationChannelEnum.IN_APP,
                title=f"[AICTE Alert] {rule.name}",
                body=message,
                is_read=False,
                sent_at=now,
            )
            db.add(notif)

            # Queue outbox email
            recipient_user = db.query(User).filter(User.id == recipient_user_id).first()
            if recipient_user and recipient_user.email:
                EmailService.queue_from_template(
                    db=db,
                    template_code="ALERT_DISPATCH",
                    recipient_email=recipient_user.email,
                    recipient_user_id=recipient_user.id,
                    context={
                        "rule_name": rule.name,
                        "entity_label": meta.get("entity_label", ""),
                        "reason": message,
                        "reference_clause": meta.get("reference_clause", ""),
                    },
                    default_subject=f"[AICTE Regulatory Alert] {rule.name}",
                    default_body=f"Dear Officer,\n\n{message}\n\nRegulatory Citation: {meta.get('reference_clause', '')}\n\nAll India Council for Technical Education",
                    entity_type=rule.entity_type,
                    entity_id=entity_id,
                )

        AuditService.log(
            db=db,
            table_name="alerts",
            record_id=new_alert.id,
            action="ALERT_CREATED",
            new_values={"rule_code": rule.code, "severity": rule.severity.value, "title": title},
        )

        return "CREATED"

    @staticmethod
    def _resolve_recipient(db: Session, rule: AlertRule, meta: Dict[str, Any]) -> Tuple[Optional[int], UserRoleEnum]:
        """
        Determines the L1 officer and role based on region and entity.
        L1 is Scrutiny Officer (or assigned officer).
        """
        region_id = meta.get("region_id", 1)

        # Scrutiny Officer for the region
        officer = db.query(User).filter(
            User.role.has(code="SCRUTINY_OFFICER"),
            User.region_id == region_id,
            User.is_active == True
        ).first()

        if not officer:
            # Fallback to any regional head
            officer = db.query(User).filter(
                User.role.has(code="REGIONAL_HEAD"),
                User.region_id == region_id,
                User.is_active == True
            ).first()

        officer_id = officer.id if officer else None
        role = UserRoleEnum.SCRUTINY_OFFICER
        return officer_id, role

    @classmethod
    def get_summary(cls, db: Session) -> Dict[str, Any]:
        """
        Returns nationwide open alert counts broken down by severity, status, and tier.
        """
        open_alerts = db.query(Alert).filter(
            Alert.status.in_([
                AlertStatusEnum.ACTIVE,
                AlertStatusEnum.ACKNOWLEDGED,
                AlertStatusEnum.SNOOZED,
                AlertStatusEnum.ESCALATED,
            ])
        ).all()

        by_severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "INFO": 0}
        by_status = {"ACTIVE": 0, "ACKNOWLEDGED": 0, "SNOOZED": 0, "ESCALATED": 0}
        by_level = {"L1": 0, "L2": 0, "L3": 0}

        for a in open_alerts:
            sev_val = a.severity.value if hasattr(a.severity, 'value') else str(a.severity)
            by_severity[sev_val] = by_severity.get(sev_val, 0) + 1
            st_val = a.status.value if hasattr(a.status, 'value') else str(a.status)
            by_status[st_val] = by_status.get(st_val, 0) + 1
            tier_key = f"L{a.escalation_tier or 1}"
            by_level[tier_key] = by_level.get(tier_key, 0) + 1

        return {
            "total_open_alerts": len(open_alerts),
            "by_severity": by_severity,
            "by_status": by_status,
            "by_tier": by_level
        }
