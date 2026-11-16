import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.conversation import ConversationSession, ConversationMessage
from backend.app.models.document import Document, DocumentACL

class SessionService:
    def get_or_create_session(
        self,
        db: Session,
        user_id: str,
        session_id: Optional[str] = None,
        principal_id: str = "general_employee"
    ) -> ConversationSession:
        if session_id:
            sess = db.query(ConversationSession).filter(
                ConversationSession.id == session_id,
                ConversationSession.user_id == user_id
            ).first()
            if sess:
                return sess

        new_sess = ConversationSession(
            user_id=user_id,
            principal_id=principal_id,
            title=f"Chat session ({principal_id})"
        )
        db.add(new_sess)
        db.commit()
        db.refresh(new_sess)
        return new_sess

    def append_message(
        self,
        db: Session,
        session_id: str,
        role: str,
        content: str,
        citations: List[Dict[str, Any]] = [],
        source_docs: List[Document] = []
    ) -> ConversationMessage:
        provenance = {
            "source_doc_ids": [d.id for d in source_docs],
            "doc_versions": {d.id: d.content_version for d in source_docs},
            "acl_epochs": {d.id: d.acl_epoch for d in source_docs}
        }
        msg = ConversationMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations_json=json.dumps(citations),
            provenance_json=json.dumps(provenance)
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    def get_sanitized_history(
        self,
        db: Session,
        session_id: str,
        principal_id: str,
        force_fault_stale_memory: bool = False
    ) -> Tuple[List[ConversationMessage], Dict[str, Any]]:
        """
        Retrieves conversation messages for a session.
        In secure mode, filters out messages derived from documents that are tombstoned
        or for which principal_id no longer has active permission.
        """
        trace = {
            "layer": "conversation_memory",
            "consulted": True,
            "contributed": False,
            "total_messages": 0,
            "pruned_messages": 0,
            "reason": None
        }

        messages = db.query(ConversationMessage).filter(
            ConversationMessage.session_id == session_id
        ).order_by(ConversationMessage.created_at.asc()).all()

        trace["total_messages"] = len(messages)

        if force_fault_stale_memory:
            # FAULT INJECTION: Return all messages unchanged without provenance checks
            trace["contributed"] = len(messages) > 0
            trace["reason"] = "Fault injection active: retained unpruned conversation memory"
            return messages, trace

        sanitized = []
        for msg in messages:
            try:
                prov = json.loads(msg.provenance_json)
                doc_ids = prov.get("source_doc_ids", [])
            except Exception:
                doc_ids = []

            is_invalid = False
            for doc_id in doc_ids:
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if not doc or doc.is_tombstoned:
                    is_invalid = True
                    break

                # Check ACL
                acl = db.query(DocumentACL).filter(
                    DocumentACL.document_id == doc.id,
                    DocumentACL.principal_id == principal_id,
                    DocumentACL.is_active == True,
                    DocumentACL.revoked_at.is_(None)
                ).first()
                if not acl and principal_id not in ["admin", "system"]:
                    is_invalid = True
                    break

            if is_invalid:
                trace["pruned_messages"] += 1
                msg.is_pruned = True
            else:
                sanitized.append(msg)

        db.commit()
        trace["contributed"] = len(sanitized) > 0
        trace["reason"] = f"Secure memory check complete: {trace['pruned_messages']} pruned of {trace['total_messages']}"
        return sanitized, trace

    def invalidate_by_document(self, db: Session, document_id: str, principal_id: Optional[str] = None):
        """Prunes conversation messages and marks sessions affected by document changes."""
        messages = db.query(ConversationMessage).filter(ConversationMessage.is_pruned == False).all()
        for msg in messages:
            try:
                prov = json.loads(msg.provenance_json)
                if document_id in prov.get("source_doc_ids", []):
                    # Check if session matches principal if specified
                    if principal_id:
                        sess = db.query(ConversationSession).filter(ConversationSession.id == msg.session_id).first()
                        if sess and sess.principal_id != principal_id:
                            continue
                    msg.is_pruned = True
            except Exception:
                pass
        db.commit()

session_service = SessionService()
