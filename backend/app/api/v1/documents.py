from typing import List, Optional, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import get_current_user, UserScope, get_user_scope
from app.models import Document, DocumentStatusEnum, DocumentTypeEnum, Application, Institution, User
from app.schemas import DocumentOut, DocumentVersionOut, DocumentVerifyRenewalRequest
from app.services.document_service import DocumentService
from app.services.file_service import FileStorageService
from app.services.clock import ClockService

router = APIRouter(prefix="/documents", tags=["Document Validity"])


def enrich_document(doc: Document, db: Session) -> Dict[str, Any]:
    inst = doc.institution
    app = doc.application
    reg = inst.region if inst else (app.region if app else None)

    now = ClockService.get_now().date()
    days_left = None
    urgency = "VALID"
    if doc.expiry_date:
        days_left = (doc.expiry_date - now).days
        if days_left < 0:
            urgency = "EXPIRED"
        elif days_left <= 30:
            urgency = "CRITICAL_EXPIRING"
        elif days_left <= 60:
            urgency = "EXPIRING_SOON"
        else:
            urgency = "VALID"

    # Fetch version chain
    # Find root document or list all versions sharing this chain
    root_id = doc.id
    curr = doc
    while curr.previous_version_id:
        prev = db.query(Document).filter(Document.id == curr.previous_version_id).first()
        if not prev or prev.id == curr.id:
            break
        curr = prev
        root_id = curr.id

    # Find all docs in chain starting from root_id
    chain_docs = [curr]
    child = db.query(Document).filter(Document.previous_version_id == curr.id).first()
    while child and child.id not in [d.id for d in chain_docs]:
        chain_docs.append(child)
        child = db.query(Document).filter(Document.previous_version_id == child.id).first()

    versions_out = []
    for d in sorted(chain_docs, key=lambda x: x.version_number or 1, reverse=True):
        verifier_name = d.verifier.full_name if getattr(d, "verifier", None) else None
        file_name = d.uploaded_file.original_name if getattr(d, "uploaded_file", None) else None
        versions_out.append({
            "id": d.id,
            "document_type": d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type),
            "title": d.title,
            "document_number": d.document_number,
            "file_id": d.renewal_file_id or getattr(d, "file_id", None),
            "file_name": file_name,
            "version_number": d.version_number or 1,
            "issue_date": d.issue_date,
            "expiry_date": d.expiry_date,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "verified_by_name": verifier_name,
            "created_at": d.created_at,
        })

    active_file_id = doc.renewal_file_id or getattr(doc, "file_id", None)
    active_file_name = doc.uploaded_file.original_name if getattr(doc, "uploaded_file", None) else None

    return {
        "id": doc.id,
        "institution_id": doc.institution_id,
        "institution_name": inst.name if inst else None,
        "region_id": reg.id if reg else None,
        "region_name": reg.name if reg else None,
        "application_id": doc.application_id,
        "document_type": doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type),
        "title": doc.title,
        "document_number": doc.document_number,
        "file_id": active_file_id,
        "file_name": active_file_name,
        "version_number": doc.version_number or 1,
        "previous_version_id": doc.previous_version_id,
        "issue_date": doc.issue_date,
        "expiry_date": doc.expiry_date,
        "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        "verified_by": doc.verified_by,
        "verified_by_name": doc.verifier.full_name if getattr(doc, "verifier", None) else None,
        "verification_remarks": doc.verification_remarks,
        "verified_at": doc.last_verified_at,
        "days_until_expiry": days_left,
        "urgency_bucket": urgency,
        "history": versions_out,
    }


@router.get("")
def list_documents(
    document_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    urgency_filter: Optional[str] = Query(None, alias="urgency"),
    region_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    include_superseded: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    List documents with versioning and validity tracking.
    Institution users only see their own institution's documents.
    """
    query = db.query(Document).join(Institution, Document.institution_id == Institution.id)

    if scope.is_institution:
        query = query.filter(Document.institution_id == scope.institution_id)
    elif scope.is_regional and scope.region_id:
        query = query.filter(Institution.region_id == scope.region_id)

    if region_id and scope.is_national:
        query = query.filter(Institution.region_id == region_id)

    if institution_id and not scope.is_institution:
        query = query.filter(Document.institution_id == institution_id)

    if not include_superseded:
        # Default to showing current versions
        query = query.filter(Document.status != DocumentStatusEnum.SUPERSEDED)

    if document_type:
        query = query.filter(Document.document_type == document_type)

    if status_filter:
        query = query.filter(Document.status == status_filter)

    now = ClockService.get_now().date()
    if urgency_filter == "EXPIRED":
        query = query.filter(Document.expiry_date < now)
    elif urgency_filter == "CRITICAL":
        from datetime import timedelta
        query = query.filter(Document.expiry_date >= now, Document.expiry_date <= now + timedelta(days=30))
    elif urgency_filter == "EXPIRING":
        from datetime import timedelta
        query = query.filter(Document.expiry_date >= now, Document.expiry_date <= now + timedelta(days=60))

    docs = query.order_by(Document.expiry_date.asc().nullslast()).all()
    return [enrich_document(d, db) for d in docs]


@router.get("/{document_id}")
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if scope.is_institution and doc.institution_id != scope.institution_id:
        raise HTTPException(status_code=403, detail="Access denied: Cannot view another institution's documents")

    return enrich_document(doc, db)


@router.post("/{document_id}/upload-renewal")
def upload_renewal(
    document_id: int,
    new_expiry_date: date = Form(...),
    new_issue_date: Optional[date] = Form(None),
    issuing_authority: Optional[str] = Form(None),
    document_number: Optional[str] = Form(None),
    renewal_notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    file_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Institution uploads renewal dossier:
    - Creates a NEW version (e.g., v2).
    - Keeps old version marked RENEWAL_SUBMITTED.
    - Linked alerts stay open with status 'Renewal submitted, awaiting verification'.
    """
    final_file_id = file_id
    if file:
        uploaded = FileStorageService.save_file(
            db=db,
            file=file,
            uploaded_by=current_user,
            entity_type="DOCUMENT_RENEWAL",
            entity_id=document_id
        )
        final_file_id = uploaded.id

    effective_issue_date = new_issue_date or ClockService.get_now().date()
    effective_authority = issuing_authority or "Competent Issuing Authority"

    new_doc = DocumentService.upload_renewal(
        db=db,
        document_id=document_id,
        new_expiry_date=new_expiry_date,
        new_issue_date=effective_issue_date,
        issuing_authority=effective_authority,
        document_number=document_number,
        renewal_notes=renewal_notes,
        renewal_file_id=final_file_id,
        actor=current_user
    )

    return enrich_document(new_doc, db)


@router.post("/{document_id}/verify-renewal")
def verify_renewal(
    document_id: int,
    payload: DocumentVerifyRenewalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Officer verifies renewal dossier:
    - If approved: old version becomes SUPERSEDED, new version becomes VALID, linked alerts auto-resolve.
    - If rejected: new version marked EXPIRED, old version reverts to EXPIRED.
    """
    updated_doc = DocumentService.verify_renewal(
        db=db,
        new_document_id=document_id,
        is_approved=payload.is_approved,
        remarks=payload.remarks or ("Renewal approved by scrutiny officer" if payload.is_approved else "Renewal rejected"),
        actor=current_user
    )

    return enrich_document(updated_doc, db)
