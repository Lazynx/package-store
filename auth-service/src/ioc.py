from typing import AsyncIterable

from dishka import Provider, Scope, from_context, provide
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.auth_service import AuthService
from config import Settings
from infrastructure.oauth.providers import GoogleOAuthProvider
from infrastructure.repositories.refresh_token import RefreshTokenRepository
from infrastructure.repositories.user import UserRepository
from infrastructure.resources.database import new_session_maker
from infrastructure.security.jwt_service import JWTService


class AppProvider(Provider):
    config = from_context(provides=Settings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_session_maker(self, config: Settings) -> async_sessionmaker[AsyncSession]:
        return new_session_maker(config.postgres)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with session_maker() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return UserRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_refresh_token_repository(
        self, session: AsyncSession
    ) -> RefreshTokenRepository:
        return RefreshTokenRepository(session)

    @provide(scope=Scope.APP)
    def get_jwt_service(self, config: Settings) -> JWTService:
        return JWTService(
            secret_key=config.jwt.secret_key,
            algorithm=config.jwt.algorithm,
            access_token_expire_minutes=config.jwt.access_token_expire_minutes,
            refresh_token_expire_days=config.jwt.refresh_token_expire_days,
        )

    @provide(scope=Scope.APP)
    def get_google_oauth_provider(self, config: Settings) -> GoogleOAuthProvider:
        return GoogleOAuthProvider(
            client_id=config.google_oauth.client_id,
            client_secret=config.google_oauth.client_secret,
            redirect_uri=config.google_oauth.redirect_uri,
        )

    @provide(scope=Scope.REQUEST)
    def get_auth_service(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        jwt_service: JWTService,
    ) -> AuthService:
        return AuthService(
            user_repo=user_repo,
            refresh_token_repo=refresh_token_repo,
            jwt_service=jwt_service,
        )
