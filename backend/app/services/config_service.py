from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import StagePath, Stage, AlertRule, SystemConfig


def get_all_stage_paths(db: Session) -> List[StagePath]:
    return db.query(StagePath).filter(StagePath.is_active == True).order_by(StagePath.id).all()


def get_all_stages(db: Session) -> List[Stage]:
    return db.query(Stage).order_by(Stage.id).all()


def get_all_alert_rules(db: Session) -> List[AlertRule]:
    return db.query(AlertRule).filter(AlertRule.is_active == True).order_by(AlertRule.id).all()


def get_system_config(db: Session, key: str) -> Optional[SystemConfig]:
    return db.query(SystemConfig).filter(SystemConfig.config_key == key).first()


def get_all_system_configs(db: Session) -> List[SystemConfig]:
    return db.query(SystemConfig).order_by(SystemConfig.id).all()
