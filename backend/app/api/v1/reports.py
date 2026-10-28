from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import get_current_user, UserScope, get_user_scope
from app.models import User
from app.services.reports_service import ReportsService

router = APIRouter(prefix="/reports", tags=["Statutory Reports & Analytics"])


@router.get("/pendency")
def get_pendency_report(
    region_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Pendency and Ageing Report by stage, region, and officer.
    Pure database-backed calculation.
    """
    effective_reg_id = scope.region_id if scope.is_regional else region_id
    effective_inst_id = scope.institution_id if scope.is_institution else institution_id

    return ReportsService.get_pendency_report(
        db=db,
        region_id=effective_reg_id,
        institution_id=effective_inst_id
    )


@router.get("/evc")
def get_evc_report(
    region_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    EVC Status Report: waiting, scheduled, completed, average days.
    """
    effective_reg_id = scope.region_id if scope.is_regional else region_id
    return ReportsService.get_evc_status_report(db=db, region_id=effective_reg_id)


@router.get("/undertakings")
def get_undertakings_report(
    region_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Undertaking Compliance Report: on-time, late, overdue, escalated.
    """
    effective_reg_id = scope.region_id if scope.is_regional else region_id
    return ReportsService.get_undertaking_compliance_report(db=db, region_id=effective_reg_id)


@router.get("/documents")
def get_documents_report(
    region_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Document Validity Report: valid, expiring, expired, renewal submitted, renewed.
    """
    effective_reg_id = scope.region_id if scope.is_regional else region_id
    return ReportsService.get_document_validity_report(db=db, region_id=effective_reg_id)


@router.get("/regional-performance")
def get_regional_performance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Regional Performance Report: applications processed, avg days per stage, SLA breach rate, alerts raised and resolved.
    """
    return ReportsService.get_regional_performance_report(db=db)


@router.get("/overdue")
def get_overdue_cases_report(
    region_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    item_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Overdue Cases Report: Applications (AICTE clock only), EVC visits,
    undertakings, and statutory documents that are overdue.
    """
    from datetime import date
    effective_reg_id = scope.region_id if scope.is_regional else region_id
    effective_inst_id = scope.institution_id if scope.is_institution else institution_id

    d_from = date.fromisoformat(date_from) if date_from else None
    d_to = date.fromisoformat(date_to) if date_to else None

    return ReportsService.get_overdue_cases_report(
        db=db,
        region_id=effective_reg_id,
        institution_id=effective_inst_id,
        item_type=item_type,
        date_from=d_from,
        date_to=d_to
    )


@router.get("/export/csv")
def export_csv(
    report_type: str = Query(..., description="pendency, evc, undertakings, documents, regional_performance, overdue"),
    region_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    item_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Export database-calculated compliance report as CSV.
    """
    effective_reg_id = scope.region_id if scope.is_regional else region_id
    effective_inst_id = scope.institution_id if scope.is_institution else institution_id

    if report_type in ["pendency", "PENDENCY"]:
        data = ReportsService.get_pendency_report(db, region_id=effective_reg_id)
        canon_type = "pendency"
    elif report_type in ["evc", "EVC"]:
        data = ReportsService.get_evc_status_report(db, region_id=effective_reg_id)
        canon_type = "evc"
    elif report_type in ["undertakings", "undertaking", "UNDERTAKINGS"]:
        data = ReportsService.get_undertaking_compliance_report(db, region_id=effective_reg_id)
        canon_type = "undertakings"
    elif report_type in ["documents", "document", "DOCUMENTS"]:
        data = ReportsService.get_document_validity_report(db, region_id=effective_reg_id)
        canon_type = "documents"
    elif report_type in ["regional_performance", "regional-performance", "REGIONAL_PERFORMANCE"]:
        data = ReportsService.get_regional_performance_report(db)
        canon_type = "regional_performance"
    elif report_type in ["overdue", "overdue_cases", "OVERDUE"]:
        data = ReportsService.get_overdue_cases_report(db, region_id=effective_reg_id, institution_id=effective_inst_id, item_type=item_type)
        canon_type = "overdue"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported report type: {report_type}")

    csv_content = ReportsService.export_csv(canon_type, data)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="aicte_{canon_type}_report.csv"'}
    )


@router.get("/export/pdf")
def export_pdf(
    report_type: str = Query(..., description="regional_performance, pendency, or overdue"),
    region_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    item_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Export official statutory report as PDF.
    """
    effective_reg_id = scope.region_id if scope.is_regional else region_id
    effective_inst_id = scope.institution_id if scope.is_institution else institution_id

    if report_type in ["regional_performance", "regional-performance", "REGIONAL_PERFORMANCE"]:
        data = ReportsService.get_regional_performance_report(db)
        canon_type = "regional_performance"
    elif report_type in ["pendency", "PENDENCY"]:
        data = ReportsService.get_pendency_report(db, region_id=effective_reg_id)
        canon_type = "pendency"
    elif report_type in ["overdue", "overdue_cases", "OVERDUE"]:
        data = ReportsService.get_overdue_cases_report(db, region_id=effective_reg_id, institution_id=effective_inst_id, item_type=item_type)
        canon_type = "overdue"
    else:
        raise HTTPException(status_code=400, detail="PDF export currently supported for 'regional_performance', 'pendency', and 'overdue'")

    pdf_bytes = ReportsService.export_pdf(canon_type, data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="aicte_{canon_type}_report.pdf"'}
    )


@router.get("/institutions/{institution_id}/health")
def get_institution_health(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    360-degree Institution Compliance Health Dossier:
    Applications, open undertakings, document expiries, open alerts, compliance score, and complaint history.
    """
    if scope.is_institution and scope.institution_id != institution_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot view another institution's compliance health")

    return ReportsService.get_institution_health_dossier(db, institution_id)
