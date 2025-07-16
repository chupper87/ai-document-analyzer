from pydantic import BaseModel
from datetime import datetime
import uuid


class CategoryCreate(BaseModel):
    name: str
    color: str = "#3B82F6"  # Default Color


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
