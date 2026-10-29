"""
Bottleneck Finder Service for SIH26262.
Identifies stages, regions and officer queues with the highest delay concentration.
Decision support only: this service NEVER modifies application stage, status, or approval state.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Application, ApplicationStatusEnum, Stage, User, Region, ClockSegment
)
from app.services.clock import ClockService, normalize_dt


class BottleneckFinderService:
    """
    Analyses open case queues by stage, region and officer to identify bottlenecks.
    Reports AICTE-held working days only; WITH_INSTITUTION time is separated.
    """

    @staticmethod
    def compute_bottlenecks(
        db: Session,
        region_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compute bottleneck analysis across stages, regions and officers.
        Returns ranked list with one-sentence reasons.
        """
        now = normalize_dt(ClockService.get_now())

        # Fetch all in-progress applications (optionally filtered by region)
        query = db.query(Application).filter(
            Application.status == ApplicationStatusEnum.IN_PROGRESS,
        )
        if region_id:
            query = query.filter(Application.region_id == region_id)
        apps = query.all()

        if not apps:
            return {
                "bottlenecks": [],
                "stage_region_grid": [],
                "total_open": 0,
                "analysis_note": "No open cases found for the selected scope.",
            }

        # Compute per-application AICTE and institution dwell times
        app_metrics = []
        for app in apps:
            aicte_hours = 0.0
            inst_hours = 0.0
            stage_aicte_hours = 0.0

            segments = db.query(ClockSegment).filter(
                ClockSegment.application_id == app.id,
            ).all()

            if segments:
                for seg in segments:
                    dur = seg.duration_hours
                    if dur is None:
                        dur = max(0.0, (now - normalize_dt(seg.started_at)).total_seconds() / 3600.0)
                    if seg.holder == "WITH_AICTE":
                        aicte_hours += dur
                        if seg.stage_id == app.current_stage_id:
                            stage_aicte_hours += dur
                    else:
                        inst_hours += dur
            else:
                entered = normalize_dt(app.stage_entered_at) if app.stage_entered_at else now
                dur = max(0.0, (now - entered).total_seconds() / 3600.0)
                if app.case_holder == "WITH_INSTITUTION":
                    inst_hours = dur
                else:
                    aicte_hours = dur
                    stage_aicte_hours = dur

            sla_days = app.current_stage.default_sla_days if app.current_stage else 7
            aicte_days = stage_aicte_hours / 24.0
            is_overdue = aicte_days > sla_days

            app_metrics.append({
                "app_id": app.id,
                "app_number": app.application_number,
                "stage_code": app.current_stage.code if app.current_stage else "UNKNOWN",
                "stage_name": app.current_stage.name if app.current_stage else "Unknown",
                "region_id": app.region_id,
                "region_name": app.region.name if app.region else "Unknown",
                "officer_id": app.assigned_officer_id,
                "officer_name": app.assigned_officer.full_name if app.assigned_officer else "Unassigned",
                "aicte_days": round(aicte_days, 1),
                "institution_days": round(inst_hours / 24.0, 1),
                "sla_days": sla_days,
                "is_overdue": is_overdue,
                "case_holder": app.case_holder,
                "risk_score": app.delay_risk_score or 0.0,
            })

        # --- Aggregate by stage + region ---
        stage_region_groups: Dict[str, Dict[str, Any]] = {}
        for m in app_metrics:
            key = f"{m['stage_code']}_{m['region_id']}"
            if key not in stage_region_groups:
                stage_region_groups[key] = {
                    "stage_code": m["stage_code"],
                    "stage_name": m["stage_name"],
                    "region_id": m["region_id"],
                    "region_name": m["region_name"],
                    "sla_days": m["sla_days"],
                    "cases": [],
                }
            stage_region_groups[key]["cases"].append(m)

        bottleneck_entries = []
        total_delay = sum(max(0, m["aicte_days"] - m["sla_days"]) for m in app_metrics if m["aicte_days"] > m["sla_days"])

        for key, group in stage_region_groups.items():
            cases = group["cases"]
            n = len(cases)
            avg_aicte = round(sum(c["aicte_days"] for c in cases) / n, 1) if n > 0 else 0
            avg_inst = round(sum(c["institution_days"] for c in cases) / n, 1) if n > 0 else 0
            overdue_count = sum(1 for c in cases if c["is_overdue"])
            overdue_rate = round(overdue_count / n * 100, 1) if n > 0 else 0.0
            group_delay = sum(max(0, c["aicte_days"] - c["sla_days"]) for c in cases if c["aicte_days"] > c["sla_days"])
            share_of_delay = round(group_delay / total_delay * 100, 1) if total_delay > 0 else 0.0
            sla = group["sla_days"]
            ratio = round(avg_aicte / sla, 2) if sla > 0 else 0

            # One-sentence reason
            reason = (
                f"{group['stage_name']} in {group['region_name']}: "
                f"{n} cases averaging {avg_aicte} days against {sla}-day SLA "
                f"({overdue_rate}% overdue, {share_of_delay}% of total delay)."
            )

            low_sample = n < 3

            bottleneck_entries.append({
                "stage_code": group["stage_code"],
                "stage_name": group["stage_name"],
                "region_id": group["region_id"],
                "region_name": group["region_name"],
                "open_cases": n,
                "avg_aicte_days": avg_aicte,
                "avg_institution_days": avg_inst,
                "sla_days": sla,
                "ratio_aicte_sla": ratio,
                "overdue_count": overdue_count,
                "overdue_rate": overdue_rate,
                "share_of_total_delay": share_of_delay,
                "reason": reason,
                "low_sample": low_sample,
            })

        # Sort by share_of_total_delay descending, then overdue_rate descending
        bottleneck_entries.sort(key=lambda x: (-x["share_of_total_delay"], -x["overdue_rate"]))

        # --- Stage-region heat grid ---
        all_stages = sorted(set(m["stage_code"] for m in app_metrics))
        all_regions = sorted(set(m["region_id"] for m in app_metrics))
        region_names = {}
        for m in app_metrics:
            region_names[m["region_id"]] = m["region_name"]

        grid = []
        for rid in all_regions:
            row = {"region_id": rid, "region_name": region_names.get(rid, "Unknown"), "stages": {}}
            for sc in all_stages:
                key = f"{sc}_{rid}"
                if key in stage_region_groups:
                    group = stage_region_groups[key]
                    cases = group["cases"]
                    n = len(cases)
                    avg = round(sum(c["aicte_days"] for c in cases) / n, 1) if n > 0 else 0
                    sla = group["sla_days"]
                    row["stages"][sc] = {
                        "avg_days": avg,
                        "sla_days": sla,
                        "ratio": round(avg / sla, 2) if sla > 0 else 0,
                        "count": n,
                    }
            grid.append(row)

        # --- Officer queue analysis ---
        officer_groups: Dict[int, List[Dict]] = {}
        for m in app_metrics:
            oid = m["officer_id"]
            if oid:
                if oid not in officer_groups:
                    officer_groups[oid] = []
                officer_groups[oid].append(m)

        officer_bottlenecks = []
        for oid, cases in officer_groups.items():
            n = len(cases)
            avg_aicte = round(sum(c["aicte_days"] for c in cases) / n, 1) if n > 0 else 0
            overdue_count = sum(1 for c in cases if c["is_overdue"])
            officer_bottlenecks.append({
                "officer_id": oid,
                "officer_name": cases[0]["officer_name"],
                "open_cases": n,
                "avg_aicte_days": avg_aicte,
                "overdue_count": overdue_count,
                "low_sample": n < 3,
            })
        officer_bottlenecks.sort(key=lambda x: (-x["open_cases"], -x["avg_aicte_days"]))

        return {
            "bottlenecks": bottleneck_entries[:20],
            "stage_region_grid": grid,
            "officer_bottlenecks": officer_bottlenecks[:10],
            "total_open": len(apps),
            "total_overdue": sum(1 for m in app_metrics if m["is_overdue"]),
            "total_delay_days": round(total_delay, 1),
            "analysis_note": "WITH_INSTITUTION time is excluded from AICTE delay calculations. Low-sample groups (fewer than 3 cases) are flagged.",
        }
