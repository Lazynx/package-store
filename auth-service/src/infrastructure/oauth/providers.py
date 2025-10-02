from abc import ABC, abstractmethod
from urllib.parse import urlencode

import httpx

from domain.schemas import OAuthUserInfo
from infrastructure.models import OAuthProvider


class BaseOAuthProvider(ABC):
    @abstractmethod
    async def get_authorization_url(self, state: str | None = None) -> str:
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> str:
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        pass


class GoogleOAuthProvider(BaseOAuthProvider):
    AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]

    async def get_authorization_url(self, state: str | None = None) -> str:
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'access_type': 'offline',
            'prompt': 'consent',
        }
        if state:
            params['state'] = state

        return f'{self.AUTHORIZATION_URL}?{urlencode(params)}'

    async def exchange_code(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': self.redirect_uri,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data['access_token']

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
            )
            response.raise_for_status()
            data = response.json()

            return OAuthUserInfo(
                oauth_id=data['id'],
                email=data['email'],
                username=data.get('name'),
                avatar_url=data.get('picture'),
                provider=OAuthProvider.GOOGLE,
            )
