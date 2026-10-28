"""
File Storage Service for SIH26262.
Provides an abstraction for file uploads, SHA256 integrity validation,
safe file sanitization, and authorized download serving.
"""
import os
import re
import uuid
import hashlib
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models import UploadedFile, User, UserRoleEnum, Institution, Application, Undertaking, Document
from app.services.audit import AuditService

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


class FileStorageService:
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitizes filename against path traversal and special characters."""
        clean = os.path.basename(filename)
        clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", clean)
        return clean or "unnamed_file"

    @staticmethod
    def save_file(
        db: Session,
        file: UploadFile,
        uploaded_by: User,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> UploadedFile:
        """
        Validates, calculates SHA256 checksum, stores on filesystem, and logs DB artifact.
        """
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        raw_name = file.filename or "upload.bin"
        sanitized_name = FileStorageService._sanitize_filename(raw_name)
        _, ext = os.path.splitext(sanitized_name)
        ext_lower = ext.lower()

        if ext_lower not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{ext}'. Allowed extensions: PDF, PNG, JPG.",
            )

        # Read content to memory to compute checksum & validate size
        content = file.file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file upload is not permitted.",
            )

        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
            )

        # Content-type validation
        mime_type = file.content_type or "application/octet-stream"
        if mime_type not in ALLOWED_MIME_TYPES and ext_lower != ".pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Disallowed MIME type '{mime_type}'.",
            )

        # Compute SHA256 checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Stored unique filename
        unique_prefix = uuid.uuid4().hex[:12]
        stored_filename = f"{unique_prefix}_{sanitized_name}"
        destination_path = os.path.join(UPLOAD_DIR, stored_filename)

        with open(destination_path, "wb") as f:
            f.write(content)

        # Record in database
        uploaded_record = UploadedFile(
            original_filename=sanitized_name,
            stored_filename=stored_filename,
            file_path=destination_path,
            file_size_bytes=file_size,
            mime_type=mime_type,
            checksum_sha256=checksum,
            entity_type=entity_type,
            entity_id=entity_id,
            uploaded_by=uploaded_by.id,
        )
        db.add(uploaded_record)
        db.commit()
        db.refresh(uploaded_record)

        AuditService.log(
            db=db,
            table_name="uploaded_files",
            record_id=uploaded_record.id,
            action="FILE_UPLOADED",
            actor_id=uploaded_by.id,
            new_values={
                "filename": sanitized_name,
                "size": file_size,
                "sha256": checksum,
                "entity": f"{entity_type}:{entity_id}",
            },
        )

        return uploaded_record

    @staticmethod
    def get_file_for_download(db: Session, file_id: int, user: User) -> Tuple[UploadedFile, str]:
        """
        Retrieves file with RBAC scoping:
        - Admin & Central officers can access all files
        - Regional officers can access files in their region
        - Institution users can ONLY access files belonging to their institution
        """
        record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="File not found")

        # RBAC Check
        role_code = user.role.code if user.role else ""
        if role_code == "INSTITUTION_USER":
            # Must verify entity belongs to this institution
            is_authorized = False
            if record.uploaded_by == user.id:
                is_authorized = True
            elif record.entity_type == "UNDERTAKING_EVIDENCE" and record.entity_id:
                ut = db.query(Undertaking).filter(Undertaking.id == record.entity_id).first()
                if ut and ut.institution_id == user.institution_id:
                    is_authorized = True
            elif record.entity_type == "DOCUMENT_RENEWAL" and record.entity_id:
                doc = db.query(Document).filter(Document.id == record.entity_id).first()
                if doc and doc.institution_id == user.institution_id:
                    is_authorized = True

            if not is_authorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: file does not belong to your institution.",
                )

        if not os.path.exists(record.file_path):
            raise HTTPException(status_code=404, detail="File content missing on storage volume")

        return record, record.file_path
