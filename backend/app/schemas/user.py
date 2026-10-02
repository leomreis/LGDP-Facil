import uuid
from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    email: str
    role: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True
