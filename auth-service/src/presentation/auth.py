from typing import Annotated

import httpx
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.auth_service import AuthService
from domain.schemas import RefreshTokenRequest, TokenPair, UserResponse
from infrastructure.oauth.providers import GoogleOAuthProvider
from infrastructure.security.jwt_service import JWTService

router = APIRouter(
    prefix='/api/v1/auth',
    tags=['Authentication'],
    route_class=DishkaRoute,
)
security = HTTPBearer()

@router.get('/google', summary='Redirect to Google OAuth')
async def google_login(
    google_provider: FromDishka[GoogleOAuthProvider],
) -> dict:
    auth_url = await google_provider.get_authorization_url()
    return {'authorization_url': auth_url}


@router.get('/google/callback', summary='Google OAuth callback')
async def google_callback(
    code: str,
    auth_service: FromDishka[AuthService],
    google_provider: FromDishka[GoogleOAuthProvider],
    request: Request,
) -> TokenPair:
    try:
        print(f'Received code: {code[:20]}...')  # Логируем первые 20 символов
        print(f'Redirect URI configured: {google_provider.redirect_uri}')

        access_token = await google_provider.exchange_code(code)
        print(f'Got access token: {access_token[:20]}...')

        oauth_user = await google_provider.get_user_info(access_token)
        print(f'Got user info for: {oauth_user.email}')

        token_pair, user = await auth_service.authenticate_with_oauth(
            oauth_user=oauth_user,
            device_info=request.headers.get('user-agent'),
            ip_address=request.client.host if request.client else None,
        )

        return token_pair
    except httpx.HTTPStatusError as e:
        error_body = e.response.text
        print(f'HTTP Error: {e.response.status_code} - {error_body}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'OAuth HTTP error: {e.response.status_code} - {error_body}',
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'OAuth authentication failed: {type(e).__name__}: {str(e)}',
        )

@router.post('/refresh', summary='Refresh access token', response_model=TokenPair)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: FromDishka[AuthService],
) -> TokenPair:
    try:
        token_pair, _ = await auth_service.refresh_access_token(request.refresh_token)
        return token_pair
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

@router.post('/logout', summary='Logout (revoke refresh token)')
async def logout(
    request: RefreshTokenRequest,
    auth_service: FromDishka[AuthService],
) -> dict:
    try:
        await auth_service.logout(request.refresh_token)
        return {'message': 'Successfully logged out'}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get('/me', summary='Get current user', response_model=UserResponse)
async def get_me(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: FromDishka[JWTService],
    auth_service: FromDishka[AuthService],
) -> UserResponse:
    try:
        token = credentials.credentials
        payload = jwt_service.verify_access_token(token)
        user = await auth_service.get_current_user(payload.sub)
        return user
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials',
            headers={'WWW-Authenticate': 'Bearer'},
        )

@router.get('/health', summary='Health check')
async def health_check() -> dict:
    return {'status': 'healthy', 'service': 'auth-service'}
