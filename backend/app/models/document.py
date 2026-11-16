import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), nullable=False)
    department = Column(String(64), default="General", index=True, nullable=False)
    uploader_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content_version = Column(Integer, default=1, nullable=False)
    indexing_status = Column(String(32), default="pending", index=True, nullable=False) # pending, indexing, ready, failed, deleted
    is_tombstoned = Column(Boolean, default=False, index=True, nullable=False)
    tombstoned_at = Column(DateTime, nullable=True)
    raw_text = Column(Text, nullable=False)
    file_path = Column(String(512), nullable=True)
    file_size = Column(Integer, default=0, nullable=False)
    mime_type = Column(String(64), default="text/plain", nullable=False)
    acl_epoch = Column(Integer, default=1, nullable=False) # increments on permission or content mutation
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    uploader = relationship("User", back_populates="documents")
    acls = relationship("DocumentACL", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentACL(Base):
    __tablename__ = "document_acls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    principal_id = Column(String(128), nullable=False, index=True) # simulated principal or user
    permission_level = Column(String(32), default="read", nullable=False) # read, write, admin
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="acls")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_id = Column(String(128), unique=True, index=True, nullable=False) # e.g. doc_123_v1_c0
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    embedding_id = Column(String(128), nullable=True)
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="chunks")
