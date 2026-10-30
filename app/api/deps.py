from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: DbSession
) -> User:
    user_id = decode_access_token(token)
    if user_id is None:
        raise AuthenticationError("Invalid or expired token", "invalid_token")

    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found", "invalid_token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
