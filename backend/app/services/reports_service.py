"""
Statutory Reporting & Analytics Service for SIH26262.
Provides 5 database-backed compliance reports, CSV/PDF export generators,
and comprehensive 360-degree Institution Health dossiers.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from io import StringIO, BytesIO
import csv
from sqlalchemy.orm import Session
from sqlalchemy import func
from fpdf import FPDF
from fastapi import HTTPException

from app.models import (
    Application, Stage, StageHistory, EvcVisit, EvcStatusEnum,
    Undertaking, UndertakingStatusEnum, Document, DocumentStatusEnum,
    Region, Institution, Alert, AlertStatusEnum, AlertTypeEnum, AlertRule, User,
    ApplicationStatusEnum
)
from app.services.clock import ClockService, normalize_dt
from app.services.workflow_engine import WorkflowEngine


class ReportsService:
    @staticmethod
    def get_pendency_report(db: Session, region_id: Optional[int] = None, institution_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Pendency and Ageing by stage, region, and officer.
        Includes fair pendency split between WITH_AICTE and WITH_INSTITUTION.
        """
        now = ClockService.get_now()
        query = db.query(Application).filter(Application.status == ApplicationStatusEnum.IN_PROGRESS)
        if region_id:
            query = query.filter(Application.region_id == region_id)
        if institution_id:
            query = query.filter(Application.institution_id == institution_id)

        apps = query.all()

        by_stage: Dict[str, Dict[str, Any]] = {}
        by_region: Dict[str, Dict[str, Any]] = {}
        by_officer: Dict[str, Dict[str, Any]] = {}

        total_pending = len(apps)
        total_overdue = 0
        total_with_aicte = 0
        total_with_institution = 0

        for a in apps:
            stage_name = a.current_stage.name if a.current_stage else "Unknown"
            reg_name = a.region.name if a.region else "Unallocated"
            officer_name = a.assigned_officer.full_name if a.assigned_officer else "Unassigned"

            holder = a.case_holder or "WITH_AICTE"
            if holder == "WITH_INSTITUTION":
                total_with_institution += 1
            else:
                total_with_aicte += 1

            # Fair pendency: days with AICTE for current stage
            pendency = WorkflowEngine.get_application_pendency(db, a)
            days_in_stage = pendency["current_stage_aicte_days"]

            # Overdue counts only if held by AICTE and past due date or stage SLA
            due = normalize_dt(a.stage_due_date) if a.stage_due_date else now
            is_overdue = (holder == "WITH_AICTE" and (now > due or (a.current_stage and days_in_stage > a.current_stage.default_sla_days)))
            if is_overdue:
                total_overdue += 1

            # Group by stage
            if stage_name not in by_stage:
                by_stage[stage_name] = {
                    "count": 0, "total_days": 0.0, "overdue_count": 0,
                    "with_aicte_count": 0, "with_institution_count": 0
                }
            by_stage[stage_name]["count"] += 1
            by_stage[stage_name]["total_days"] += days_in_stage
            if holder == "WITH_INSTITUTION":
                by_stage[stage_name]["with_institution_count"] += 1
            else:
                by_stage[stage_name]["with_aicte_count"] += 1
            if is_overdue:
                by_stage[stage_name]["overdue_count"] += 1

            # Group by region
            if reg_name not in by_region:
                by_region[reg_name] = {
                    "count": 0, "total_days": 0.0, "overdue_count": 0,
                    "with_aicte_count": 0, "with_institution_count": 0
                }
            by_region[reg_name]["count"] += 1
            by_region[reg_name]["total_days"] += days_in_stage
            if holder == "WITH_INSTITUTION":
                by_region[reg_name]["with_institution_count"] += 1
            else:
                by_region[reg_name]["with_aicte_count"] += 1
            if is_overdue:
                by_region[reg_name]["overdue_count"] += 1

            # Group by officer
            if officer_name not in by_officer:
                by_officer[officer_name] = {
                    "count": 0, "total_days": 0.0, "overdue_count": 0,
                    "with_aicte_count": 0, "with_institution_count": 0
                }
            by_officer[officer_name]["count"] += 1
            by_officer[officer_name]["total_days"] += days_in_stage
            if holder == "WITH_INSTITUTION":
                by_officer[officer_name]["with_institution_count"] += 1
            else:
                by_officer[officer_name]["with_aicte_count"] += 1
            if is_overdue:
                by_officer[officer_name]["overdue_count"] += 1

        stage_breakdown = [
            {
                "stage": s,
                "count": data["count"],
                "avg_days": round(data["total_days"] / data["count"], 1) if data["count"] else 0,
                "overdue_count": data["overdue_count"],
                "with_aicte_count": data["with_aicte_count"],
                "with_institution_count": data["with_institution_count"],
            }
            for s, data in by_stage.items()
        ]

        region_breakdown = [
            {
                "region": r,
                "count": data["count"],
                "avg_days": round(data["total_days"] / data["count"], 1) if data["count"] else 0,
                "overdue_count": data["overdue_count"],
                "with_aicte_count": data["with_aicte_count"],
                "with_institution_count": data["with_institution_count"],
            }
            for r, data in by_region.items()
        ]

        officer_breakdown = [
            {
                "officer": o,
                "count": data["count"],
                "avg_days": round(data["total_days"] / data["count"], 1) if data["count"] else 0,
                "overdue_count": data["overdue_count"],
                "with_aicte_count": data["with_aicte_count"],
                "with_institution_count": data["with_institution_count"],
            }
            for o, data in by_officer.items()
        ]

        return {
            "total_pending": total_pending,
            "total_overdue": total_overdue,
            "total_with_aicte": total_with_aicte,
            "total_with_institution": total_with_institution,
            "on_time_count": total_pending - total_overdue,
            "by_stage": stage_breakdown,
            "by_region": region_breakdown,
            "by_officer": officer_breakdown,
        }

    @staticmethod
    def get_evc_status_report(db: Session, region_id: Optional[int] = None) -> Dict[str, Any]:
        """
        EVC status: waiting assignment, scheduled, visit done, report received, average turnaround.
        """
        query = db.query(EvcVisit).join(Application)
        if region_id:
            query = query.filter(Application.region_id == region_id)

        visits = query.all()
        by_status: Dict[str, int] = {}
        completed_days: List[float] = []

        for v in visits:
            st = v.status.value
            by_status[st] = by_status.get(st, 0) + 1

            if v.visit_completed_at and v.created_at:
                c_at = normalize_dt(v.visit_completed_at)
                cr_at = normalize_dt(v.created_at)
                diff = (c_at - cr_at).total_seconds() / 86400.0
                completed_days.append(diff)

        avg_turnaround_days = round(sum(completed_days) / len(completed_days), 1) if completed_days else 0.0

        return {
            "total_visits": len(visits),
            "waiting_assignment": by_status.get("PENDING_ASSIGNMENT", 0) + by_status.get("PENDING_SCHEDULE", 0),
            "scheduled": by_status.get("SCHEDULED", 0) + by_status.get("ASSIGNED", 0),
            "visit_done": by_status.get("VISIT_DONE", 0) + by_status.get("VISIT_COMPLETED", 0),
            "report_received": by_status.get("REPORT_RECEIVED", 0) + by_status.get("REPORT_SUBMITTED", 0),
            "closed": by_status.get("CLOSED", 0),
            "average_turnaround_days": avg_turnaround_days,
            "by_status": [{"status": k, "count": v} for k, v in by_status.items()],
        }

    @staticmethod
    def get_undertaking_compliance_report(db: Session, region_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Undertakings compliance: on-time, submitted, overdue, escalated, verified.
        """
        query = db.query(Undertaking).join(Institution)
        if region_id:
            query = query.filter(Institution.region_id == region_id)

        undertakings = query.all()
        by_status: Dict[str, int] = {}
        now = ClockService.get_now().date()

        overdue_count = 0
        for ut in undertakings:
            st = ut.status.value
            by_status[st] = by_status.get(st, 0) + 1
            if ut.due_date < now and ut.status not in [UndertakingStatusEnum.VERIFIED, UndertakingStatusEnum.COMPLIED]:
                overdue_count += 1

        return {
            "total_undertakings": len(undertakings),
            "verified_count": by_status.get("VERIFIED", 0) + by_status.get("COMPLIED", 0),
            "submitted_count": by_status.get("SUBMITTED", 0),
            "pending_count": by_status.get("PENDING", 0) + by_status.get("PENDING_SUBMISSION", 0),
            "overdue_count": overdue_count,
            "escalated_count": by_status.get("ESCALATED", 0),
            "by_status": [{"status": k, "count": v} for k, v in by_status.items()],
        }

    @staticmethod
    def get_document_validity_report(db: Session, region_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Document validity: valid, expiring, expired, renewal submitted, superseded.
        """
        query = db.query(Document).join(Institution)
        if region_id:
            query = query.filter(Institution.region_id == region_id)

        docs = query.all()
        by_status: Dict[str, int] = {}
        by_type: Dict[str, Dict[str, int]] = {}

        now = ClockService.get_now().date()

        for d in docs:
            st = d.status.value
            dtype = d.document_type.value

            by_status[st] = by_status.get(st, 0) + 1

            if dtype not in by_type:
                by_type[dtype] = {"total": 0, "valid": 0, "expired": 0, "expiring": 0}
            by_type[dtype]["total"] += 1

            if d.expiry_date < now:
                by_type[dtype]["expired"] += 1
            elif (d.expiry_date - now).days <= 30:
                by_type[dtype]["expiring"] += 1
            else:
                by_type[dtype]["valid"] += 1

        return {
            "total_documents": len(docs),
            "valid_count": by_status.get("VALID", 0) + by_status.get("ACTIVE", 0),
            "expired_count": by_status.get("EXPIRED", 0),
            "expiring_soon_count": by_status.get("EXPIRING", 0) + by_status.get("EXPIRING_SOON", 0),
            "renewal_submitted_count": by_status.get("RENEWAL_SUBMITTED", 0),
            "superseded_count": by_status.get("SUPERSEDED", 0),
            "by_status": [{"status": k, "count": v} for k, v in by_status.items()],
            "by_type": [{"type": k, **v} for k, v in by_type.items()],
        }

    @staticmethod
    def get_regional_performance_report(db: Session) -> Dict[str, Any]:
        """
        Regional performance: applications processed, avg days per stage, SLA breach rate %, alerts raised and resolved.
        """
        regions = db.query(Region).order_by(Region.id).all()
        results = []

        for reg in regions:
            apps = db.query(Application).filter(Application.region_id == reg.id).all()
            total_apps = len(apps)

            # Stage transitions duration
            history_rows = db.query(StageHistory).join(Application).filter(
                Application.region_id == reg.id,
                StageHistory.duration_hours != None
            ).all()

            avg_stage_days = 0.0
            if history_rows:
                total_hours = sum(h.duration_hours for h in history_rows if h.duration_hours)
                avg_stage_days = round((total_hours / len(history_rows)) / 24.0, 1)

            # SLA breach rate
            overdue_alerts = db.query(Alert).join(Application).filter(
                Application.region_id == reg.id,
                Alert.rule.has(AlertRule.code.in_(["RULE_SCRUTINY_OVERDUE", "RULE_EVC_VISIT_OVERDUE"]))
            ).count()

            sla_breach_rate = round((overdue_alerts / total_apps * 100), 1) if total_apps else 0.0

            # Alerts raised & resolved
            alerts_raised = db.query(Alert).join(Application).filter(Application.region_id == reg.id).count()
            # Phase 6: Fair pendency holder breakdown and closed cases
            with_aicte_count = db.query(Application).filter(
                Application.region_id == reg.id,
                Application.status == ApplicationStatusEnum.IN_PROGRESS,
                Application.case_holder == "WITH_AICTE"
            ).count()
            with_institution_count = db.query(Application).filter(
                Application.region_id == reg.id,
                Application.status == ApplicationStatusEnum.IN_PROGRESS,
                Application.case_holder == "WITH_INSTITUTION"
            ).count()
            closed_count = db.query(Application).filter(
                Application.region_id == reg.id,
                Application.status == ApplicationStatusEnum.CLOSED
            ).count()

            alerts_resolved = db.query(Alert).join(Application).filter(
                Application.region_id == reg.id,
                Alert.status == AlertStatusEnum.RESOLVED
            ).count()

            results.append({
                "region_id": reg.id,
                "region_name": reg.name,
                "headquarters": reg.headquarters,
                "total_applications": total_apps,
                "with_aicte_count": with_aicte_count,
                "with_institution_count": with_institution_count,
                "closed_count": closed_count,
                "avg_days_per_stage": avg_stage_days or 4.5, # default baseline if fresh
                "sla_breach_rate_pct": sla_breach_rate,
                "alerts_raised": alerts_raised,
                "alerts_resolved": alerts_resolved,
                "resolution_rate_pct": round(alerts_resolved / alerts_raised * 100, 1) if alerts_raised else 100.0,
            })

        return {"regions": results}

    @staticmethod
    def get_overdue_cases_report(
        db: Session,
        region_id: Optional[int] = None,
        institution_id: Optional[int] = None,
        item_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Sixth Statutory Report: Overdue cases & compliance tracking.
        Applications (AICTE-held clock only), EVC visits, undertakings and documents
        that are overdue, with days overdue, who holds the case, officer, region,
        escalation level and linked alert.
        """
        now_dt = ClockService.get_now()
        now_date = now_dt.date()
        raw_items: List[Dict[str, Any]] = []

        # 1. Overdue Applications (AICTE-held clock only)
        app_query = db.query(Application).filter(
            Application.status == ApplicationStatusEnum.IN_PROGRESS,
            Application.case_holder == "WITH_AICTE"
        )
        if region_id:
            app_query = app_query.filter(Application.region_id == region_id)
        if institution_id:
            app_query = app_query.filter(Application.institution_id == institution_id)

        in_prog_apps = app_query.all()
        for a in in_prog_apps:
            pendency = WorkflowEngine.get_application_pendency(db, a)
            due_dt = normalize_dt(a.stage_due_date) if a.stage_due_date else now_dt
            sla_days = a.current_stage.default_sla_days if a.current_stage else 10.0
            dwell_days = pendency["current_stage_aicte_days"]

            is_overdue = (now_dt > due_dt or dwell_days > sla_days)
            if is_overdue:
                days_overdue = max(0.1, round((now_dt - due_dt).total_seconds() / 86400.0, 1))
                linked_alert = db.query(Alert).filter(
                    Alert.application_id == a.id,
                    Alert.status != AlertStatusEnum.RESOLVED
                ).order_by(Alert.severity.desc(), Alert.created_at.desc()).first()

                esc_level = f"TIER_{linked_alert.escalation_tier}" if linked_alert else "NORMAL"
                due_date_val = due_dt.date()

                raw_items.append({
                    "id": f"APP-{a.id}",
                    "item_type": "APPLICATION",
                    "reference_no": a.application_number,
                    "title": f"{a.category.title if a.category else 'Application'} - {a.current_stage.name if a.current_stage else 'In Progress'}",
                    "institution_id": a.institution_id,
                    "institution_name": a.institution.name if a.institution else "-",
                    "region_id": a.region_id,
                    "region_name": a.region.name if a.region else "-",
                    "assigned_officer": a.assigned_officer.full_name if a.assigned_officer else "Unassigned",
                    "case_holder": a.case_holder,
                    "due_date": due_date_val.isoformat(),
                    "due_date_obj": due_date_val,
                    "days_overdue": days_overdue,
                    "escalation_level": esc_level,
                    "linked_alert_id": linked_alert.id if linked_alert else None,
                    "linked_alert_severity": linked_alert.severity.value if linked_alert else None,
                })

        # 2. Overdue EVC visits
        evc_query = db.query(EvcVisit).join(Application)
        if region_id:
            evc_query = evc_query.filter(Application.region_id == region_id)
        if institution_id:
            evc_query = evc_query.filter(Application.institution_id == institution_id)

        visits = evc_query.all()
        for v in visits:
            if v.scheduled_date and v.scheduled_date < now_date and v.status not in [EvcStatusEnum.VISIT_COMPLETED, EvcStatusEnum.REPORT_SUBMITTED, EvcStatusEnum.CLOSED]:
                days_overdue = (now_date - v.scheduled_date).days
                linked_alert = db.query(Alert).filter(
                    Alert.application_id == v.application_id,
                    Alert.status != AlertStatusEnum.RESOLVED,
                    Alert.rule.has(AlertRule.code.in_(["RULE_EVC_UNSCHEDULED", "RULE_EVC_VISIT_OVERDUE"]))
                ).first()

                app = v.application
                raw_items.append({
                    "id": f"EVC-{v.id}",
                    "item_type": "EVC_VISIT",
                    "reference_no": f"EVC-{v.id:04d}",
                    "title": f"Expert Visit ({v.status.value})",
                    "institution_id": app.institution_id if app else None,
                    "institution_name": app.institution.name if app and app.institution else "-",
                    "region_id": app.region_id if app else None,
                    "region_name": app.region.name if app and app.region else "-",
                    "assigned_officer": app.assigned_officer.full_name if app and app.assigned_officer else "-",
                    "case_holder": app.case_holder if app else "WITH_AICTE",
                    "due_date": v.scheduled_date.isoformat(),
                    "due_date_obj": v.scheduled_date,
                    "days_overdue": float(days_overdue),
                    "escalation_level": f"TIER_{linked_alert.escalation_tier}" if linked_alert else "NORMAL",
                    "linked_alert_id": linked_alert.id if linked_alert else None,
                    "linked_alert_severity": linked_alert.severity.value if linked_alert else None,
                })

        # 3. Overdue Undertakings
        ut_query = db.query(Undertaking).join(Institution)
        if region_id:
            ut_query = ut_query.filter(Institution.region_id == region_id)
        if institution_id:
            ut_query = ut_query.filter(Undertaking.institution_id == institution_id)

        undertakings = ut_query.all()
        for ut in undertakings:
            if ut.due_date < now_date and ut.status not in [UndertakingStatusEnum.VERIFIED, UndertakingStatusEnum.COMPLIED]:
                days_overdue = (now_date - ut.due_date).days
                linked_alert = db.query(Alert).filter(
                    Alert.undertaking_id == ut.id,
                    Alert.status != AlertStatusEnum.RESOLVED
                ).first()

                app = ut.application
                inst = ut.institution
                raw_items.append({
                    "id": f"UT-{ut.id}",
                    "item_type": "UNDERTAKING",
                    "reference_no": f"UT-{ut.id:04d}",
                    "title": f"Undertaking: {ut.condition_title}",
                    "institution_id": ut.institution_id,
                    "institution_name": inst.name if inst else "-",
                    "region_id": inst.region_id if inst else None,
                    "region_name": inst.region.name if inst and inst.region else "-",
                    "assigned_officer": app.assigned_officer.full_name if app and app.assigned_officer else "-",
                    "case_holder": app.case_holder if app else "WITH_INSTITUTION",
                    "due_date": ut.due_date.isoformat(),
                    "due_date_obj": ut.due_date,
                    "days_overdue": float(days_overdue),
                    "escalation_level": f"TIER_{linked_alert.escalation_tier}" if linked_alert else "NORMAL",
                    "linked_alert_id": linked_alert.id if linked_alert else None,
                    "linked_alert_severity": linked_alert.severity.value if linked_alert else None,
                })

        # 4. Expired/Overdue Documents
        doc_query = db.query(Document).join(Institution)
        if region_id:
            doc_query = doc_query.filter(Institution.region_id == region_id)
        if institution_id:
            doc_query = doc_query.filter(Document.institution_id == institution_id)

        documents = doc_query.all()
        for doc in documents:
            if doc.expiry_date < now_date and doc.status != DocumentStatusEnum.SUPERSEDED:
                days_overdue = (now_date - doc.expiry_date).days
                linked_alert = db.query(Alert).filter(
                    Alert.document_id == doc.id,
                    Alert.status != AlertStatusEnum.RESOLVED
                ).first()

                app = doc.application
                inst = doc.institution
                raw_items.append({
                    "id": f"DOC-{doc.id}",
                    "item_type": "DOCUMENT",
                    "reference_no": f"DOC-{doc.id:04d}",
                    "title": f"Statutory Document: {doc.document_type.value if hasattr(doc.document_type, 'value') else doc.document_type} ({doc.title})",
                    "institution_id": doc.institution_id,
                    "institution_name": inst.name if inst else "-",
                    "region_id": inst.region_id if inst else None,
                    "region_name": inst.region.name if inst and inst.region else "-",
                    "assigned_officer": app.assigned_officer.full_name if app and app.assigned_officer else "-",
                    "case_holder": app.case_holder if app else "WITH_INSTITUTION",
                    "due_date": doc.expiry_date.isoformat(),
                    "due_date_obj": doc.expiry_date,
                    "days_overdue": float(days_overdue),
                    "escalation_level": f"TIER_{linked_alert.escalation_tier}" if linked_alert else "NORMAL",
                    "linked_alert_id": linked_alert.id if linked_alert else None,
                    "linked_alert_severity": linked_alert.severity.value if linked_alert else None,
                })

        # Apply secondary filters
        filtered = raw_items
        if item_type and item_type != "ALL":
            filtered = [x for x in filtered if x["item_type"] == item_type]
        if date_from:
            filtered = [x for x in filtered if x["due_date_obj"] >= date_from]
        if date_to:
            filtered = [x for x in filtered if x["due_date_obj"] <= date_to]

        # Clean out temporary due_date_obj
        for x in filtered:
            x.pop("due_date_obj", None)

        # Compute summary
        by_region_map: Dict[str, int] = {}
        by_type_map: Dict[str, int] = {}
        for x in filtered:
            reg = x.get("region_name") or "Unknown"
            t = x.get("item_type") or "Unknown"
            by_region_map[reg] = by_region_map.get(reg, 0) + 1
            by_type_map[t] = by_type_map.get(t, 0) + 1

        summary = {
            "total_overdue": len(filtered),
            "applications_overdue": sum(1 for x in filtered if x["item_type"] == "APPLICATION"),
            "evc_overdue": sum(1 for x in filtered if x["item_type"] == "EVC_VISIT"),
            "undertakings_overdue": sum(1 for x in filtered if x["item_type"] == "UNDERTAKING"),
            "documents_overdue": sum(1 for x in filtered if x["item_type"] == "DOCUMENT"),
            "with_aicte_count": sum(1 for x in filtered if x["case_holder"] == "WITH_AICTE"),
            "with_institution_count": sum(1 for x in filtered if x["case_holder"] == "WITH_INSTITUTION"),
            "by_region": [{"region": k, "count": v} for k, v in by_region_map.items()],
            "by_type": [{"type": k, "count": v} for k, v in by_type_map.items()],
        }

        return {
            "summary": summary,
            "items": filtered
        }

    @staticmethod
    def export_csv(report_type: str, data: Dict[str, Any]) -> str:
        """Serializes report data to CSV format string."""
        output = StringIO()
        writer = csv.writer(output)

        if report_type == "pendency":
            writer.writerow(["Report", "AICTE Application Pendency & Ageing Report"])
            writer.writerow(["Total Pending", data.get("total_pending")])
            writer.writerow(["Total Overdue", data.get("total_overdue")])
            writer.writerow(["Total With AICTE", data.get("total_with_aicte")])
            writer.writerow(["Total With Institution", data.get("total_with_institution")])
            writer.writerow([])
            writer.writerow(["Approval Stage", "Pending Applications", "Average Days in Stage", "Overdue Count", "With AICTE", "With Institution"])
            for s in data.get("by_stage", []):
                writer.writerow([s["stage"], s["count"], s["avg_days"], s["overdue_count"], s.get("with_aicte_count", 0), s.get("with_institution_count", 0)])
            writer.writerow([])
            writer.writerow(["Region", "Pending Applications", "Average Days", "Overdue Count", "With AICTE", "With Institution"])
            for r in data.get("by_region", []):
                writer.writerow([r["region"], r["count"], r["avg_days"], r["overdue_count"], r.get("with_aicte_count", 0), r.get("with_institution_count", 0)])

        elif report_type == "regional_performance":
            writer.writerow(["Report", "AICTE Regional Performance & Compliance Matrix"])
            writer.writerow([])
            writer.writerow(["Region Name", "Headquarters", "Total Applications", "With AICTE", "With Institution", "Closed Cases", "Avg Days/Stage", "SLA Breach Rate (%)", "Alerts Raised", "Alerts Resolved"])
            for reg in data.get("regions", []):
                writer.writerow([
                    reg["region_name"], reg["headquarters"], reg["total_applications"],
                    reg.get("with_aicte_count", 0), reg.get("with_institution_count", 0), reg.get("closed_count", 0),
                    reg["avg_days_per_stage"], reg["sla_breach_rate_pct"],
                    reg["alerts_raised"], reg["alerts_resolved"]
                ])

        elif report_type == "evc":
            writer.writerow(["Report", "AICTE Expert Visit Committee (EVC) Turnaround Report"])
            writer.writerow(["Total Visits", data.get("total_visits")])
            writer.writerow(["Average Turnaround Days", data.get("average_turnaround_days")])
            writer.writerow([])
            writer.writerow(["Status", "Count"])
            for s in data.get("by_status", []):
                writer.writerow([s["status"], s["count"]])

        elif report_type == "undertakings":
            writer.writerow(["Report", "AICTE Conditional Undertakings Compliance Report"])
            writer.writerow(["Total Undertakings", data.get("total_undertakings")])
            writer.writerow(["Verified", data.get("verified_count")])
            writer.writerow(["Overdue", data.get("overdue_count")])
            writer.writerow(["Escalated", data.get("escalated_count")])
            writer.writerow([])
            writer.writerow(["Status", "Count"])
            for s in data.get("by_status", []):
                writer.writerow([s["status"], s["count"]])

        elif report_type == "documents":
            writer.writerow(["Report", "AICTE Statutory Document Validity Report"])
            writer.writerow(["Total Documents", data.get("total_documents")])
            writer.writerow(["Valid", data.get("valid_count")])
            writer.writerow(["Expired", data.get("expired_count")])
            writer.writerow(["Expiring Soon", data.get("expiring_soon_count")])
            writer.writerow([])
            writer.writerow(["Document Type", "Total", "Valid", "Expiring", "Expired"])
            for t in data.get("by_type", []):
                writer.writerow([t["type"], t["total"], t["valid"], t["expiring"], t["expired"]])

        elif report_type in ["overdue", "overdue_cases"]:
            writer.writerow(["Report", "AICTE Statutory Overdue Cases & Compliance Docket"])
            summary = data.get("summary", {})
            writer.writerow(["Total Overdue Items", summary.get("total_overdue")])
            writer.writerow(["Applications Overdue", summary.get("applications_overdue")])
            writer.writerow(["EVC Visits Overdue", summary.get("evc_overdue")])
            writer.writerow(["Undertakings Overdue", summary.get("undertakings_overdue")])
            writer.writerow(["Documents Expired", summary.get("documents_overdue")])
            writer.writerow([])
            writer.writerow(["Type", "Reference", "Title", "Institution", "Region", "Officer", "Case Holder", "Due Date", "Days Overdue", "Escalation", "Alert ID"])
            for it in data.get("items", []):
                writer.writerow([
                    it["item_type"], it["reference_no"], it["title"],
                    it["institution_name"], it["region_name"], it["assigned_officer"],
                    it["case_holder"], it["due_date"], it["days_overdue"],
                    it["escalation_level"], it.get("linked_alert_id") or "-"
                ])

        return output.getvalue()

    @staticmethod
    def export_pdf(report_type: str, data: Dict[str, Any]) -> bytes:
        """Generates downloadable summary PDF using fpdf2."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, "Statutory Compliance & Regulatory Monitoring Docket", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "SAMPLE - SYNTHETIC DEMO REPORT, NOT AN OFFICIAL AICTE ORDER", new_x="LMARGIN", new_y="NEXT")
        pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
        pdf.ln(5)

        if report_type == "regional_performance":
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Regional Performance & SLA Breach Benchmark", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(40, 7, "Region", 1)
            pdf.cell(20, 7, "Apps", 1)
            pdf.cell(25, 7, "AICTE/Inst", 1)
            pdf.cell(20, 7, "Closed", 1)
            pdf.cell(25, 7, "Avg Days", 1)
            pdf.cell(25, 7, "Breach Rate", 1)
            pdf.cell(35, 7, "Alerts Resolved", 1, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 8)
            for reg in data.get("regions", []):
                pdf.cell(40, 7, str(reg["region_name"])[:20], 1)
                pdf.cell(20, 7, str(reg["total_applications"]), 1)
                pdf.cell(25, 7, f"{reg.get('with_aicte_count',0)}/{reg.get('with_institution_count',0)}", 1)
                pdf.cell(20, 7, str(reg.get('closed_count', 0)), 1)
                pdf.cell(25, 7, str(reg["avg_days_per_stage"]), 1)
                pdf.cell(25, 7, f"{reg['sla_breach_rate_pct']}%", 1)
                pdf.cell(35, 7, f"{reg['alerts_resolved']}/{reg['alerts_raised']}", 1, new_x="LMARGIN", new_y="NEXT")

        elif report_type == "pendency":
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Application Pendency & Ageing Audit Docket", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 7, f"Total In-Progress: {data.get('total_pending')} | Overdue: {data.get('total_overdue')} | With AICTE: {data.get('total_with_aicte', 0)} | With Inst: {data.get('total_with_institution', 0)}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(60, 7, "Stage", 1)
            pdf.cell(30, 7, "Pending", 1)
            pdf.cell(35, 7, "AICTE / Inst", 1)
            pdf.cell(30, 7, "Avg Days", 1)
            pdf.cell(35, 7, "Overdue Count", 1, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 9)
            for s in data.get("by_stage", []):
                pdf.cell(60, 7, str(s["stage"])[:28], 1)
                pdf.cell(30, 7, str(s["count"]), 1)
                pdf.cell(35, 7, f"{s.get('with_aicte_count',0)} / {s.get('with_institution_count',0)}", 1)
                pdf.cell(30, 7, str(s["avg_days"]), 1)
                pdf.cell(35, 7, str(s["overdue_count"]), 1, new_x="LMARGIN", new_y="NEXT")

        elif report_type in ["overdue", "overdue_cases"]:
            summary = data.get("summary", {})
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Statutory Overdue Cases & Compliance Audit Report", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 7, f"Total Overdue: {summary.get('total_overdue', 0)} (Apps: {summary.get('applications_overdue', 0)}, EVC: {summary.get('evc_overdue', 0)}, UT: {summary.get('undertakings_overdue', 0)}, Docs: {summary.get('documents_overdue', 0)})", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(25, 7, "Type", 1)
            pdf.cell(35, 7, "Reference", 1)
            pdf.cell(45, 7, "Institution", 1)
            pdf.cell(25, 7, "Holder", 1)
            pdf.cell(25, 7, "Days Overdue", 1)
            pdf.cell(35, 7, "Escalation", 1, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 8)
            for it in data.get("items", [])[:40]: # First 40 for clean PDF display
                pdf.cell(25, 7, str(it["item_type"])[:12], 1)
                pdf.cell(35, 7, str(it["reference_no"])[:18], 1)
                pdf.cell(45, 7, str(it["institution_name"])[:22], 1)
                pdf.cell(25, 7, str(it["case_holder"])[:12], 1)
                pdf.cell(25, 7, f"{it['days_overdue']} d", 1)
                pdf.cell(35, 7, str(it["escalation_level"])[:18], 1, new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())

    @staticmethod
    def get_institution_health_dossier(db: Session, institution_id: int) -> Dict[str, Any]:
        """
        360-degree Institution Health compliance summary:
        Applications, open undertakings, document expiries, open alerts, and complaint history.
        """
        inst = db.query(Institution).filter(Institution.id == institution_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="Institution not found")

        apps = db.query(Application).filter(Application.institution_id == inst.id).order_by(Application.created_at.desc()).all()
        undertakings = db.query(Undertaking).filter(Undertaking.institution_id == inst.id).order_by(Undertaking.due_date.asc()).all()
        documents = db.query(Document).filter(Document.institution_id == inst.id).order_by(Document.expiry_date.asc()).all()
        alerts = db.query(Alert).filter(Alert.institution_id == inst.id, Alert.status != AlertStatusEnum.RESOLVED).all()

        now = ClockService.get_now().date()

        # Compute health score: 100 base, penalize for open alerts, expired docs, overdue undertakings
        health_score = 100
        critical_alerts = [a for a in alerts if a.severity.value == "CRITICAL"]
        high_alerts = [a for a in alerts if a.severity.value == "HIGH"]
        expired_docs = [d for d in documents if d.expiry_date < now and d.status.value != "SUPERSEDED"]
        overdue_uts = [u for u in undertakings if u.due_date < now and u.status.value not in ["VERIFIED", "COMPLIED"]]

        health_score -= (len(critical_alerts) * 25)
        health_score -= (len(high_alerts) * 10)
        health_score -= (len(expired_docs) * 15)
        health_score -= (len(overdue_uts) * 10)
        health_score = max(0, min(100, health_score))

        health_rating = "EXCELLENT" if health_score >= 85 else "SATISFACTORY" if health_score >= 65 else "NEEDS_ATTENTION" if health_score >= 40 else "CRITICAL_DEFICIENCY"

        return {
            "institution": {
                "id": inst.id,
                "aicte_id": inst.aicte_id,
                "name": inst.name,
                "category": inst.category,
                "institution_type": inst.institution_type,
                "city": inst.city,
                "state": inst.state,
                "region_id": inst.region_id,
                "primary_email": inst.primary_email,
            },
            "compliance_summary": {
                "health_score": health_score,
                "health_rating": health_rating,
                "open_alerts_count": len(alerts),
                "critical_alerts_count": len(critical_alerts),
                "expired_documents_count": len(expired_docs),
                "overdue_undertakings_count": len(overdue_uts),
            },
            "applications": [
                {
                    "id": a.id,
                    "application_number": a.application_number,
                    "category": a.category.title if a.category else "General",
                    "current_stage": a.current_stage.name if a.current_stage else "Pending",
                    "status": a.status.value,
                    "revert_count": a.revert_count,
                    "stage_due_date": a.stage_due_date.isoformat(),
                }
                for a in apps
            ],
            "undertakings": [
                {
                    "id": u.id,
                    "condition_title": u.condition_title,
                    "due_date": u.due_date.isoformat(),
                    "status": u.status.value,
                    "is_overdue": u.due_date < now and u.status.value not in ["VERIFIED", "COMPLIED"],
                }
                for u in undertakings
            ],
            "documents": [
                {
                    "id": d.id,
                    "document_type": d.document_type.value,
                    "document_number": d.document_number,
                    "expiry_date": d.expiry_date.isoformat(),
                    "status": d.status.value,
                    "version_number": d.version_number,
                    "is_expired": d.expiry_date < now,
                }
                for d in documents
            ],
            "open_alerts": [
                {
                    "id": al.id,
                    "rule_code": al.rule.code if getattr(al, "rule", None) else (al.alert_type.value if hasattr(al.alert_type, "value") else str(al.alert_type)),
                    "title": al.title,
                    "severity": al.severity.value,
                    "status": al.status.value,
                    "escalation_tier": al.escalation_tier,
                }
                for al in alerts
            ],
        }
