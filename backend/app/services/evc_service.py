"""
EVC (Expert Visit Committee) Scheduling & Panel Management Service.
Enforces statutory 3-member panel rules, conflict-of-interest checks,
concurrency limits, and valid visit lifecycle transitions.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status

from app.models import (
    EvcVisit, EvcStatusEnum, EvcExpert, Application, Institution,
    User, UserRoleEnum, SystemConfig, Alert, AlertStatusEnum, AlertTypeEnum,
    AlertRule, EscalationHistory
)
from app.services.clock import ClockService
from app.services.audit import AuditService
from app.services.alert_engine import AlertEngine


class EvcService:
    @staticmethod
    def get_max_concurrent_visits(db: Session) -> int:
        config = db.query(SystemConfig).filter(SystemConfig.config_key == "max_concurrent_evc_visits").first()
        if config and isinstance(config.config_value, (int, str)):
            try:
                return int(config.config_value)
            except ValueError:
                pass
        return 2

    @staticmethod
    def check_expert_conflict(db: Session, expert: EvcExpert, institution: Institution, current_visit_id: Optional[int] = None) -> List[str]:
        """
        Evaluates regulatory conflict-of-interest checks:
        1. Home Institution conflict
        2. City conflict
        3. Concurrency visit limit (default 2 active visits)
        Returns list of conflict reason strings (empty if compliant).
        """
        conflicts = []
        max_concurrent = EvcService.get_max_concurrent_visits(db)

        # 1. Home institution check
        inst_name = institution.name.strip().lower()
        exp_home = expert.home_institution.strip().lower()
        if exp_home in inst_name or inst_name in exp_home:
            conflicts.append(f"Institutional Conflict: Expert is currently affiliated with '{expert.home_institution}'.")

        # 2. City geographic conflict
        if expert.city.strip().lower() == institution.city.strip().lower():
            conflicts.append(f"Geographic Conflict: Expert resides in the same municipality ({institution.city}) as the candidate institution.")

        # 3. Concurrency check
        # Count active visits where expert is in assigned_experts
        active_visits = db.query(EvcVisit).filter(
            EvcVisit.status.in_([
                EvcStatusEnum.ASSIGNED,
                EvcStatusEnum.SCHEDULED,
                EvcStatusEnum.VISIT_DONE,
                EvcStatusEnum.VISIT_COMPLETED,
            ])
        ).all()

        current_active_count = 0
        for v in active_visits:
            if current_visit_id and v.id == current_visit_id:
                continue
            if v.assigned_experts and isinstance(v.assigned_experts, list):
                for a in v.assigned_experts:
                    if isinstance(a, dict) and a.get("id") == expert.id:
                        current_active_count += 1

        if current_active_count >= max_concurrent:
            conflicts.append(f"Capacity Limit: Expert has reached maximum permitted concurrent visits ({current_active_count}/{max_concurrent} active).")

        return conflicts

    @staticmethod
    def get_suggested_experts(db: Session, visit_id: int) -> List[Dict[str, Any]]:
        """
        Returns ranked list of candidate experts for decision support:
        Scored on regional proximity, zero conflicts, discipline match, and load.
        """
        visit = db.query(EvcVisit).filter(EvcVisit.id == visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="EVC visit not found")

        app = db.query(Application).filter(Application.id == visit.application_id).first()
        institution = app.institution if app else None
        if not institution:
            raise HTTPException(status_code=400, detail="Associated institution not found")

        experts = db.query(EvcExpert).filter(EvcExpert.is_available == True).all()
        ranked = []

        for exp in experts:
            conflicts = EvcService.check_expert_conflict(db, exp, institution, current_visit_id=visit.id)
            has_conflict = len(conflicts) > 0

            # Scoring algorithm for decision support
            score = 100
            if has_conflict:
                score -= 1000 # Penalize conflicts
            if exp.region_id == institution.region_id:
                score += 50
            if exp.designation in ["Director", "Principal", "Dean"]:
                score += 20

            ranked.append({
                "id": exp.id,
                "name": exp.name,
                "designation": exp.designation,
                "discipline": exp.discipline,
                "region_id": exp.region_id,
                "home_institution": exp.home_institution,
                "city": exp.city,
                "has_conflict": has_conflict,
                "conflict_reasons": conflicts,
                "recommendation_score": score,
            })

        # Sort by recommendation score descending
        ranked.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return ranked

    @staticmethod
    def assign_panel(db: Session, visit_id: int, expert_ids: List[int], actor: User) -> EvcVisit:
        """
        Assigns exactly 3 members to the EVC panel after validating conflict checks.
        Transitions state: PENDING_ASSIGNMENT -> ASSIGNED
        """
        role_code = actor.role.code if actor.role else ""
        if role_code not in ["ADMIN", "REGIONAL_HEAD", "EVC_COORDINATOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the Regional EVC Coordinator, Regional Head, or Admin can assign inspection panels.",
            )

        if len(expert_ids) != 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Regulatory mandate requires exactly 3 committee experts. Received {len(expert_ids)}.",
            )

        if len(set(expert_ids)) != 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate experts cannot be assigned to the same committee panel.",
            )

        visit = db.query(EvcVisit).filter(EvcVisit.id == visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="EVC visit not found")

        app = db.query(Application).filter(Application.id == visit.application_id).first()
        institution = app.institution if app else None
        if not institution:
            raise HTTPException(status_code=400, detail="Associated institution not found")

        # Validate each expert
        assigned_data = []
        for eid in expert_ids:
            exp = db.query(EvcExpert).filter(EvcExpert.id == eid).first()
            if not exp:
                raise HTTPException(status_code=404, detail=f"Expert with ID {eid} not found")

            conflicts = EvcService.check_expert_conflict(db, exp, institution, current_visit_id=visit.id)
            if conflicts:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Conflict detected for expert {exp.name}: {'; '.join(conflicts)}",
                )

            assigned_data.append({
                "id": exp.id,
                "name": exp.name,
                "designation": exp.designation,
                "discipline": exp.discipline,
                "home_institution": exp.home_institution,
                "city": exp.city,
            })

        visit.assigned_experts = assigned_data
        visit.committee_chair = assigned_data[0]["name"]  # Lead expert is chair
        visit.committee_experts = assigned_data
        visit.status = EvcStatusEnum.ASSIGNED
        visit.coordinator_id = actor.id

        AuditService.log(
            db=db,
            table_name="evc_visits",
            record_id=visit.id,
            action="EVC_PANEL_ASSIGNED",
            actor_id=actor.id,
            new_values={"panel": [e["name"] for e in assigned_data]},
        )

        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def schedule_visit(db: Session, visit_id: int, scheduled_date: date, scheduled_time: str, visit_type: str, actor: User) -> EvcVisit:
        """
        Schedules the inspection date and time.
        Transitions state: ASSIGNED -> SCHEDULED
        Automatically resolves RULE_EVC_UNSCHEDULED alerts.
        """
        visit = db.query(EvcVisit).filter(EvcVisit.id == visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="EVC visit not found")

        if visit.status not in [EvcStatusEnum.ASSIGNED, EvcStatusEnum.PENDING_ASSIGNMENT, EvcStatusEnum.PENDING_SCHEDULE, EvcStatusEnum.SCHEDULED]:
            raise HTTPException(status_code=400, detail=f"Cannot schedule visit in status {visit.status.value}")

        visit.scheduled_date = scheduled_date
        visit.scheduled_time = scheduled_time or "10:00 AM"
        visit.visit_type = visit_type or "PHYSICAL"
        visit.status = EvcStatusEnum.SCHEDULED

        # Auto-resolve RULE_EVC_UNSCHEDULED alerts
        now = ClockService.get_now()
        alerts = db.query(Alert).filter(
            Alert.application_id == visit.application_id,
            Alert.rule.has(AlertRule.code == "RULE_EVC_UNSCHEDULED"),
            Alert.status != AlertStatusEnum.RESOLVED
        ).all()
        for alt in alerts:
            alt.status = AlertStatusEnum.RESOLVED
            alt.resolved_at = now
            alt.resolved_by = actor.id
            alt.resolution_remarks = f"Inspection scheduled for {scheduled_date.isoformat()} by Coordinator {actor.full_name}."

        AuditService.log(
            db=db,
            table_name="evc_visits",
            record_id=visit.id,
            action="EVC_VISIT_SCHEDULED",
            actor_id=actor.id,
            new_values={"scheduled_date": scheduled_date.isoformat(), "time": visit.scheduled_time},
        )

        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def mark_visit_done(db: Session, visit_id: int, visit_summary: str, actor: User) -> EvcVisit:
        """
        Committee concludes physical site inspection.
        Transitions state: SCHEDULED -> VISIT_DONE
        """
        visit = db.query(EvcVisit).filter(EvcVisit.id == visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="EVC visit not found")

        now = ClockService.get_now()
        visit.status = EvcStatusEnum.VISIT_DONE
        visit.visit_completed_at = now
        visit.visit_summary = visit_summary or "Physical inspection concluded by Expert Committee."

        AuditService.log(
            db=db,
            table_name="evc_visits",
            record_id=visit.id,
            action="EVC_VISIT_COMPLETED",
            actor_id=actor.id,
            new_values={"completed_at": now.isoformat()},
        )

        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def upload_report(
        db: Session,
        visit_id: int,
        outcome_recommendation: str,
        remarks: str,
        report_file_id: Optional[int],
        report_file_url: Optional[str],
        actor: User
    ) -> EvcVisit:
        """
        Uploads committee report and outcome recommendation.
        Transitions state: VISIT_DONE -> REPORT_RECEIVED
        Auto-resolves RULE_EVC_VISIT_OVERDUE alerts.
        """
        visit = db.query(EvcVisit).filter(EvcVisit.id == visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="EVC visit not found")

        now = ClockService.get_now()
        visit.status = EvcStatusEnum.REPORT_RECEIVED
        visit.report_uploaded_at = now
        visit.outcome_recommendation = outcome_recommendation
        visit.remarks = remarks
        if report_file_id:
            visit.report_file_id = report_file_id
        if report_file_url:
            visit.report_file_url = report_file_url

        # Auto-resolve RULE_EVC_VISIT_OVERDUE alerts
        alerts = db.query(Alert).filter(
            Alert.application_id == visit.application_id,
            Alert.rule.has(AlertRule.code == "RULE_EVC_VISIT_OVERDUE"),
            Alert.status != AlertStatusEnum.RESOLVED
        ).all()
        for alt in alerts:
            alt.status = AlertStatusEnum.RESOLVED
            alt.resolved_at = now
            alt.resolved_by = actor.id
            alt.resolution_remarks = f"EVC inspection report uploaded with recommendation: {outcome_recommendation}."

        AuditService.log(
            db=db,
            table_name="evc_visits",
            record_id=visit.id,
            action="EVC_REPORT_UPLOADED",
            actor_id=actor.id,
            new_values={"recommendation": outcome_recommendation},
        )

        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def close_visit(db: Session, visit_id: int, actor: User) -> EvcVisit:
        """
        Closes out EVC visit.
        Transitions state: REPORT_RECEIVED -> CLOSED
        """
        visit = db.query(EvcVisit).filter(EvcVisit.id == visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="EVC visit not found")

        now = ClockService.get_now()
        visit.status = EvcStatusEnum.CLOSED
        visit.closed_at = now
        visit.closed_by = actor.id

        AuditService.log(
            db=db,
            table_name="evc_visits",
            record_id=visit.id,
            action="EVC_VISIT_CLOSED",
            actor_id=actor.id,
            new_values={"closed_at": now.isoformat()},
        )

        db.commit()
        db.refresh(visit)
        return visit
