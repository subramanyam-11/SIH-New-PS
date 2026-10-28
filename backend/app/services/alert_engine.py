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

        # -------------------------------------------------------------------------
        # DOCUMENT RULES
        # -------------------------------------------------------------------------
        elif rule.entity_type == "DOCUMENT":
            active_docs = db.query(Document).filter(
                Document.status.notin_([DocumentStatusEnum.SUPERSEDED, DocumentStatusEnum.RENEWAL_SUBMITTED])
            ).all()

            for doc in active_docs:
                days_until_expiry = (doc.expiry_date - now_date).days
                region_id = doc.institution.region_id if doc.institution else None
                is_non_working, nw_reason = WorkingDayService.is_holiday_or_weekend(db, doc.expiry_date, region_id)
                nw_note = f" Note: Expiry date falls on a {nw_reason}; manual verification deferred to next working day." if is_non_working else ""

                # RULE 4: Lease 90D Warning
                if rule.code == "RULE_LEASE_90D":
                    threshold = int(cond.get("value", 90))
                    if 30 < days_until_expiry <= threshold:
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
                    if 0 < days_until_expiry <= threshold:
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

                # RULE 6: Fire NOC or Document Expired
                elif rule.code == "RULE_FIRE_NOC_EXPIRED":
                    if days_until_expiry <= 0:
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
                    if days_until_due <= threshold:
                        actual_str = f"{days_until_due} days remaining" if days_until_due >= 0 else f"{abs(days_until_due)} days overdue"
                        results[ut.id] = {
                            "rule_code": rule.code,
                            "entity_type": "UNDERTAKING",
                            "entity_id": ut.id,
                            "entity_label": ut.condition_title,
                            "institution_id": ut.institution_id,
                            "institution_name": ut.institution.name if ut.institution else "",
                            "region_id": ut.institution.region_id if ut.institution else 1,
                            "actual_value": actual_str,
                            "threshold_value": f"<= {threshold} days",
                            "why_this_fired": f"Undertaking condition '{ut.condition_title}' is due in {days_until_due} days ({ut.due_date.isoformat()}) on CALENDAR days basis.{nw_note}",
                            "reference_clause": rule.aph_reference_clause or "APH 2026 Chapter III Clause 3.2",
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
