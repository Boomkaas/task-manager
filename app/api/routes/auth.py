from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DbSession
from app.models import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(user_data: UserCreate, session: DbSession) -> User:
    return await AuthService(session).register(user_data)


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: DbSession
) -> Token:
    access_token = await AuthService(session).login(
        form_data.username, form_data.password
    )
    return Token(access_token=access_token)
