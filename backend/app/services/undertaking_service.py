"""
Undertaking Compliance & Verification Service for SIH26262.
Handles multi-file evidence upload, Scrutiny Officer regional verification,
Regional Head override, and automated Competent Authority escalation.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import (
    Undertaking, UndertakingStatusEnum, UndertakingEvidence, UndertakingHistory,
    User, UserRoleEnum, SystemConfig, Alert, AlertStatusEnum, Application, Institution
)
from app.services.clock import ClockService
from app.services.audit import AuditService
from app.services.email_service import EmailService


class UndertakingService:
    @staticmethod
    def get_escalation_thresholds(db: Session) -> Dict[str, int]:
        overdue_cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "undertaking_overdue_escalation_days").first()
        rejection_cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "undertaking_rejection_escalation_count").first()
        
        overdue_days = 7
        if overdue_cfg and isinstance(overdue_cfg.config_value, (int, str)):
            try:
                overdue_days = int(overdue_cfg.config_value)
            except ValueError:
                pass

        max_rejections = 2
        if rejection_cfg and isinstance(rejection_cfg.config_value, (int, str)):
            try:
                max_rejections = int(rejection_cfg.config_value)
            except ValueError:
                pass

        return {"overdue_days": overdue_days, "max_rejections": max_rejections}

    @staticmethod
    def submit_evidence(
        db: Session,
        undertaking_id: int,
        file_name: str,
        file_url: str,
        file_id: Optional[int],
        comments: Optional[str],
        actor: User
    ) -> UndertakingEvidence:
        """
        Uploads compliance evidence. Transitions undertaking status: PENDING/REJECTED/NEEDS_MORE_EVIDENCE -> SUBMITTED
        """
        ut = db.query(Undertaking).filter(Undertaking.id == undertaking_id).first()
        if not ut:
            raise HTTPException(status_code=404, detail="Undertaking not found")

        # Institution scoping
        if actor.role.code == "INSTITUTION_USER" and ut.institution_id != actor.institution_id:
            raise HTTPException(status_code=403, detail="Cannot upload evidence for another institution's undertaking")

        evidence = UndertakingEvidence(
            undertaking_id=ut.id,
            submitted_by=actor.id,
            file_name=file_name,
            file_url=file_url,
            file_id=file_id,
            comments=comments,
            submitted_at=ClockService.get_now(),
        )
        db.add(evidence)

        old_status = ut.status.value
        ut.status = UndertakingStatusEnum.SUBMITTED

        # Record history
        history = UndertakingHistory(
            undertaking_id=ut.id,
            from_status=old_status,
            to_status=UndertakingStatusEnum.SUBMITTED.value,
            action_by=actor.id,
            action_role=actor.role.code if actor.role else "USER",
            remarks=f"Evidence artifact '{file_name}' uploaded with remarks: {comments or 'None'}",
            created_at=ClockService.get_now(),
        )
        db.add(history)

        AuditService.log(
            db=db,
            table_name="undertakings",
            record_id=ut.id,
            action="UNDERTAKING_EVIDENCE_SUBMITTED",
            actor_id=actor.id,
            new_values={"file_name": file_name, "status": "SUBMITTED"},
        )

        db.commit()
        db.refresh(evidence)
        return evidence

    @staticmethod
    def verify_undertaking(
        db: Session,
        undertaking_id: int,
        decision: str,  # "VERIFIED", "REJECTED", "NEEDS_MORE_EVIDENCE"
        remarks: str,
        actor: User
    ) -> Undertaking:
        """
        Scrutiny Officer verification of evidence.
        Regional Head can override.
        Competent Authority only reviews escalated items.
        """
        role_code = actor.role.code if actor.role else ""
        if role_code not in ["ADMIN", "REGIONAL_HEAD", "SCRUTINY_OFFICER", "COMPETENT_AUTHORITY"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institution users cannot verify undertakings. Only authorized scrutiny officers or regional heads can verify compliance evidence.",
            )

        if not remarks or len(remarks.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Substantive verification remarks (at least 5 characters) are mandatory.",
            )

        ut = db.query(Undertaking).filter(Undertaking.id == undertaking_id).first()
        if not ut:
            raise HTTPException(status_code=404, detail="Undertaking not found")

        old_status = ut.status.value
        now = ClockService.get_now()
        thresholds = UndertakingService.get_escalation_thresholds(db)

        if decision == "VERIFIED":
            ut.status = UndertakingStatusEnum.VERIFIED
            ut.verified_at = now
            ut.assigned_verifier_id = actor.id
            ut.verification_remarks = remarks

            # Auto-resolve linked undertaking alerts
            alerts = db.query(Alert).filter(
                Alert.undertaking_id == ut.id,
                Alert.status != AlertStatusEnum.RESOLVED
            ).all()
            for alt in alerts:
                alt.status = AlertStatusEnum.RESOLVED
                alt.resolved_at = now
                alt.resolved_by = actor.id
                alt.resolution_remarks = f"Undertaking verified and complied by Officer {actor.full_name}: {remarks}"

        elif decision == "REJECTED":
            ut.status = UndertakingStatusEnum.REJECTED
            ut.rejection_count += 1
            ut.verification_remarks = remarks

            # Check if rejection count triggers escalation to Competent Authority
            if ut.rejection_count >= thresholds["max_rejections"]:
                ut.status = UndertakingStatusEnum.ESCALATED
                ut.escalated_to_tier = 3 # Competent Authority
                ut.escalation_reason = f"Rejected {ut.rejection_count} times by scrutiny desk. Escalated for Competent Authority determination."

                # Notify institution of escalation
                inst = ut.institution
                if inst and inst.primary_email:
                    EmailService.queue_from_template(
                        db=db,
                        template_code="UNDERTAKING_ESCALATED",
                        recipient_email=inst.primary_email,
                        recipient_user_id=None,
                        context={"condition_title": ut.condition_title, "rejection_count": ut.rejection_count, "remarks": remarks},
                        default_subject=f"[AICTE URGENT] Undertaking Escalated to Competent Authority: {ut.condition_title}",
                        default_body=f"Dear Head of Institution,\n\nUndertaking '{ut.condition_title}' has been rejected {ut.rejection_count} times and is escalated to the Competent Authority.\nReason: {remarks}\n\nCouncil Secretariat, AICTE",
                        entity_type="UNDERTAKING",
                        entity_id=ut.id,
                    )

        elif decision == "NEEDS_MORE_EVIDENCE":
            ut.status = UndertakingStatusEnum.NEEDS_MORE_EVIDENCE
            ut.verification_remarks = remarks

        else:
            raise HTTPException(status_code=400, detail=f"Invalid verification decision: {decision}")

        # Record history
        history = UndertakingHistory(
            undertaking_id=ut.id,
            from_status=old_status,
            to_status=ut.status.value,
            action_by=actor.id,
            action_role=role_code,
            remarks=remarks,
            created_at=now,
        )
        db.add(history)

        AuditService.log(
            db=db,
            table_name="undertakings",
            record_id=ut.id,
            action="UNDERTAKING_VERIFIED",
            actor_id=actor.id,
            new_values={"decision": decision, "status": ut.status.value, "remarks": remarks},
        )

        db.commit()
        db.refresh(ut)
        return ut
