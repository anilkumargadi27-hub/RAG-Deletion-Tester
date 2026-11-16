import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.conversation import ConversationSession, ConversationMessage
from backend.app.models.document import Document
from backend.app.schemas.chat import (
    ChatMessageRequest, ChatMessageResponse, ConversationSessionResponse
)
from backend.app.schemas.document import CitationItem
from backend.app.core.security import get_current_user
from backend.app.services.session_service import session_service
from backend.app.services.cache_service import cache_service
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.generator_service import generator_service

router = APIRouter(prefix="/api/chat", tags=["Assistant Playground"])

@router.get("/sessions", response_model=List[ConversationSessionResponse])
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = db.query(ConversationSession).filter(
        ConversationSession.user_id == current_user.id
    ).order_by(ConversationSession.updated_at.desc()).all()

    resp = []
    for s in sessions:
        msg_count = db.query(ConversationMessage).filter(ConversationMessage.session_id == s.id).count()
        resp.append(ConversationSessionResponse(
            id=s.id,
            title=s.title,
            principal_id=s.principal_id,
            is_invalidated=s.is_invalidated,
            invalidated_reason=s.invalidated_reason,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=msg_count
        ))
    return resp

@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sess = db.query(ConversationSession).filter(
        ConversationSession.id == session_id,
        ConversationSession.user_id == current_user.id
    ).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    messages, _ = session_service.get_sanitized_history(
        db=db,
        session_id=sess.id,
        principal_id=sess.principal_id,
        force_fault_stale_memory=False # Always secure in playground
    )

    return [
        {
            "id": m.id,
            "session_id": m.session_id,
            "role": m.role,
            "content": m.content,
            "citations": json.loads(m.citations_json),
            "created_at": m.created_at
        }
        for m in messages
    ]

@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Principal isolation: normal member can only chat as their own user/general_employee
    principal = payload.principal_id or "general_employee"
    if current_user.role == "member" and principal not in ["general_employee", current_user.username]:
        principal = current_user.username

    sess = session_service.get_or_create_session(
        db=db,
        user_id=current_user.id,
        session_id=payload.session_id,
        principal_id=principal
    )

    # Append user question
    session_service.append_message(
        db=db,
        session_id=sess.id,
        role="user",
        content=payload.message.strip()
    )

    mode = payload.answer_mode or "local_extractive"

    # 1. Check Answer Cache with authoritative revalidation
    cached, _ = cache_service.get_cached_answer(
        db=db,
        query=payload.message,
        scope="production",
        principal_id=principal,
        answer_mode=mode,
        force_fault_stale_cache=False
    )

    if cached:
        ans_text = cached["answer_text"]
        citations = [CitationItem(**c) for c in cached["citations"]]
        is_hit = True
        source_docs = []
    else:
        is_hit = False
        # 2. Retrieve Permitted Chunks
        chunks, _ = retrieval_service.retrieve_permitted_chunks(
            db=db,
            query=payload.message,
            principal_id=principal,
            collection_name="production_documents",
            force_fault_stale_index=False
        )

        ans_text, raw_cites, _ = generator_service.generate_answer(
            query=payload.message,
            permitted_chunks=chunks,
            answer_mode=mode
        )
        citations = [CitationItem(**c) for c in raw_cites]

        # Gather source docs for provenance
        doc_ids = list({c["document_id"] for c in raw_cites if c["document_id"] != "unknown"})
        source_docs = db.query(Document).filter(Document.id.in_(doc_ids)).all() if doc_ids else []

        # Store in cache if permitted chunks were found
        if source_docs:
            cache_service.store_cached_answer(
                db=db,
                query=payload.message,
                scope="production",
                principal_id=principal,
                answer_mode=mode,
                answer_text=ans_text,
                citations=raw_cites,
                source_docs=source_docs
            )

    # Append assistant response with provenance
    asst_msg = session_service.append_message(
        db=db,
        session_id=sess.id,
        role="assistant",
        content=ans_text,
        citations=[c.model_dump() for c in citations],
        source_docs=source_docs
    )

    return ChatMessageResponse(
        id=asst_msg.id,
        session_id=sess.id,
        role="assistant",
        content=ans_text,
        citations=citations,
        answer_mode=mode,
        is_cache_hit=is_hit,
        created_at=asst_msg.created_at
    )
