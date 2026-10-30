"""
Data Retention Preview and Policy Endpoints for SIH26262.
Provides:
- GET /retention/preview: non-destructive dry-run preview of candidate records
- GET /retention/preview/csv: CSV export of the retention preview
- GET /retention/policy: current retention periods
- PUT /retention/policy: update retention thresholds with mandatory audit logging
"""
import io
import csv
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_role
from app.models import User, UserRoleEnum
from app.services.retention_service import RetentionService

router = APIRouter(prefix="/retention", tags=["Data Retention"])


class RetentionPolicyUpdate(BaseModel):
    closed_cases_years: int = Field(5, ge=1, le=20)
    resolved_alerts_days: int = Field(180, ge=30, le=1825)
    notifications_days: int = Field(90, ge=15, le=365)
    outbox_entries_days: int = Field(60, ge=15, le=365)


@router.get("/policy")
def get_retention_policy(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN, UserRoleEnum.COMPETENT_AUTHORITY])),
):
    """Returns the statutory data retention thresholds."""
    return RetentionService.get_policy(db)


@router.put("/policy")
def update_retention_policy(
    payload: RetentionPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN])),
):
    """Admin updates data retention policy periods. Strictly audited."""
    updated = RetentionService.update_policy(db, current_user, payload.model_dump())
    return {
        "status": "success",
        "message": "Data retention policy updated successfully (audited).",
        "policy": updated
    }


@router.get("/preview")
def get_retention_preview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN, UserRoleEnum.COMPETENT_AUTHORITY])),
):
    """
    Non-destructive preview: computes how many records would be archived under current policy.
    Labelled: 'Preview only. No data is deleted by this prototype.'
    """
    return RetentionService.preview_retention(db)


@router.get("/preview/csv")
def export_retention_preview_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRoleEnum.ADMIN, UserRoleEnum.COMPETENT_AUTHORITY])),
):
    """Exports retention preview summary as CSV for regulatory reporting."""
    preview = RetentionService.preview_retention(db)
    summary = preview["summary"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["AICTE Approval System - Data Retention Dry-Run Preview"])
    writer.writerow(["Disclaimer", preview["disclaimer"]])
    writer.writerow(["Generated At (UTC)", preview["generated_at"]])
    writer.writerow([])
    writer.writerow([
        "Record Category",
        "Category Title",
        "Statutory Threshold",
        "Candidate Records for Archiving",
        "Oldest Record Date",
        "Newest Candidate Date"
    ])

    for cat in summary["categories"]:
        writer.writerow([
            cat["category"],
            cat["title"],
            cat["statutory_threshold"],
            cat["candidate_count"],
            cat.get("oldest_record") or "-",
            cat.get("newest_candidate") or "-"
        ])

    output.seek(0)
    filename = f"aicte_retention_preview_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
