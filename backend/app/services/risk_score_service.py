"""
Explainable Delay Risk Score Service for SIH26262.
Computes a transparent, rule-based risk score (0-100) from four configurable factors.
Decision support only: this service NEVER modifies application stage, status, or approval state.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Application, ApplicationStatusEnum, Stage, User, SystemConfig,
    RiskScoreSnapshot, ClockSegment
)
from app.services.clock import ClockService, normalize_dt
from app.services.working_day_service import WorkingDayService
from app.services.audit import AuditService


# Default weights (must total 100)
DEFAULT_WEIGHTS = {
    "age_against_time_limit": 40,
    "past_returns": 25,
    "officer_workload": 20,
    "current_stage": 15,
}

# Default band thresholds
DEFAULT_BANDS = {
    "low_max": 35,
    "medium_max": 65,
}

# Default officer capacity
DEFAULT_OFFICER_CAPACITY = 12

# Default per-stage baseline weights (higher for EVC and SAC/SHC stages)
DEFAULT_STAGE_BASELINES = {
    "SUBMITTED": 0.1,
    "SCRUTINY": 0.3,
    "RE_SCRUTINY": 0.4,
    "EVC_PENDING": 0.6,
    "EVC_SCHEDULED": 0.7,
    "EVC_COMPLETED": 0.5,
    "SAC_SHC_REVIEW": 0.8,
    "APPROVAL_GRANTED": 0.1,
    "APPROVAL_REJECTED": 0.0,
    "CLOSED": 0.0,
}


class RiskScoreService:
    """
    Transparent rule-based risk score: 0-100 with explainable factor breakdown.
    This is NOT machine learning. It is a configurable weighted formula.
    """

    @staticmethod
    def get_weights(db: Session) -> Dict[str, int]:
        """Fetch risk weights from system_config or return defaults."""
        cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "risk_weights").first()
        if cfg and isinstance(cfg.config_value, dict):
            return cfg.config_value
        return dict(DEFAULT_WEIGHTS)

    @staticmethod
    def get_band_thresholds(db: Session) -> Dict[str, int]:
        """Fetch band thresholds from system_config or return defaults."""
        cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "risk_band_thresholds").first()
        if cfg and isinstance(cfg.config_value, dict):
            return cfg.config_value
        return dict(DEFAULT_BANDS)

    @staticmethod
    def get_officer_capacity(db: Session) -> int:
        """Fetch configurable officer capacity."""
        cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "officer_capacity").first()
        if cfg and isinstance(cfg.config_value, (int, float)):
            return int(cfg.config_value)
        if cfg and isinstance(cfg.config_value, dict):
            return int(cfg.config_value.get("value", DEFAULT_OFFICER_CAPACITY))
        return DEFAULT_OFFICER_CAPACITY

    @staticmethod
    def get_stage_baselines(db: Session) -> Dict[str, float]:
        """Fetch per-stage baseline weights."""
        cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "stage_risk_baselines").first()
        if cfg and isinstance(cfg.config_value, dict):
            return cfg.config_value
        return dict(DEFAULT_STAGE_BASELINES)

    @staticmethod
    def score_to_band(score: float, thresholds: Dict[str, int]) -> str:
        """Convert numeric score to band label."""
        low_max = thresholds.get("low_max", 35)
        medium_max = thresholds.get("medium_max", 65)
        if score <= low_max:
            return "LOW"
        elif score <= medium_max:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def compute_score(
        db: Session,
        application: Application,
        weights: Optional[Dict[str, int]] = None,
        thresholds: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Compute risk score for a single application.
        Returns full breakdown with raw values, weighted points, and explanations.
        NEVER modifies the application record.
        """
        if application.status == ApplicationStatusEnum.CLOSED:
            return {
                "score": 0.0,
                "band": "N/A",
                "is_closed": True,
                "factors": [],
                "explanation": "Closed cases are not scored.",
            }

        if weights is None:
            weights = RiskScoreService.get_weights(db)
        if thresholds is None:
            thresholds = RiskScoreService.get_band_thresholds(db)

        now = normalize_dt(ClockService.get_now())

        # --- Factor 1: Age against time limit ---
        w_age = weights.get("age_against_time_limit", 40)
        stage = application.current_stage
        sla_days = stage.default_sla_days if stage else 7

        # Compute AICTE-held working days in current stage
        is_paused = (application.case_holder == "WITH_INSTITUTION")
        stage_aicte_days = 0.0

        segments = db.query(ClockSegment).filter(
            ClockSegment.application_id == application.id,
            ClockSegment.stage_id == application.current_stage_id,
            ClockSegment.holder == "WITH_AICTE",
        ).all()

        for seg in segments:
            dur = seg.duration_hours
            if dur is None:
                dur = max(0.0, (now - normalize_dt(seg.started_at)).total_seconds() / 3600.0)
            stage_aicte_days += dur / 24.0

        if len(segments) == 0 and not is_paused:
            entered = normalize_dt(application.stage_entered_at) if application.stage_entered_at else now
            stage_aicte_days = max(0.0, (now - entered).total_seconds() / 86400.0)

        if sla_days > 0:
            ratio_age = min(stage_aicte_days / sla_days, 1.5)
        else:
            ratio_age = 0.0
        points_age = round(ratio_age * w_age, 1)

        # --- Factor 2: Past returns ---
        w_returns = weights.get("past_returns", 25)
        revert_cap_cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "max_revert_cycles").first()
        revert_cap = 2
        if revert_cap_cfg and isinstance(revert_cap_cfg.config_value, dict):
            revert_cap = int(revert_cap_cfg.config_value.get("limit", 2))
        revert_count = application.revert_count or 0
        ratio_returns = min(revert_count / max(revert_cap, 1), 1.0)
        points_returns = round(ratio_returns * w_returns, 1)

        # --- Factor 3: Officer workload ---
        w_workload = weights.get("officer_workload", 20)
        officer_capacity = RiskScoreService.get_officer_capacity(db)
        officer_id = application.assigned_officer_id
        officer_open = 0
        if officer_id:
            officer_open = db.query(func.count(Application.id)).filter(
                Application.assigned_officer_id == officer_id,
                Application.status == ApplicationStatusEnum.IN_PROGRESS,
            ).scalar() or 0
        ratio_workload = min(officer_open / max(officer_capacity, 1), 1.0)
        points_workload = round(ratio_workload * w_workload, 1)

        # --- Factor 4: Current stage ---
        w_stage = weights.get("current_stage", 15)
        stage_baselines = RiskScoreService.get_stage_baselines(db)
        stage_code = stage.code if stage else "SCRUTINY"
        baseline = stage_baselines.get(stage_code, 0.3)
        points_stage = round(baseline * w_stage, 1)

        # --- Total score ---
        score = round(min(points_age + points_returns + points_workload + points_stage, 100.0), 1)
        band = RiskScoreService.score_to_band(score, thresholds)

        factors = [
            {
                "name": "Age against time limit",
                "weight": w_age,
                "raw_value": round(stage_aicte_days, 1),
                "raw_denominator": sla_days,
                "ratio": round(ratio_age, 3),
                "points": points_age,
                "explanation": (
                    f"Open for {round(stage_aicte_days, 1)} of {sla_days} working days"
                    f"{' (paused: with institution)' if is_paused else ''}"
                    f", so {points_age} of {w_age} points"
                ),
            },
            {
                "name": "Past returns",
                "weight": w_returns,
                "raw_value": revert_count,
                "raw_denominator": revert_cap,
                "ratio": round(ratio_returns, 3),
                "points": points_returns,
                "explanation": f"{revert_count} of {revert_cap} allowed reverts, so {points_returns} of {w_returns} points",
            },
            {
                "name": "Officer workload",
                "weight": w_workload,
                "raw_value": officer_open,
                "raw_denominator": officer_capacity,
                "ratio": round(ratio_workload, 3),
                "points": points_workload,
                "explanation": f"Officer has {officer_open} of {officer_capacity} capacity open cases, so {points_workload} of {w_workload} points",
            },
            {
                "name": "Current stage",
                "weight": w_stage,
                "raw_value": stage_code,
                "raw_denominator": "baseline",
                "ratio": round(baseline, 3),
                "points": points_stage,
                "explanation": f"Stage {stage_code} has baseline weight {baseline}, so {points_stage} of {w_stage} points",
            },
        ]

        return {
            "score": score,
            "band": band,
            "is_paused": is_paused,
            "is_closed": False,
            "factors": factors,
            "weights": weights,
            "raw_values": {
                "age": round(stage_aicte_days, 1),
                "returns": revert_count,
                "workload": officer_open,
                "stage": stage_code,
            },
            "weighted_points": {
                "age": points_age,
                "returns": points_returns,
                "workload": points_workload,
                "stage": points_stage,
            },
        }

    @staticmethod
    def compute_and_store(db: Session, application: Application) -> RiskScoreSnapshot:
        """Compute score and persist a snapshot. Also updates application.delay_risk_score and risk_band."""
        result = RiskScoreService.compute_score(db, application)

        if result.get("is_closed"):
            application.delay_risk_score = 0.0
            application.risk_band = "N/A"
            return None

        weights = result["weights"]
        now = normalize_dt(ClockService.get_now())

        snapshot = RiskScoreSnapshot(
            application_id=application.id,
            score=result["score"],
            band=result["band"],
            factor_age=result["weighted_points"]["age"],
            factor_returns=result["weighted_points"]["returns"],
            factor_workload=result["weighted_points"]["workload"],
            factor_stage=result["weighted_points"]["stage"],
            raw_age=result["raw_values"]["age"],
            raw_returns=result["raw_values"]["returns"],
            raw_workload=result["raw_values"]["workload"],
            raw_stage=None,  # stage code is a string, stored in weights
            weights=weights,
            config_version="v1",
            computed_at=now,
        )
        db.add(snapshot)

        # Update application cached fields (for quick listing and filtering)
        application.delay_risk_score = result["score"]
        application.risk_band = result["band"]

        return snapshot

    @staticmethod
    def recompute_all(db: Session) -> Dict[str, Any]:
        """Recompute risk scores for all IN_PROGRESS applications."""
        apps = db.query(Application).filter(
            Application.status == ApplicationStatusEnum.IN_PROGRESS
        ).all()

        counts = {"total": len(apps), "low": 0, "medium": 0, "high": 0}
        for app in apps:
            result = RiskScoreService.compute_score(db, app)
            snapshot = RiskScoreService.compute_and_store(db, app)
            band = result["band"]
            if band == "LOW":
                counts["low"] += 1
            elif band == "MEDIUM":
                counts["medium"] += 1
            elif band == "HIGH":
                counts["high"] += 1

        db.commit()
        return counts
