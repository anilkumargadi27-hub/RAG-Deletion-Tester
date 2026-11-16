from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from backend.app.schemas.document import CitationItem

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    principal_id: Optional[str] = "general_employee"
    answer_mode: Optional[str] = "local_extractive" # local_extractive or live_gemini

class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: List[CitationItem] = []
    answer_mode: str
    is_cache_hit: bool = False
    created_at: datetime

class ConversationSessionResponse(BaseModel):
    id: str
    title: str
    principal_id: str
    is_invalidated: bool
    invalidated_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True
