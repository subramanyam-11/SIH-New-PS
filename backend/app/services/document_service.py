"""
Statutory Document Validity & Versioning Service for SIH26262.
Enforces multi-version tracking, supersede chains, and conditional alert resolution
strictly upon authorized officer verification.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import (
    Document, DocumentStatusEnum, DocumentTypeEnum,
    User, UserRoleEnum, Alert, AlertStatusEnum, Application, Institution, UploadedFile
)
from app.services.clock import ClockService
from app.services.audit import AuditService


class DocumentService:
    @staticmethod
    def upload_renewal(
        db: Session,
        document_id: int,
        new_expiry_date: date,
        new_issue_date: date,
        issuing_authority: str,
        document_number: Optional[str],
        renewal_notes: Optional[str],
        renewal_file_id: Optional[int],
        actor: User
    ) -> Document:
        """
        Creates a new version of the document in RENEWAL_SUBMITTED status.
        Marks existing version as RENEWAL_SUBMITTED.
        Does NOT auto-resolve alerts yet; sets interim state 'Renewal submitted, awaiting verification'.
        """
        old_doc = db.query(Document).filter(Document.id == document_id).first()
        if not old_doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Institution scoping
        if actor.role.code == "INSTITUTION_USER" and old_doc.institution_id != actor.institution_id:
            raise HTTPException(status_code=403, detail="Cannot upload renewal for another institution's document")

        now = ClockService.get_now()
        old_doc.status = DocumentStatusEnum.RENEWAL_SUBMITTED
        old_doc.renewal_notes = renewal_notes or "Renewal dossier submitted. Awaiting scrutiny verification."

        # Create new version
        new_version_num = (old_doc.version_number or 1) + 1
        new_doc = Document(
            institution_id=old_doc.institution_id,
            application_id=old_doc.application_id,
            document_type=old_doc.document_type,
            document_number=document_number or old_doc.document_number,
            title=f"{old_doc.title} (v{new_version_num})",
            issuing_authority=issuing_authority or old_doc.issuing_authority,
            issue_date=new_issue_date,
            expiry_date=new_expiry_date,
            status=DocumentStatusEnum.RENEWAL_SUBMITTED,
            version_number=new_version_num,
            previous_version_id=old_doc.id,
            renewal_file_id=renewal_file_id,
            renewal_notes=renewal_notes,
            created_at=now,
        )
        db.add(new_doc)
        db.flush()

        # Update linked active alerts to indicate renewal submitted awaiting verification
        alerts = db.query(Alert).filter(
            Alert.document_id == old_doc.id,
            Alert.status != AlertStatusEnum.RESOLVED
        ).all()
        for alt in alerts:
            alt.message = f"[Renewal Submitted] {alt.title}. Awaiting regional scrutiny verification."
            if isinstance(alt.explanation_meta, dict):
                alt.explanation_meta["renewal_status"] = "Renewal submitted, awaiting verification"

        AuditService.log(
            db=db,
            table_name="documents",
            record_id=new_doc.id,
            action="DOCUMENT_RENEWAL_SUBMITTED",
            actor_id=actor.id,
            new_values={
                "previous_id": old_doc.id,
                "version": new_version_num,
                "new_expiry": new_expiry_date.isoformat(),
            },
        )

        db.commit()
        db.refresh(new_doc)
        return new_doc

    @staticmethod
    def verify_renewal(
        db: Session,
        new_document_id: int,
        is_approved: bool,
        remarks: str,
        actor: User
    ) -> Document:
        """
        Officer verifies renewal dossier.
        If approved:
          - Old document marked SUPERSEDED
          - New document marked VALID
          - Linked alerts auto-resolved with recorded reason
        If rejected:
          - New document marked EXPIRED/REJECTED
          - Old document reverts to EXPIRED
        """
        role_code = actor.role.code if actor.role else ""
        if role_code not in ["ADMIN", "REGIONAL_HEAD", "SCRUTINY_OFFICER", "COMPETENT_AUTHORITY"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorized scrutiny officers or regional heads can verify document renewals.",
            )

        if not remarks or len(remarks.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Substantive verification remarks (at least 5 characters) are mandatory.",
            )

        new_doc = db.query(Document).filter(Document.id == new_document_id).first()
        if not new_doc:
            raise HTTPException(status_code=404, detail="Renewal document record not found")

        old_doc = None
        if new_doc.previous_version_id:
            old_doc = db.query(Document).filter(Document.id == new_doc.previous_version_id).first()

        now = ClockService.get_now()

        if is_approved:
            # 1. Supersede old document
            if old_doc:
                old_doc.status = DocumentStatusEnum.SUPERSEDED
                old_doc.last_verified_at = now
                old_doc.verification_remarks = f"Superseded by renewed v{new_doc.version_number}."

            # 2. Activate new document
            new_doc.status = DocumentStatusEnum.VALID
            new_doc.verified_by = actor.id
            new_doc.last_verified_at = now
            new_doc.verification_remarks = remarks

            # 3. Auto-resolve alerts linked to old document or new document
            doc_ids = [new_doc.id]
            if old_doc:
                doc_ids.append(old_doc.id)

            alerts = db.query(Alert).filter(
                Alert.document_id.in_(doc_ids),
                Alert.status != AlertStatusEnum.RESOLVED
            ).all()

            for alt in alerts:
                alt.status = AlertStatusEnum.RESOLVED
                alt.resolved_at = now
                alt.resolved_by = actor.id
                alt.resolution_remarks = f"Renewal verified by Officer {actor.full_name}: {remarks}. New valid expiry date: {new_doc.expiry_date.isoformat()}."

        else:
            # Renewal rejected
            new_doc.status = DocumentStatusEnum.EXPIRED
            new_doc.verified_by = actor.id
            new_doc.verification_remarks = f"Renewal Rejected: {remarks}"
            if old_doc:
                old_doc.status = DocumentStatusEnum.EXPIRED

        AuditService.log(
            db=db,
            table_name="documents",
            record_id=new_doc.id,
            action="DOCUMENT_RENEWAL_VERIFIED",
            actor_id=actor.id,
            new_values={
                "is_approved": is_approved,
                "status": new_doc.status.value,
                "remarks": remarks,
            },
        )

        db.commit()
        db.refresh(new_doc)
        return new_doc
