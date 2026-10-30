from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, get_current_user
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUser) -> User:
    return current_user


@router.get("", response_model=list[UserRead], dependencies=[Depends(get_current_user)])
async def get_users(session: DbSession) -> list[User]:
    return await UserRepository(session).get_all()
