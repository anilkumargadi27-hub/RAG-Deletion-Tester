import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Index
from backend.app.database import Base

class AnswerCache(Base):
    __tablename__ = "answer_caches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cache_key = Column(String(128), unique=True, index=True, nullable=False)
    query_text = Column(Text, nullable=False)
    scope = Column(String(128), default="production", index=True, nullable=False)
    principal_id = Column(String(128), index=True, nullable=False)
    answer_text = Column(Text, nullable=False)
    citations_json = Column(Text, default="[]", nullable=False)
    source_doc_ids_json = Column(Text, default="[]", nullable=False) # list of doc IDs
    doc_versions_json = Column(Text, default="{}", nullable=False) # {doc_id: version}
    acl_epoch_snapshot = Column(Text, default="{}", nullable=False) # {doc_id: acl_epoch}
    is_valid = Column(Boolean, default=True, index=True, nullable=False)
    invalidated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_cache_scope_principal", "scope", "principal_id"),
    )
