from uuid import UUID

from domain.schemas import (
    OAuthUserInfo,
    TokenPair,
    UserCreate,
    UserResponse,
)
from infrastructure.repositories.refresh_token import RefreshTokenRepository
from infrastructure.repositories.user import UserRepository
from infrastructure.security.jwt_service import JWTService


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        jwt_service: JWTService,
    ):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.jwt_service = jwt_service

    async def authenticate_with_oauth(
        self,
        oauth_user: OAuthUserInfo,
        device_info: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[TokenPair, UserResponse]:
        user = await self.user_repo.get_by_oauth(
            provider=oauth_user.provider,
            oauth_id=oauth_user.oauth_id,
        )

        if not user:
            user = await self.user_repo.get_by_email(oauth_user.email)

        if not user:
            user_create = UserCreate(
                email=oauth_user.email,
                username=oauth_user.username,
                oauth_provider=oauth_user.provider,
                oauth_id=oauth_user.oauth_id,
                avatar_url=oauth_user.avatar_url,
            )
            user = await self.user_repo.create(user_create)

        await self.user_repo.update_last_login(user.id)

        token_pair, token_hash, expires_at = self.jwt_service.create_token_pair(user)

        await self.refresh_token_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )

        return token_pair, UserResponse.model_validate(user)

    async def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[TokenPair, UserResponse]:
        try:
            payload = self.jwt_service.verify_refresh_token(refresh_token)
        except ValueError as e:
            raise ValueError('Invalid refresh token') from e

        token_hash = self.jwt_service.hash_token(refresh_token)
        stored_token = await self.refresh_token_repo.get_by_hash(token_hash)

        if not stored_token:
            raise ValueError('Refresh token not found or revoked')

        user_id = UUID(payload.sub)
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise ValueError('User not found')

        await self.refresh_token_repo.revoke(token_hash)

        token_pair, new_token_hash, expires_at = self.jwt_service.create_token_pair(user)

        await self.refresh_token_repo.create(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=expires_at,
            device_info=stored_token.device_info,
            ip_address=stored_token.ip_address,
        )

        return token_pair, UserResponse.model_validate(user)

    async def logout(self, refresh_token: str) -> None:
        token_hash = self.jwt_service.hash_token(refresh_token)
        await self.refresh_token_repo.revoke(token_hash)

    async def get_current_user(self, user_id: UUID) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError('User not found')
        return UserResponse.model_validate(user)
