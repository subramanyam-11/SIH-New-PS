"""
Risk Score API Endpoints for SIH26262 (Phase 7 Innovation Layer).
Provides explainable delay risk scores, factor breakdowns, and configurable weights.
Decision support only: Automation assists officers; statutory scrutiny,
inspections, and final decisions stay with authorized humans.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.core.database import get_db
from app.core.rbac import get_current_user, require_role, get_user_scope, UserScope
from app.models import Application, ApplicationStatusEnum, User, UserRoleEnum, SystemConfig
from app.schemas import (
    ApplicationRiskListItemOut, ApplicationRiskDetailOut, RiskFactorOut,
    RiskWeightsOut, RiskWeightsUpdate
)
from app.services.risk_score_service import (
    RiskScoreService, DEFAULT_WEIGHTS, DEFAULT_BANDS, DEFAULT_OFFICER_CAPACITY,
    DEFAULT_STAGE_BASELINES
)
from app.services.audit import AuditService
from app.services.clock import ClockService, normalize_dt

router = APIRouter(prefix="", tags=["Risk Scores & Delay Prediction"])


@router.get("/risk/applications", response_model=List[ApplicationRiskListItemOut])
def list_application_risk_scores(
    region_id: Optional[int] = None,
    stage_id: Optional[int] = None,
    risk_band: Optional[str] = None,
    sort_by: str = Query("delay_risk_score", pattern="^(delay_risk_score|application_number|stage_entered_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
):
    """
    List applications with delay risk score badges and bands.
    Supports filtering by risk_band (LOW, MEDIUM, HIGH) and sorting by score.
    Strictly scoped by user role & regional jurisdiction.
    """
    query = db.query(Application).filter(
        Application.status == ApplicationStatusEnum.IN_PROGRESS
    )

    # Scoping
    if scope.is_institution:
        query = query.filter(Application.institution_id == current_user.institution_id)
    elif scope.is_regional and current_user.region_id:
        query = query.filter(Application.region_id == current_user.region_id)
    elif region_id:
        query = query.filter(Application.region_id == region_id)

    if stage_id:
        query = query.filter(Application.current_stage_id == stage_id)
    if risk_band:
        query = query.filter(Application.risk_band == risk_band.upper())

    # Sorting
    sort_col = getattr(Application, sort_by, Application.delay_risk_score)
    order_func = desc if sort_order == "desc" else asc
    apps = query.order_by(order_func(sort_col)).offset(offset).limit(limit).all()

    output = []
    for app in apps:
        is_paused = (app.case_holder == "WITH_INSTITUTION")
        output.append(ApplicationRiskListItemOut(
            id=app.id,
            application_number=app.application_number,
            institution_id=app.institution_id,
            institution_name=app.institution.name if app.institution else "Unknown",
            region_id=app.region_id,
            region_name=app.region.name if app.region else "Unknown",
            stage_id=app.current_stage_id,
            stage_name=app.current_stage.name if app.current_stage else "Unknown",
            stage_code=app.current_stage.code if app.current_stage else "UNKNOWN",
            status=app.status.value,
            case_holder=app.case_holder,
            delay_risk_score=app.delay_risk_score or 0.0,
            risk_band=app.risk_band or "LOW",
            is_paused=is_paused,
        ))

    return output


@router.get("/risk/applications/{application_id}", response_model=ApplicationRiskDetailOut)
def get_application_risk_detail(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope),
):
    """
    Get full explainable risk score breakdown for a single application:
    4 factors, raw values, weights, points contributed, and plain sentence explanation.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # Scoping check
    if scope.is_institution and app.institution_id != current_user.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if scope.is_regional and current_user.region_id and app.region_id != current_user.region_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    score_data = RiskScoreService.compute_score(db, app)
    now = normalize_dt(ClockService.get_now())

    factors = [
        RiskFactorOut(
            name=f["name"],
            weight=f["weight"],
            raw_value=f["raw_value"],
            raw_denominator=f["raw_denominator"],
            ratio=f["ratio"],
            points=f["points"],
            explanation=f["explanation"],
        )
        for f in score_data.get("factors", [])
    ]

    return ApplicationRiskDetailOut(
        application_id=app.id,
        application_number=app.application_number,
        score=score_data["score"],
        band=score_data["band"],
        is_paused=score_data.get("is_paused", False),
        is_closed=score_data.get("is_closed", False),
        factors=factors,
        weights=score_data.get("weights", DEFAULT_WEIGHTS),
        raw_values=score_data.get("raw_values", {}),
        weighted_points=score_data.get("weighted_points", {}),
        computed_at=now,
        disclaimer="Decision support only: Rule-based baseline; can be trained on real AICTE data later. Automation never moves, approves, rejects, reverts or closes a case.",
    )


@router.get("/config/risk-weights", response_model=RiskWeightsOut)
def get_risk_weights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current delay risk score formula weights and thresholds.
    """
    weights = RiskScoreService.get_weights(db)
    thresholds = RiskScoreService.get_band_thresholds(db)
    capacity = RiskScoreService.get_officer_capacity(db)
    baselines = RiskScoreService.get_stage_baselines(db)

    return RiskWeightsOut(
        weights=weights,
        thresholds=thresholds,
        officer_capacity=capacity,
        stage_baselines=baselines,
        disclaimer="Rule-based baseline; can be trained on real AICTE data later.",
    )


@router.put("/config/risk-weights", response_model=RiskWeightsOut)
def update_risk_weights(
    payload: RiskWeightsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN])),
):
    """
    Update delay risk formula weights (Admin only).
    Validation: Weights across the four factors must total exactly 100.
    Audited with before/after snapshots. Recomputes open application scores.
    """
    required_keys = ["age_against_time_limit", "past_returns", "officer_workload", "current_stage"]
    for k in required_keys:
        if k not in payload.weights:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required risk factor weight: '{k}'"
            )

    total_weight = sum(int(payload.weights[k]) for k in required_keys)
    if total_weight != 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Total weights must equal exactly 100. Provided sum is {total_weight}."
        )

    # Save weights
    old_weights = RiskScoreService.get_weights(db)
    cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "risk_weights").first()
    if not cfg:
        cfg = SystemConfig(config_key="risk_weights", description="Delay risk scoring weights")
        db.add(cfg)
    cfg.config_value = {k: int(payload.weights[k]) for k in required_keys}

    if payload.thresholds:
        t_cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "risk_band_thresholds").first()
        if not t_cfg:
            t_cfg = SystemConfig(config_key="risk_band_thresholds", description="Risk band thresholds")
            db.add(t_cfg)
        t_cfg.config_value = payload.thresholds

    if payload.officer_capacity:
        c_cfg = db.query(SystemConfig).filter(SystemConfig.config_key == "officer_capacity").first()
        if not c_cfg:
            c_cfg = SystemConfig(config_key="officer_capacity", description="Configurable officer workload capacity")
            db.add(c_cfg)
        c_cfg.config_value = {"value": payload.officer_capacity}

    db.commit()

    # Recompute scores for open applications
    RiskScoreService.recompute_all(db)

    # Audit log
    AuditService.log(
        db=db,
        table_name="system_config",
        record_id=cfg.id,
        action="UPDATE_RISK_WEIGHTS",
        actor_id=current_user.id,
        old_values={"weights": old_weights},
        new_values={"weights": cfg.config_value},
    )

    return get_risk_weights(db=db, current_user=current_user)
