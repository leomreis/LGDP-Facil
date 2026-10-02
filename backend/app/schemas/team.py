from pydantic import BaseModel, EmailStr


class TeamInviteCreate(BaseModel):
    email: EmailStr
    name: str
