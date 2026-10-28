from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import get_current_user, UserScope, get_user_scope
from app.models import User, UploadedFile
from app.schemas import UploadedFileOut
from app.services.file_service import FileStorageService

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=UploadedFileOut)
def upload_file(
    file: UploadFile = File(...),
    entity_type: Optional[str] = Form(None),
    entity_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document or evidence file (PDF, PNG, JPG).
    Enforces format, size limit (10MB), sanitizes filename and calculates SHA-256 hash.
    """
    uploaded_file = FileStorageService.save_file(
        db=db,
        file=file,
        uploaded_by=current_user,
        entity_type=entity_type,
        entity_id=entity_id
    )
    return uploaded_file


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: UserScope = Depends(get_user_scope)
):
    """
    Download an authorized uploaded file.
    Non-public endpoint enforcing authentication and data access scope.
    """
    uploaded_file, file_path = FileStorageService.get_file_for_download(
        db=db,
        file_id=file_id,
        user=current_user
    )

    return FileResponse(
        path=str(file_path),
        filename=uploaded_file.original_filename,
        media_type=uploaded_file.mime_type
    )
