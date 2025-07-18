from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from uuid import UUID
from datetime import datetime


class DocumentBase(BaseModel):
    category_id: Optional[UUID] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentWithCategory(DocumentResponse):
    """Extended response that includes category information"""

    category: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
