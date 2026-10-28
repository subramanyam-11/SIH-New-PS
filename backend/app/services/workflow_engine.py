from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import (
    Application, StageHistory, Stage, StagePath, ApplicationCategory,
    Institution, User, UserRoleEnum, ApplicationStatusEnum, StageStatusEnum,
    SystemConfig, ApplicationCommunication, CommunicationTemplate
)
from app.services.clock import get_system_time, compute_stage_due_date, calculate_sla_status, normalize_dt
from app.services.audit import log_audit_event
from app.services.llm import get_llm_client


def get_config_val(db: Session, key: str, default: Any) -> Any:
    """Helper to fetch a system_config value safely."""
    cfg = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if cfg and cfg.config_value:
        return cfg.config_value
    return default


def get_default_path_for_category(category_code: str) -> str:
    """Standard category-to-path mapping per APH guidelines."""
    mapping = {
        "NEW_INSTITUTE": "PATH_2_SCRUTINY_EVC",
        "EOA": "PATH_1_SCRUTINY_ONLY",
        "INCREASE_INTAKE": "PATH_2_SCRUTINY_EVC",
        "CHANGE_OF_SITE": "PATH_5_FULL_CYCLE",
        "CLOSURE": "PATH_3_EVC_SAC_SHC"
    }
    return mapping.get(category_code, "PATH_1_SCRUTINY_ONLY")


def generate_draft_communication(
    db: Session,
    application: Application,
    template_code: str,
    context: Dict[str, Any]
) -> ApplicationCommunication:
    """
    Renders communication_templates into an editable draft communication.
    The draft is saved with status 'DRAFT' and is never dispatched automatically.
    """
    template = db.query(CommunicationTemplate).filter(CommunicationTemplate.code == template_code).first()
    if not template:
        # Fallback template if missing in DB
        subject = f"[AICTE] Notification regarding {application.application_number}"
        body = f"Notice regarding application {application.application_number} at stage {application.current_stage.name}."
    else:
        subject = template.subject
        body = template.body_template
        for k, v in context.items():
            subject = subject.replace(f"{{{k}}}", str(v))
            body = body.replace(f"{{{k}}}", str(v))

    comm = ApplicationCommunication(
        application_id=application.id,
        template_code=template_code,
        subject=subject,
        body=body,
        recipient_email=application.institution.primary_email,
        status="DRAFT",
        created_at=get_system_time()
    )
    db.add(comm)
    return comm


class WorkflowEngine:
    """
    Transactional state machine driving statutory AICTE application lifecycles.
    Enforces APH path rules, atomic transitions, concurrency safety, and audit logs.
    """

    @staticmethod
    def submit_application(
        db: Session,
        actor: User,
        institution_id: int,
        category_id: int,
        application_number: str,
        stage_path_id: Optional[int] = None,
        academic_year: str = "2026-2027",
        submission_time: Optional[datetime] = None
    ) -> Application:
        """
        Creates and docketizes a new institutional approval application.
        """
        # Validate Institution & Category
        institution = db.query(Institution).filter(Institution.id == institution_id).first()
        if not institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

        # Regional scoping: institution users can only submit for their own institution
        if actor.role.code == UserRoleEnum.INSTITUTION_USER and actor.institution_id != institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit application for another institution")

        category = db.query(ApplicationCategory).filter(ApplicationCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        # Determine Stage Path
        if stage_path_id:
            path = db.query(StagePath).filter(StagePath.id == stage_path_id).first()
        else:
            path_code = get_default_path_for_category(category.code)
            path = db.query(StagePath).filter(StagePath.code == path_code).first()

        if not path:
            path = db.query(StagePath).first()

        # Initial Stage is the first in the path sequence (typically 'SUBMITTED')
        first_stage_code = path.stage_sequence[0] if path.stage_sequence else "SUBMITTED"
        initial_stage = db.query(Stage).filter(Stage.code == first_stage_code).first()
        if not initial_stage:
            initial_stage = db.query(Stage).filter(Stage.code == "SUBMITTED").first()

        now = normalize_dt(submission_time or get_system_time())
        stage_due_date = compute_stage_due_date(now, initial_stage.default_sla_days)

        application = Application(
            application_number=application_number,
            academic_year=academic_year,
            institution_id=institution.id,
            category_id=category.id,
            stage_path_id=path.id,
            current_stage_id=initial_stage.id,
            status=ApplicationStatusEnum.IN_PROGRESS,
            region_id=institution.region_id,
            stage_entered_at=now,
            stage_due_date=stage_due_date,
            revert_count=0,
            created_at=now,
            updated_at=now
        )
        db.add(application)
        db.flush()

        # Record Initial Stage History
        history = StageHistory(
            application_id=application.id,
            from_stage_id=None,
            to_stage_id=initial_stage.id,
            action_taken="SUBMIT",
            actor_id=actor.id,
            status=StageStatusEnum.IN_PROGRESS,
            reason="Initial application dossier submission and statutory docketing",
            entered_at=now,
            completed_at=None,
            duration_hours=0.0
        )
        db.add(history)

        # Generate Draft Routine Communication (Application Docketed)
        generate_draft_communication(
            db=db,
            application=application,
            template_code="APP_SUBMITTED",
            context={
                "application_number": application.application_number,
                "academic_year": application.academic_year,
                "path_name": path.name,
                "current_stage": initial_stage.name,
                "sla_days": initial_stage.default_sla_days
            }
        )

        # Generate Baseline E-Case Summary via Fallback Service
        llm = get_llm_client()
        summary_payload = llm.generate_case_summary({
            "application_number": application.application_number,
            "institution_name": institution.name,
            "current_stage": initial_stage.name,
            "category": category.title,
            "revert_count": 0
        })

        # Save to case_summaries
        from app.models import CaseSummary
        case_summary = CaseSummary(
            application_id=application.id,
            executive_summary=summary_payload["executive_summary"],
            key_findings=summary_payload["key_findings"],
            compliance_flags=summary_payload["compliance_flags"],
            risk_assessment=summary_payload["risk_assessment"],
            generated_by="AI_ASSISTANT",
            last_generated_at=now
        )
        db.add(case_summary)

        # Audit Log
        log_audit_event(
            db=db,
            table_name="applications",
            record_id=application.id,
            action="SUBMIT_APPLICATION",
            actor_id=actor.id,
            new_values={"application_number": application_number, "stage": initial_stage.code}
        )

        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def complete_stage(
        db: Session,
        application_id: int,
        actor: User,
        remarks: Optional[str] = None,
        transition_time: Optional[datetime] = None
    ) -> Tuple[Application, Stage]:
        """
        Validates actor permissions and advances the application to the next statutory stage.
        Uses PostgreSQL row-locking to ensure strict concurrency safety.
        """
        now = normalize_dt(transition_time or get_system_time())

        # 1. Acquire row lock to prevent concurrent double-transitions
        application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        if application.status != ApplicationStatusEnum.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition closed application. Current status is {application.status.value}"
            )

        current_stage = application.current_stage
        user_role = actor.role.code

        # 2. Permission & Scope Check
        # Regional Heads and Admins have supervisory override in their jurisdiction
        is_admin = (user_role == UserRoleEnum.ADMIN)
        is_competent_authority = (user_role == UserRoleEnum.COMPETENT_AUTHORITY)
        is_regional_head = (user_role == UserRoleEnum.REGIONAL_HEAD and actor.region_id == application.region_id)
        is_responsible_role = (user_role == current_stage.responsible_role)

        # Institution users can only complete stage when in RE_SCRUTINY (submitting clarification)
        if current_stage.code == "RE_SCRUTINY":
            if user_role != UserRoleEnum.INSTITUTION_USER and not is_admin and not is_regional_head:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the applicant institution can submit deficiency clarifications for Re-Scrutiny"
                )
            if user_role == UserRoleEnum.INSTITUTION_USER and actor.institution_id != application.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only submit clarifications for your own institution"
                )
        else:
            # Regional scoping check for staff roles
            if user_role in [UserRoleEnum.SCRUTINY_OFFICER, UserRoleEnum.EVC_COORDINATOR, UserRoleEnum.REGIONAL_HEAD]:
                if actor.region_id and actor.region_id != application.region_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied. Application belongs to a different regional office jurisdiction."
                    )
            
            if not (is_responsible_role or is_regional_head or is_admin or is_competent_authority):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{user_role.value}' is not authorized to complete stage '{current_stage.name}'. Required: {current_stage.responsible_role.value}"
                )

        # 3. Determine the Next Stage
        path = application.stage_path
        sequence = path.stage_sequence

        if current_stage.code == "RE_SCRUTINY":
            # Re-scrutiny clarification always returns to SCRUTINY for desk re-evaluation
            next_stage_code = "SCRUTINY"
        else:
            try:
                current_idx = sequence.index(current_stage.code)
            except ValueError:
                current_idx = -1

            if current_idx >= 0 and current_idx + 1 < len(sequence):
                next_stage_code = sequence[current_idx + 1]
                # RE_SCRUTINY is a deficiency loop; forward completion from SCRUTINY skips to the next statutory stage
                if next_stage_code == "RE_SCRUTINY":
                    if current_idx + 2 < len(sequence):
                        next_stage_code = sequence[current_idx + 2]
                    else:
                        next_stage_code = "APPROVAL_GRANTED"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Application has reached the end of pathway sequence. Use /decision to record statutory approval/rejection."
                )

        # Statutory Rule: Final approval or rejection must be recorded via record_decision, not complete_stage
        if next_stage_code in ["APPROVAL_GRANTED", "APPROVAL_REJECTED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Final statutory decision cannot be automated. An authorized Competent Authority must record the decision via /decision."
            )

        next_stage = db.query(Stage).filter(Stage.code == next_stage_code).first()
        if not next_stage:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Target stage '{next_stage_code}' not found in database")

        # 4. Calculate Stage Dwell Time
        duration_hours = max(0.1, round((now - normalize_dt(application.stage_entered_at)).total_seconds() / 3600.0, 2))

        # Close current stage history
        open_history = db.query(StageHistory).filter(
            StageHistory.application_id == application.id,
            StageHistory.to_stage_id == current_stage.id,
            StageHistory.completed_at == None
        ).order_by(StageHistory.id.desc()).first()

        if open_history:
            open_history.completed_at = now
            open_history.duration_hours = duration_hours
            open_history.status = StageStatusEnum.COMPLETED

        # 5. Apply State Update
        application.current_stage_id = next_stage.id
        application.stage_entered_at = now
        application.stage_due_date = compute_stage_due_date(now, next_stage.default_sla_days)
        application.updated_at = now

        # Create New Stage History Entry
        new_history = StageHistory(
            application_id=application.id,
            from_stage_id=current_stage.id,
            to_stage_id=next_stage.id,
            action_taken="ADVANCE",
            actor_id=actor.id,
            status=StageStatusEnum.IN_PROGRESS,
            reason=remarks or f"Stage '{current_stage.name}' completed and advanced to '{next_stage.name}'",
            entered_at=now,
            completed_at=None,
            duration_hours=0.0
        )
        db.add(new_history)

        # 6. Generate Draft Routine Communication
        comm_template = "EVC_INTIMATION" if next_stage.code == "EVC_PENDING" else "STAGE_ADVANCED"
        generate_draft_communication(
            db=db,
            application=application,
            template_code=comm_template,
            context={
                "application_number": application.application_number,
                "institution_name": application.institution.name,
                "from_stage": current_stage.name,
                "to_stage": next_stage.name,
                "sla_days": next_stage.default_sla_days,
                "responsible_role": next_stage.responsible_role.value
            }
        )

        # Audit Log
        log_audit_event(
            db=db,
            table_name="applications",
            record_id=application.id,
            action="ADVANCE_STAGE",
            actor_id=actor.id,
            old_values={"stage": current_stage.code},
            new_values={"stage": next_stage.code, "due_date": application.stage_due_date.isoformat()}
        )

        db.commit()
        db.refresh(application)
        return application, next_stage

    @staticmethod
    def return_application(
        db: Session,
        application_id: int,
        actor: User,
        deficiency_tags: List[str],
        reason: str,
        revert_time: Optional[datetime] = None
    ) -> Application:
        """
        Reverts an application to RE_SCRUTINY due to statutory deficiencies.
        Enforces mandatory tags, free-text remark, and configurable revert cap.
        """
        now = normalize_dt(revert_time or get_system_time())

        # 1. Row Lock
        application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        if application.status != ApplicationStatusEnum.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot revert a closed application.")

        # 2. Permission Check
        user_role = actor.role.code
        allowed_roles = [UserRoleEnum.SCRUTINY_OFFICER, UserRoleEnum.REGIONAL_HEAD, UserRoleEnum.ADMIN]
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role.value}' is not authorized to revert applications."
            )

        if actor.region_id and actor.region_id != application.region_id and user_role != UserRoleEnum.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Application belongs to a different regional office."
            )

        # 3. Deficiency Tag Validation
        if not deficiency_tags or len(deficiency_tags) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one statutory deficiency tag is mandatory to revert an application."
            )

        # Free-text remark validation
        if not reason or len(reason.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Detailed written remarks explaining the deficiency grounds are strictly mandatory."
            )

        if "DEF_OTHER" in deficiency_tags and len(reason.strip()) < 15:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="DEF_OTHER requires a specific, comprehensive explanation in the remarks field."
            )

        # 4. Configurable Revert Cap Check
        revert_cap_cfg = get_config_val(db, "max_revert_cycles", {"limit": 2})
        max_reverts = int(revert_cap_cfg.get("limit", 2))

        if application.revert_count >= max_reverts:
            application.escalation_required = True
            application.escalation_reason = (
                f"Statutory clarification limit exceeded ({max_reverts} cycles). "
                f"Flagged for mandatory Regional Head intervention under APH Clause 2.5."
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Statutory revert cap ({max_reverts} cycles) exceeded. Application has been flagged as 'ESCALATION REQUIRED' for Regional Head intervention."
            )

        # 5. Transition to RE_SCRUTINY
        current_stage = application.current_stage
        re_scrutiny_stage = db.query(Stage).filter(Stage.code == "RE_SCRUTINY").first()
        if not re_scrutiny_stage:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stage 'RE_SCRUTINY' not found")

        duration_hours = max(0.1, round((now - normalize_dt(application.stage_entered_at)).total_seconds() / 3600.0, 2))

        # Close open history
        open_history = db.query(StageHistory).filter(
            StageHistory.application_id == application.id,
            StageHistory.to_stage_id == current_stage.id,
            StageHistory.completed_at == None
        ).order_by(StageHistory.id.desc()).first()

        if open_history:
            open_history.completed_at = now
            open_history.duration_hours = duration_hours
            open_history.status = StageStatusEnum.REVERTED

        # Update Application
        application.current_stage_id = re_scrutiny_stage.id
        application.revert_count += 1
        application.stage_entered_at = now
        application.stage_due_date = compute_stage_due_date(now, re_scrutiny_stage.default_sla_days)
        application.updated_at = now

        # Add Revert History
        revert_history = StageHistory(
            application_id=application.id,
            from_stage_id=current_stage.id,
            to_stage_id=re_scrutiny_stage.id,
            action_taken="REVERT",
            actor_id=actor.id,
            status=StageStatusEnum.IN_PROGRESS,
            reason=reason,
            deficiency_tags=deficiency_tags,
            entered_at=now,
            completed_at=None,
            duration_hours=0.0
        )
        db.add(revert_history)

        # 6. Generate Draft Deficiency Notice Communication
        generate_draft_communication(
            db=db,
            application=application,
            template_code="DEFICIENCY_NOTICE",
            context={
                "application_number": application.application_number,
                "deficiency_tags": ", ".join(deficiency_tags),
                "remarks": reason,
                "clarification_limit_days": re_scrutiny_stage.default_sla_days
            }
        )

        # Audit Log
        log_audit_event(
            db=db,
            table_name="applications",
            record_id=application.id,
            action="REVERT_APPLICATION",
            actor_id=actor.id,
            new_values={
                "revert_count": application.revert_count,
                "deficiency_tags": deficiency_tags,
                "reason": reason
            }
        )

        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def record_decision(
        db: Session,
        application_id: int,
        actor: User,
        decision: str,  # 'APPROVE' or 'REJECT'
        remarks: str,
        decision_time: Optional[datetime] = None
    ) -> Application:
        """
        Statutory decision rendering by Competent Authority.
        The system never decides; an authorized human records the decision.
        """
        now = normalize_dt(decision_time or get_system_time())

        # 1. Row Lock
        application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        if application.status != ApplicationStatusEnum.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application is already closed.")

        # 2. Authorization
        user_role = actor.role.code
        if user_role not in [UserRoleEnum.COMPETENT_AUTHORITY, UserRoleEnum.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the Competent Authority (Senior Council Management) is authorized to render final statutory decisions."
            )

        if not remarks or len(remarks.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Statutory justification remarks are mandatory for final decision recording."
            )

        decision_upper = decision.upper()
        current_stage = application.current_stage
        duration_hours = max(0.1, round((now - normalize_dt(application.stage_entered_at)).total_seconds() / 3600.0, 2))

        # Close open history
        open_history = db.query(StageHistory).filter(
            StageHistory.application_id == application.id,
            StageHistory.to_stage_id == current_stage.id,
            StageHistory.completed_at == None
        ).order_by(StageHistory.id.desc()).first()

        if open_history:
            open_history.completed_at = now
            open_history.duration_hours = duration_hours
            open_history.status = StageStatusEnum.COMPLETED

        if decision_upper == "APPROVE":
            target_stage = db.query(Stage).filter(Stage.code == "APPROVAL_GRANTED").first()
            application.status = ApplicationStatusEnum.APPROVED
            
            # Generate Sample Letter of Approval
            ref_number = f"AICTE/APH-2026/LOA-{application.id:05d}"
            letter_data = {
                "letter_type": "Letter of Approval (Extension of Approval)",
                "reference_number": ref_number,
                "academic_year": application.academic_year,
                "institution_name": application.institution.name,
                "aicte_permanent_id": application.institution.aicte_id,
                "category": application.category.title,
                "region": application.region.name,
                "issued_by_name": actor.full_name,
                "issued_by_role": "Member Secretary / Competent Authority",
                "issuance_timestamp": now.strftime("%d-%b-%Y %H:%M:%S UTC"),
                "remarks": remarks,
                "watermark": "SAMPLE - SYNTHETIC DEMO DOCUMENT, NOT AN OFFICIAL AICTE ORDER",
                "statutory_clauses": [
                    "Approved under AICTE Approval Process Handbook (APH 2026-27), Chapter II.",
                    "Subject to compliance of mandatory conditional undertakings and document validity."
                ]
            }
            application.approval_letter_ref = ref_number
            application.approval_letter_data = letter_data

        elif decision_upper == "REJECT":
            target_stage = db.query(Stage).filter(Stage.code == "APPROVAL_REJECTED").first()
            application.status = ApplicationStatusEnum.REJECTED
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be 'APPROVE' or 'REJECT'")

        application.current_stage_id = target_stage.id
        application.stage_entered_at = now
        application.updated_at = now

        # Add History
        decision_history = StageHistory(
            application_id=application.id,
            from_stage_id=current_stage.id,
            to_stage_id=target_stage.id,
            action_taken=f"DECISION_{decision_upper}",
            actor_id=actor.id,
            status=StageStatusEnum.COMPLETED,
            reason=remarks,
            entered_at=now,
            completed_at=now,
            duration_hours=0.0
        )
        db.add(decision_history)

        # Draft Routine Communication
        generate_draft_communication(
            db=db,
            application=application,
            template_code="APPROVAL_ORDER",
            context={
                "application_number": application.application_number,
                "category": application.category.title,
                "decision_status": "APPROVED" if decision_upper == "APPROVE" else "REJECTED",
                "approval_letter_ref": application.approval_letter_ref or "N/A (Rejected)",
                "issued_at": now.strftime("%d-%b-%Y")
            }
        )

        # Audit Log
        log_audit_event(
            db=db,
            table_name="applications",
            record_id=application.id,
            action=f"DECISION_{decision_upper}",
            actor_id=actor.id,
            new_values={
                "decision": decision_upper,
                "stage": target_stage.code,
                "status": application.status.value,
                "approval_ref": application.approval_letter_ref
            }
        )

        db.commit()
        db.refresh(application)
        return application
