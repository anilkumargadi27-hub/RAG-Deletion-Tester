import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from backend.app.models.cache import AnswerCache
from backend.app.models.document import Document, DocumentACL

class CacheService:
    def compute_cache_key(self, scope: str, principal_id: str, answer_mode: str, query: str) -> str:
        norm_query = query.strip().lower()
        raw = f"{scope}|{principal_id}|{answer_mode}|{norm_query}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def get_cached_answer(
        self,
        db: Session,
        query: str,
        scope: str,
        principal_id: str,
        answer_mode: str,
        force_fault_stale_cache: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieves answer from cache with authoritative dependency revalidation.
        If force_fault_stale_cache is True, revalidation is intentionally skipped.
        """
        cache_key = self.compute_cache_key(scope, principal_id, answer_mode, query)
        entry = db.query(AnswerCache).filter(
            AnswerCache.cache_key == cache_key,
            AnswerCache.is_valid == True
        ).first()

        trace = {
            "layer": "cache",
            "consulted": True,
            "contributed": False,
            "cache_hit": False,
            "revalidated": False,
            "reason": None
        }

        if not entry:
            trace["reason"] = "Cache miss (no entry found)"
            return None, trace

        if force_fault_stale_cache:
            # FAULT INJECTION: Return stale answer directly
            trace["contributed"] = True
            trace["cache_hit"] = True
            trace["revalidated"] = False
            trace["reason"] = "Fault injection active: served stale cached answer without revalidation"
            return {
                "answer_text": entry.answer_text,
                "citations": json.loads(entry.citations_json),
                "is_cache_hit": True
            }, trace

        # SECURE VALIDATION:
        # Recheck all source document dependencies against current DB state
        source_doc_ids = json.loads(entry.source_doc_ids_json)
        doc_versions = json.loads(entry.doc_versions_json)
        acl_epochs = json.loads(entry.acl_epoch_snapshot)

        is_stale = False
        stale_reasons = []

        for doc_id in source_doc_ids:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc or doc.is_tombstoned or doc.indexing_status != "ready":
                is_stale = True
                stale_reasons.append(f"Document {doc_id} is tombstoned or missing")
                break

            # Check version
            expected_ver = doc_versions.get(doc_id)
            if expected_ver is not None and doc.content_version != expected_ver:
                is_stale = True
                stale_reasons.append(f"Document {doc_id} version changed from {expected_ver} to {doc.content_version}")
                break

            # Check ACL epoch
            expected_epoch = acl_epochs.get(doc_id)
            if expected_epoch is not None and doc.acl_epoch != expected_epoch:
                is_stale = True
                stale_reasons.append(f"Document {doc_id} ACL epoch changed from {expected_epoch} to {doc.acl_epoch}")
                break

            # Verify principal permission is still active
            acl = db.query(DocumentACL).filter(
                DocumentACL.document_id == doc_id,
                DocumentACL.principal_id == principal_id,
                DocumentACL.is_active == True,
                DocumentACL.revoked_at.is_(None)
            ).first()
            if not acl and principal_id not in ["admin", "system"]:
                is_stale = True
                stale_reasons.append(f"Principal {principal_id} access revoked for document {doc_id}")
                break

        if is_stale:
            # Mark entry invalid and treat as miss
            entry.is_valid = False
            entry.invalidated_at = datetime.utcnow()
            db.commit()
            trace["reason"] = f"Cache invalidated on read: {'; '.join(stale_reasons)}"
            return None, trace

        trace["contributed"] = True
        trace["cache_hit"] = True
        trace["revalidated"] = True
        trace["reason"] = "Cache hit: all document dependencies and ACLs revalidated successfully"
        return {
            "answer_text": entry.answer_text,
            "citations": json.loads(entry.citations_json),
            "is_cache_hit": True
        }, trace

    def store_cached_answer(
        self,
        db: Session,
        query: str,
        scope: str,
        principal_id: str,
        answer_mode: str,
        answer_text: str,
        citations: List[Dict[str, Any]],
        source_docs: List[Document]
    ) -> AnswerCache:
        cache_key = self.compute_cache_key(scope, principal_id, answer_mode, query)
        source_doc_ids = [d.id for d in source_docs]
        doc_versions = {d.id: d.content_version for d in source_docs}
        acl_epochs = {d.id: d.acl_epoch for d in source_docs}

        # Check if existing entry exists
        existing = db.query(AnswerCache).filter(AnswerCache.cache_key == cache_key).first()
        if existing:
            existing.answer_text = answer_text
            existing.citations_json = json.dumps(citations)
            existing.source_doc_ids_json = json.dumps(source_doc_ids)
            existing.doc_versions_json = json.dumps(doc_versions)
            existing.acl_epoch_snapshot = json.dumps(acl_epochs)
            existing.is_valid = True
            existing.invalidated_at = None
            db.commit()
            db.refresh(existing)
            return existing

        entry = AnswerCache(
            cache_key=cache_key,
            query_text=query,
            scope=scope,
            principal_id=principal_id,
            answer_text=answer_text,
            citations_json=json.dumps(citations),
            source_doc_ids_json=json.dumps(source_doc_ids),
            doc_versions_json=json.dumps(doc_versions),
            acl_epoch_snapshot=json.dumps(acl_epochs),
            is_valid=True
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def invalidate_by_document(self, db: Session, document_id: str, principal_id: Optional[str] = None):
        """Invalidates all cached answers depending on this document."""
        entries = db.query(AnswerCache).filter(AnswerCache.is_valid == True).all()
        for e in entries:
            try:
                doc_ids = json.loads(e.source_doc_ids_json)
                if document_id in doc_ids:
                    if principal_id is None or e.principal_id == principal_id:
                        e.is_valid = False
                        e.invalidated_at = datetime.utcnow()
            except Exception:
                pass
        db.commit()

cache_service = CacheService()
