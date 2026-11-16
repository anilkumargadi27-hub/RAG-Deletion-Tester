import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.document import Document, DocumentChunk, DocumentACL
from backend.app.services.vector_store import vector_store_service

class RetrievalService:
    def retrieve_permitted_chunks(
        self,
        db: Session,
        query: str,
        principal_id: str,
        collection_name: str = "production_documents",
        top_k: int = 4,
        force_fault_stale_index: bool = False,
        force_tfidf: bool = False
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieves document chunks, enforcing authoritative database permission checks
        and tombstone verification unless force_fault_stale_index is active.
        """
        trace = {
            "layer": "retrieval",
            "consulted": True,
            "contributed": False,
            "retrieved_count": 0,
            "permitted_count": 0,
            "rejected_count": 0,
            "rejections": [],
            "retrieval_mode": "semantic_vector"
        }

        # 1. Retrieve raw candidate chunks from vector store / TF-IDF
        raw_candidates = vector_store_service.search(
            collection_name=collection_name,
            query=query,
            top_k=top_k,
            force_tfidf=force_tfidf
        )

        trace["retrieved_count"] = len(raw_candidates)
        if raw_candidates:
            trace["retrieval_mode"] = raw_candidates[0].get("retrieval_mode", "semantic_vector")

        permitted_chunks = []

        for cand in raw_candidates:
            chunk_id = cand["chunk_id"]
            meta = cand.get("metadata", {})
            doc_id = meta.get("document_id")

            if not doc_id:
                # Try finding from DB chunk table
                db_chunk = db.query(DocumentChunk).filter(DocumentChunk.chunk_id == chunk_id).first()
                if db_chunk:
                    doc_id = db_chunk.document_id

            if not doc_id:
                trace["rejected_count"] += 1
                trace["rejections"].append({"chunk_id": chunk_id, "reason": "No document ID found"})
                continue

            # Query authoritative current state from Database
            doc = db.query(Document).filter(Document.id == doc_id).first()

            if force_fault_stale_index:
                # FAULT INJECTION MODE:
                # Simulates stale vector index where deleted/revoked document chunk was not purged
                # and retrieval authorizer failed to check DB tombstone.
                cand["authoritative_doc_title"] = doc.title if doc else meta.get("title", "Unknown")
                cand["document_id"] = doc_id
                cand["acl_epoch"] = doc.acl_epoch if doc else 0
                permitted_chunks.append(cand)
                continue

            # SECURE PIPELINE:
            # Recheck tombstone and status
            if not doc or doc.is_tombstoned or doc.indexing_status != "ready":
                trace["rejected_count"] += 1
                trace["rejections"].append({
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "reason": "Document tombstoned or not ready"
                })
                continue

            # Check ACL authorization for principal
            has_access = self._check_principal_access(db, doc, principal_id)
            if not has_access:
                trace["rejected_count"] += 1
                trace["rejections"].append({
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "principal_id": principal_id,
                    "reason": "Principal access revoked or not granted"
                })
                continue

            # Permitted
            cand["authoritative_doc_title"] = doc.title
            cand["document_id"] = doc.id
            cand["acl_epoch"] = doc.acl_epoch
            permitted_chunks.append(cand)

        trace["permitted_count"] = len(permitted_chunks)
        trace["contributed"] = len(permitted_chunks) > 0
        return permitted_chunks, trace

    def _check_principal_access(self, db: Session, doc: Document, principal_id: str) -> bool:
        """Check whether principal_id has active read permission on doc."""
        # System admin or open public docs
        if principal_id in ["admin", "system"]:
            return True

        # Check explicit ACL
        acl = db.query(DocumentACL).filter(
            DocumentACL.document_id == doc.id,
            DocumentACL.principal_id == principal_id,
            DocumentACL.is_active == True,
            DocumentACL.revoked_at.is_(None)
        ).first()

        if acl:
            return True

        # Check wildcard or department match if granted
        group_acl = db.query(DocumentACL).filter(
            DocumentACL.document_id == doc.id,
            DocumentACL.principal_id.in_(["*", "all_employees", f"dept_{doc.department.lower()}"]),
            DocumentACL.is_active == True,
            DocumentACL.revoked_at.is_(None)
        ).first()

        return group_acl is not None

retrieval_service = RetrievalService()
