import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import UUID

import jwt
from pydantic import SecretStr

from domain.schemas import (
    AccessTokenPayload,
    RefreshTokenPayload,
    TokenPair,
)
from infrastructure.models import User


class JWTService:
    def __init__(
        self,
        secret_key: SecretStr,
        algorithm: str = 'HS256',
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30,
    ):
        self.secret_key = secret_key.get_secret_value()
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(self, user: User) -> str:
        now = datetime.now()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = AccessTokenPayload(
            sub=str(user.id),
            email=user.email,
            role=user.role,
            exp=int(expire.timestamp()),
        )

        return jwt.encode(
            payload.model_dump(),
            self.secret_key,
            algorithm=self.algorithm,
        )

    def create_refresh_token(self, user_id: UUID) -> tuple[str, str, datetime]:
        now = datetime.now()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        jti = secrets.token_urlsafe(32)

        payload = RefreshTokenPayload(
            sub=str(user_id),
            jti=jti,
            exp=int(expire.timestamp()),
        )

        token = jwt.encode(
            payload.model_dump(),
            self.secret_key,
            algorithm=self.algorithm,
        )

        token_hash = self._hash_token(token)

        return token, token_hash, expire

    def create_token_pair(self, user: User) -> tuple[TokenPair, str, datetime]:
        access_token = self.create_access_token(user)
        refresh_token, token_hash, expires_at = self.create_refresh_token(user.id)

        return (
            TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
            ),
            token_hash,
            expires_at,
        )

    def verify_access_token(self, token: str) -> AccessTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return AccessTokenPayload(**payload)
        except jwt.InvalidTokenError as e:
            raise ValueError(f'Invalid access token: {str(e)}')

    def verify_refresh_token(self, token: str) -> RefreshTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return RefreshTokenPayload(**payload)
        except jwt.InvalidTokenError as e:
            raise ValueError(f'Invalid refresh token: {str(e)}')

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def hash_token(self, token: str) -> str:
        return self._hash_token(token)
