from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from infrastructure.models import OAuthProvider, UserRole


class UserBase(BaseModel):
    email: str
    username: str | None = None


class UserCreate(UserBase):
    oauth_provider: OAuthProvider
    oauth_id: str
    avatar_url: str | None = None


class UserResponse(UserBase):
    id: UUID
    role: UserRole
    avatar_url: str | None = None
    oauth_provider: OAuthProvider | None
    created_at: datetime
    last_login: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True
    )


class UserUpdate(UserBase):
    username: str | None = None
    avatar_url: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'Bearer'

class AccessTokenPayload(BaseModel):
    sub: str
    email: str
    role: UserRole
    exp: int


class RefreshTokenPayload(BaseModel):
    sub: str
    jti: str
    exp: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str | None = None


class OAuthUserInfo(BaseModel):
    oauth_id: str
    email: str
    username: str | None
    avatar_url: str | None = None
    provider: OAuthProvider


class GoogleOAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str] = Field(
        default_factory=lambda: [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    )
