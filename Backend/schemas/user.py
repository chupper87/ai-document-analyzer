from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
import uuid


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Låter Pydantic läsa från SQLAlchemy objects
