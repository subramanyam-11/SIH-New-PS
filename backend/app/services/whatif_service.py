"""
EVC What-If Capacity & Backlog Planner Service for SIH26262.
Models the projected regulatory backlog and dwell time under counterfactual staffing
and inspection throughput scenarios.
Strictly read-only: NEVER mutates any database records.
Decision support only: All results are estimates to assist administrative planning.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Application, ApplicationStatusEnum, Stage, Region, EvcVisit, EvcStatusEnum,
    ClockSegment, Alert, AlertRule, AlertStatusEnum
)
from app.services.clock import ClockService, normalize_dt
from app.services.working_day_service import WorkingDayService


class WhatIfPlannerService:
    """
    Simulation service for EVC inspection capacity planning.
    Projects backlog curves, dwell days, avoided alerts, and cases cleared.
    """

    # Baseline operational constants
    DEFAULT_WEEKLY_COMPLETION_RATE = 3.0  # visits completed per region per week
    VISITS_PER_STAFF_PER_WEEK = 2.0       # additional visits per extra staff capacity unit

    @staticmethod
    def simulate_evc_capacity(
        db: Session,
        region_id: Optional[int] = None,
        extra_visits_per_week: int = 0,
        extra_staffing_capacity: int = 0,
        horizon_weeks: int = 4,
    ) -> Dict[str, Any]:
        """
        Run counterfactual simulation for EVC queue.
        Parameters:
        - region_id: None for all regions, or specific region ID.
        - extra_visits_per_week: 0 to 10
        - extra_staffing_capacity: 0 to 5
        - horizon_weeks: 1 to 8
        """
        # Bounds validation
        extra_visits_per_week = max(0, min(10, extra_visits_per_week))
        extra_staffing_capacity = max(0, min(5, extra_staffing_capacity))
        horizon_weeks = max(1, min(8, horizon_weeks))

        now = normalize_dt(ClockService.get_now())

        # 1. Query current open EVC applications
        evc_stages = db.query(Stage).filter(
            Stage.code.in_(["EVC_PENDING", "EVC_SCHEDULED"])
        ).all()
        evc_stage_ids = [s.id for s in evc_stages]

        query = db.query(Application).filter(
            Application.status == ApplicationStatusEnum.IN_PROGRESS,
            Application.current_stage_id.in_(evc_stage_ids),
        )
        if region_id:
            query = query.filter(Application.region_id == region_id)
        evc_apps = query.order_by(Application.stage_entered_at.asc()).all()

        total_in_queue = len(evc_apps)

        # 2. Compute current dwell times in queue
        queue_cases = []
        total_waiting_days = 0.0

        for idx, app in enumerate(evc_apps, start=1):
            entered = normalize_dt(app.stage_entered_at) if app.stage_entered_at else now
            wait_days = max(0.0, round((now - entered).total_seconds() / 86400.0, 1))
            total_waiting_days += wait_days

            # Check if visit scheduled
            scheduled_visit = db.query(EvcVisit).filter(
                EvcVisit.application_id == app.id,
                EvcVisit.status.in_([EvcStatusEnum.SCHEDULED, EvcStatusEnum.VISIT_COMPLETED])
            ).first()

            queue_cases.append({
                "queue_rank": idx,
                "application_id": app.id,
                "application_number": app.application_number,
                "institution_name": app.institution.name if app.institution else "Unknown",
                "region_id": app.region_id,
                "region_name": app.region.name if app.region else "Unknown",
                "stage": app.current_stage.name if app.current_stage else "EVC",
                "stage_code": app.current_stage.code if app.current_stage else "EVC_PENDING",
                "days_in_queue": wait_days,
                "risk_score": app.delay_risk_score or 0.0,
                "risk_band": app.risk_band or "LOW",
                "has_scheduled_visit": bool(scheduled_visit),
                "scheduled_date": scheduled_visit.scheduled_date.isoformat() if scheduled_visit and scheduled_visit.scheduled_date else None,
            })

        avg_current_wait_days = round(total_waiting_days / max(total_in_queue, 1), 1)

        # 3. Calculate baseline vs scenario completion throughput
        # Historical completion rate in last 4 weeks
        four_weeks_ago = now - timedelta(days=28)
        hist_completed = db.query(func.count(EvcVisit.id)).filter(
            EvcVisit.status.in_([EvcStatusEnum.REPORT_SUBMITTED, EvcStatusEnum.VISIT_COMPLETED]),
            EvcVisit.visit_completed_at >= four_weeks_ago,
        )
        if region_id:
            hist_completed = hist_completed.join(Application, EvcVisit.application_id == Application.id).filter(
                Application.region_id == region_id
            )
        actual_hist_count = hist_completed.scalar() or 0
        computed_weekly_rate = max(1.0, round(actual_hist_count / 4.0, 1)) if actual_hist_count > 0 else WhatIfPlannerService.DEFAULT_WEEKLY_COMPLETION_RATE

        baseline_rate = computed_weekly_rate
        added_rate = float(extra_visits_per_week) + (float(extra_staffing_capacity) * WhatIfPlannerService.VISITS_PER_STAFF_PER_WEEK)
        scenario_rate = baseline_rate + added_rate

        # 4. Week-by-week projection
        weekly_projection = []
        b_backlog = total_in_queue
        s_backlog = total_in_queue

        for w in range(1, horizon_weeks + 1):
            b_cleared_cumulative = min(total_in_queue, int(round(baseline_rate * w)))
            s_cleared_cumulative = min(total_in_queue, int(round(scenario_rate * w)))

            b_remaining = max(0, total_in_queue - b_cleared_cumulative)
            s_remaining = max(0, total_in_queue - s_cleared_cumulative)

            # Average wait days projection (approximate reduction as throughput increases)
            b_wait_proj = max(1.0, round(avg_current_wait_days * (b_remaining / max(total_in_queue, 1)), 1))
            s_wait_proj = max(1.0, round(avg_current_wait_days * (s_remaining / max(total_in_queue, 1)), 1))

            weekly_projection.append({
                "week": w,
                "label": f"Week {w}",
                "baseline_backlog": b_remaining,
                "scenario_backlog": s_remaining,
                "baseline_cleared": b_cleared_cumulative,
                "scenario_cleared": s_cleared_cumulative,
                "baseline_avg_wait_days": b_wait_proj,
                "scenario_avg_wait_days": s_wait_proj,
            })

        # 5. Cases that move forward under the scenario
        scenario_total_cleared = min(total_in_queue, int(round(scenario_rate * horizon_weeks)))
        baseline_total_cleared = min(total_in_queue, int(round(baseline_rate * horizon_weeks)))
        additional_cleared = max(0, scenario_total_cleared - baseline_total_cleared)

        # Tag each case with projected advancement
        cases_moving_forward = []
        for i, c in enumerate(queue_cases):
            case_copy = dict(c)
            if i < scenario_total_cleared:
                advancement_week = int(i // scenario_rate) + 1
                case_copy["will_advance_in_scenario"] = True
                case_copy["projected_week"] = min(advancement_week, horizon_weeks)
                case_copy["advancement_status"] = "Advanced in Scenario" if i >= baseline_total_cleared else "Cleared in Baseline"
            else:
                case_copy["will_advance_in_scenario"] = False
                case_copy["projected_week"] = None
                case_copy["advancement_status"] = "Remains in Queue"

            cases_moving_forward.append(case_copy)

        # 6. Avoided overdue EVC alerts
        # Cases where days_in_queue + (7 * week) would have breached 10d SLA in baseline but are cleared in scenario
        avoided_alerts_count = 0
        for i in range(baseline_total_cleared, scenario_total_cleared):
            if i < len(queue_cases):
                if queue_cases[i]["days_in_queue"] >= 5:
                    avoided_alerts_count += 1
        # Minimum estimation
        avoided_alerts_count = max(avoided_alerts_count, int(additional_cleared * 0.6))

        # 7. Summary metrics
        region_obj = db.query(Region).filter(Region.id == region_id).first() if region_id else None
        region_name = region_obj.name if region_obj else "All Regions"

        return {
            "inputs": {
                "region_id": region_id,
                "region_name": region_name,
                "extra_visits_per_week": extra_visits_per_week,
                "extra_staffing_capacity": extra_staffing_capacity,
                "horizon_weeks": horizon_weeks,
            },
            "assumptions": {
                "baseline_completion_rate_per_week": baseline_rate,
                "scenario_completion_rate_per_week": scenario_rate,
                "added_visits_per_staff_unit": WhatIfPlannerService.VISITS_PER_STAFF_PER_WEEK,
                "historical_sample_weeks": 4,
                "note": "Baseline completion rate derived from database event records. Estimates assume continuous officer availability.",
            },
            "summary": {
                "current_backlog": total_in_queue,
                "current_avg_wait_days": avg_current_wait_days,
                "baseline_projected_backlog": weekly_projection[-1]["baseline_backlog"] if weekly_projection else 0,
                "scenario_projected_backlog": weekly_projection[-1]["scenario_backlog"] if weekly_projection else 0,
                "baseline_cases_cleared": baseline_total_cleared,
                "scenario_cases_cleared": scenario_total_cleared,
                "additional_cases_cleared": additional_cleared,
                "avoided_overdue_alerts": avoided_alerts_count,
                "backlog_reduction_percent": round(((total_in_queue - (weekly_projection[-1]["scenario_backlog"] if weekly_projection else 0)) / max(total_in_queue, 1)) * 100, 1),
            },
            "weekly_projection": weekly_projection,
            "cases_moving_forward": cases_moving_forward,
            "disclaimer": "Estimate, decision support only. Automation assists planning; statutory inspection scheduling and decision authority remain strictly with authorized officers.",
        }
