from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models import User
from app.schemas import StagePathOut, StageOut, AlertRuleOut, SystemConfigOut
from app.services.config_service import (
    get_all_stage_paths, get_all_stages, get_all_alert_rules, get_all_system_configs
)

router = APIRouter(prefix="/config", tags=["Configuration & Rules"])


@router.get("/stage-paths", response_model=List[StagePathOut])
def list_stage_paths(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns all active APH approval stage paths."""
    return get_all_stage_paths(db)


@router.get("/stages", response_model=List[StageOut])
def list_stages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns all configured stages with SLA days and responsible roles."""
    return get_all_stages(db)


@router.get("/rules", response_model=Dict[str, Any])
def list_rules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns alert rules and general system configuration settings."""
    alert_rules = get_all_alert_rules(db)
    system_configs = get_all_system_configs(db)
    
    return {
        "alert_rules": [AlertRuleOut.model_validate(r) for r in alert_rules],
        "system_configs": [SystemConfigOut.model_validate(c) for c in system_configs]
    }
