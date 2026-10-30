from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserRead


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, examples=["Looks good, moving to review"])


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    text: str
    author: UserRead
    created_at: datetime
