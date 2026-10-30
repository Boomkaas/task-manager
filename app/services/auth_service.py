from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, BusinessRuleError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repository = UserRepository(session)

    async def register(self, user_data: UserCreate) -> User:
        if await self.user_repository.get_by_email(user_data.email):
            raise BusinessRuleError("Email is already registered", "email_taken")
        if await self.user_repository.get_by_username(user_data.username):
            raise BusinessRuleError("Username is already taken", "username_taken")

        return await self.user_repository.create(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hash_password(user_data.password),
        )

    async def login(self, username: str, password: str) -> str:
        user = await self.user_repository.get_by_username(username)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError(
                "Incorrect username or password", "invalid_credentials"
            )
        return create_access_token(user.id)
