from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.schemas import UserCreate, UserUpdate
from infrastructure.models import OAuthProvider, User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_oauth(self, provider: OAuthProvider, oauth_id: str) -> User | None:
        result = await self._session.execute(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_id == oauth_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user_data: UserCreate) -> User | None:
        user = User(
            email=user_data.email,
            username=user_data.username,
            oauth_provider=user_data.oauth_provider,
            oauth_id=user_data.oauth_id,
            avatar_url=user_data.avatar_url,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def update(self, user_id: UUID, user_data: UserUpdate) -> User | None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**user_data.model_dump(exclude_unset=True))
            .returning(User)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: UUID) -> User | None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.now())
        )
        await self._session.commit()

