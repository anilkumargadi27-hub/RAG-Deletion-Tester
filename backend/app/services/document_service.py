import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from backend.app.config import settings
from backend.app.models.document import Document, DocumentChunk, DocumentACL
from backend.app.models.synthetic import CleanupJob
from backend.app.services.vector_store import vector_store_service
from backend.app.services.cache_service import cache_service
from backend.app.services.session_service import session_service

class DocumentService:
    def sanitize_filename(self, filename: str) -> str:
        name = os.path.basename(filename)
        clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
        return clean or "uploaded_document.txt"

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        chunks = []
        start = 0
        text_len = len(text)
        if text_len <= chunk_size:
            return [text.strip()] if text.strip() else []

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_len:
                break
            start += (chunk_size - overlap)
        return chunks

    def extract_text_from_file(self, file_path: Path, mime_type: str) -> str:
        if "pdf" in mime_type.lower() or file_path.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            try:
                reader = PdfReader(str(file_path))
                text_parts = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                extracted = "\n".join(text_parts).strip()
                if not extracted:
                    raise ValueError(
                        "Scanned or image-only PDF detected with no extractable text. OCR is not supported; please provide a text-based document."
                    )
                return extracted
            except Exception as e:
                if "Scanned or image-only" in str(e):
                    raise
                raise ValueError(f"Could not read PDF document: {str(e)}")
        else:
            # Plain text / Markdown
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"Failed to read text file: {str(e)}")

    def ingest_document(
        self,
        db: Session,
        title: str,
        department: str,
        raw_text: str,
        permitted_principals: List[str],
        uploader_id: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size: int = 0,
        mime_type: str = "text/plain",
        collection_name: str = "production_documents"
    ) -> Document:
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Document content cannot be empty.")

        doc = Document(
            title=title.strip(),
            department=department.strip(),
            uploader_id=uploader_id,
            content_version=1,
            indexing_status="indexing",
            is_tombstoned=False,
            raw_text=raw_text,
            file_path=file_path,
            file_size=file_size or len(raw_text.encode('utf-8')),
            mime_type=mime_type,
            acl_epoch=1
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Create ACL entries
        for principal in permitted_principals:
            clean_p = principal.strip()
            if clean_p:
                acl = DocumentACL(
                    document_id=doc.id,
                    principal_id=clean_p,
                    permission_level="read",
                    is_active=True
                )
                db.add(acl)
        db.commit()

        # Chunk and index
        try:
            chunks = self.chunk_text(raw_text)
            chunk_records = []
            vector_chunks = []
            for idx, c_text in enumerate(chunks):
                stable_chunk_id = f"doc_{doc.id}_v{doc.content_version}_c{idx}"
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    chunk_id=stable_chunk_id,
                    content=c_text,
                    token_count=len(c_text.split()),
                    metadata_json="{}"
                )
                db.add(db_chunk)
                chunk_records.append(db_chunk)
                vector_chunks.append({
                    "chunk_id": stable_chunk_id,
                    "content": c_text,
                    "metadata": {
                        "document_id": doc.id,
                        "title": doc.title,
                        "department": doc.department,
                        "chunk_index": idx,
                        "version": doc.content_version
                    }
                })
            db.commit()

            # Add to vector store
            vector_store_service.add_chunks(collection_name, vector_chunks)

            doc.indexing_status = "ready"
            db.commit()
            db.refresh(doc)
            return doc
        except Exception as e:
            doc.indexing_status = "failed"
            doc.error_message = str(e)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

    def update_acls(
        self,
        db: Session,
        document_id: str,
        new_permitted_principals: List[str]
    ) -> Document:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc or doc.is_tombstoned:
            raise HTTPException(status_code=404, detail="Document not found or already deleted.")

        # Increment ACL epoch
        doc.acl_epoch += 1

        existing_acls = db.query(DocumentACL).filter(DocumentACL.document_id == document_id).all()
        current_active = {a.principal_id: a for a in existing_acls if a.is_active}
        new_set = set(p.strip() for p in new_permitted_principals if p.strip())

        # Revoke principals no longer in new_set
        revoked_principals = []
        for p, acl in current_active.items():
            if p not in new_set:
                acl.is_active = False
                acl.revoked_at = datetime.utcnow()
                revoked_principals.append(p)
                # Invalidate dependent caches for this specific revoked principal
                cache_service.invalidate_by_document(db, document_id, principal_id=p)
                # Prune conversation messages for this principal
                session_service.invalidate_by_document(db, document_id, principal_id=p)

        # Add newly permitted principals
        for p in new_set:
            if p not in current_active:
                new_acl = DocumentACL(
                    document_id=doc.id,
                    principal_id=p,
                    permission_level="read",
                    is_active=True
                )
                db.add(new_acl)

        db.commit()
        db.refresh(doc)
        return doc

    def delete_document(
        self,
        db: Session,
        document_id: str,
        collection_name: str = "production_documents"
    ) -> Document:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        # 1. Authoritative Tombstone: Immediately block future access for all principals
        doc.is_tombstoned = True
        doc.tombstoned_at = datetime.utcnow()
        doc.indexing_status = "deleted"
        doc.acl_epoch += 1
        db.commit()

        # 2. Invalidate ALL dependent caches
        cache_service.invalidate_by_document(db, document_id)

        # 3. Prune/invalidate ALL dependent conversation sessions
        session_service.invalidate_by_document(db, document_id)

        # 4. Schedule and execute physical purge cleanup
        cleanup_job = CleanupJob(
            document_id=document_id,
            target_store="chroma",
            status="pending"
        )
        db.add(cleanup_job)
        db.commit()

        try:
            vector_store_service.delete_document_chunks(collection_name, document_id)
            cleanup_job.status = "completed"
        except Exception as e:
            cleanup_job.status = "failed"
            cleanup_job.error_message = str(e)
            cleanup_job.retry_count += 1

        db.commit()
        db.refresh(doc)
        return doc

document_service = DocumentService()
