from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class DocumentCreate(BaseModel):
    title: str
    department: str = "General"
    raw_text: str
    permitted_principals: List[str] = ["general_employee"]

class DocumentACLItem(BaseModel):
    id: str
    principal_id: str
    permission_level: str
    is_active: bool
    granted_at: datetime
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: str
    title: str
    department: str
    content_version: int
    indexing_status: str
    is_tombstoned: bool
    tombstoned_at: Optional[datetime] = None
    file_size: int
    mime_type: str
    acl_epoch: int
    created_at: datetime
    updated_at: datetime
    permitted_principals: List[str] = []

    class Config:
        from_attributes = True

class DocumentDetailResponse(DocumentResponse):
    raw_text: str
    chunks_count: int = 0
    acls: List[DocumentACLItem] = []

class DocumentACLUpdateRequest(BaseModel):
    permitted_principals: List[str]

class CitationItem(BaseModel):
    document_id: str
    document_title: str
    chunk_id: str
    snippet: str

class SearchResultItem(BaseModel):
    document_id: str
    document_title: str
    department: str
    chunk_id: str
    content: str
    score: float
    retrieval_mode: str
