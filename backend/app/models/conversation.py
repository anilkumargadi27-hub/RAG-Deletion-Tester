import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    principal_id = Column(String(128), default="general_employee", nullable=False, index=True)
    title = Column(String(256), default="New Chat Session", nullable=False)
    is_invalidated = Column(Boolean, default=False, nullable=False, index=True)
    invalidated_reason = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan", order_by="ConversationMessage.created_at")

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    citations_json = Column(Text, default="[]", nullable=False)
    provenance_json = Column(Text, default="{}", nullable=False) # source doc IDs, versions, chunk IDs
    is_pruned = Column(Boolean, default=False, nullable=False) # true if context invalidated due to deletion/revocation
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ConversationSession", back_populates="messages")
