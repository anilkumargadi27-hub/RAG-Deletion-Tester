import os
import shutil
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.document import Document, DocumentACL, DocumentChunk
from backend.app.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentDetailResponse,
    DocumentACLUpdateRequest, DocumentACLItem
)
from backend.app.core.security import get_current_user, require_roles
from backend.app.services.document_service import document_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])

def _format_doc_response(doc: Document) -> DocumentResponse:
    principals = [a.principal_id for a in doc.acls if a.is_active]
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        department=doc.department,
        content_version=doc.content_version,
        indexing_status=doc.indexing_status,
        is_tombstoned=doc.is_tombstoned,
        tombstoned_at=doc.tombstoned_at,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        acl_epoch=doc.acl_epoch,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        permitted_principals=principals
    )

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document)
    if not include_deleted:
        query = query.filter(Document.is_tombstoned == False)

    # Admin and Auditor see all docs; Members see only their permitted docs
    docs = query.order_by(Document.created_at.desc()).all()
    if current_user.role in ["admin", "auditor"]:
        return [_format_doc_response(d) for d in docs]

    # Member: filter by active ACL containing username or member groups
    permitted = []
    for d in docs:
        active_principals = {a.principal_id for a in d.acls if a.is_active}
        if any(p in active_principals for p in [current_user.username, "general_employee", "*"]):
            permitted.append(d)
    return [_format_doc_response(d) for d in permitted]

@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if doc.is_tombstoned and current_user.role != "admin":
        raise HTTPException(status_code=404, detail="Document is deleted and inaccessible.")

    # Check permission for member
    if current_user.role == "member":
        active_principals = {a.principal_id for a in doc.acls if a.is_active}
        if not any(p in active_principals for p in [current_user.username, "general_employee", "*"]):
            raise HTTPException(status_code=403, detail="Access denied to this document.")

    chunks_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    principals = [a.principal_id for a in doc.acls if a.is_active]
    acls_list = [DocumentACLItem.model_validate(a) for a in doc.acls]

    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        department=doc.department,
        content_version=doc.content_version,
        indexing_status=doc.indexing_status,
        is_tombstoned=doc.is_tombstoned,
        tombstoned_at=doc.tombstoned_at,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        acl_epoch=doc.acl_epoch,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        permitted_principals=principals,
        raw_text=doc.raw_text,
        chunks_count=chunks_count,
        acls=acls_list
    )

@router.post("/paste", response_model=DocumentResponse)
def ingest_pasted_text(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    doc = document_service.ingest_document(
        db=db,
        title=payload.title,
        department=payload.department,
        raw_text=payload.raw_text,
        permitted_principals=payload.permitted_principals,
        uploader_id=current_user.id,
        mime_type="text/plain"
    )
    return _format_doc_response(doc)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    department: str = Form("General"),
    permitted_principals: str = Form("general_employee"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    sanitized_name = document_service.sanitize_filename(file.filename or "upload.txt")
    save_path = settings.upload_dir / f"{uuid.uuid4().hex}_{sanitized_name}"

    # Read and validate size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds maximum allowed size (15MB).")

    with open(save_path, "wb") as f:
        f.write(contents)

    # Extract text
    mime = file.content_type or "text/plain"
    try:
        extracted_text = document_service.extract_text_from_file(save_path, mime)
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=400, detail=str(e))

    principals_list = [p.strip() for p in permitted_principals.split(",") if p.strip()]

    doc = document_service.ingest_document(
        db=db,
        title=title,
        department=department,
        raw_text=extracted_text,
        permitted_principals=principals_list,
        uploader_id=current_user.id,
        file_path=str(save_path),
        file_size=len(contents),
        mime_type=mime
    )
    return _format_doc_response(doc)

@router.put("/{document_id}/acls", response_model=DocumentResponse)
def update_document_acls(
    document_id: str,
    payload: DocumentACLUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    doc = document_service.update_acls(
        db=db,
        document_id=document_id,
        new_permitted_principals=payload.permitted_principals
    )
    return _format_doc_response(doc)

@router.delete("/{document_id}", response_model=DocumentResponse)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    doc = document_service.delete_document(db=db, document_id=document_id)
    return _format_doc_response(doc)
