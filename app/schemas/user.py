from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(examples=["anna@example.com"])
    username: str = Field(min_length=3, max_length=50, examples=["anna"])
    password: str = Field(min_length=8, max_length=72, examples=["secret123"])


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    created_at: datetime
