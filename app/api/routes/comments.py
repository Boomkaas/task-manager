from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, get_current_user
from app.models import Comment
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.pagination import Page
from app.services.comment_service import CommentService

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])


@router.post("", response_model=CommentRead, status_code=201)
async def create_comment(
    task_id: int,
    comment_data: CommentCreate,
    session: DbSession,
    current_user: CurrentUser,
) -> Comment:
    return await CommentService(session).create_comment(
        task_id, comment_data, current_user
    )


@router.get("", dependencies=[Depends(get_current_user)])
async def get_comments(
    task_id: int,
    session: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Page[CommentRead]:
    return await CommentService(session).get_comments(task_id, page, size)
