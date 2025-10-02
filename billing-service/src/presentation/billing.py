import logging
from typing import Annotated
from uuid import UUID

import httpx
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.billing_service import BillingService
from config import settings
from domain.schemas import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    PackageInfo,
)
from infrastructure.models import OrderStatus
from infrastructure.stripe.service import StripeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/billing', tags=['Billing'], route_class=DishkaRoute)
security = HTTPBearer()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> UUID:
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f'{settings.auth_service_url}/api/v1/auth/me',
                headers={'Authorization': f'Bearer {token}'},
            )
            response.raise_for_status()
            user_data = response.json()
            return UUID(user_data['id'])
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get('detail', 'Invalid authentication credentials'),
                headers={'WWW-Authenticate': 'Bearer'},
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f'Auth service error: {str(e)}',
            )


@router.get('/packages', summary='Get all packages', response_model=list[PackageInfo])
async def get_packages(
    billing_service: FromDishka[BillingService],
) -> list[PackageInfo]:
    return billing_service.get_all_packages()


@router.get('/packages/{package_type}', summary='Get package details', response_model=PackageInfo)
async def get_package(
    package_type: str,
    billing_service: FromDishka[BillingService],
) -> PackageInfo:
    try:
        from infrastructure.models import PackageType
        pkg_type = PackageType(package_type)
        return billing_service.get_package_info(pkg_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Package not found',
        )



@router.post('/orders', summary='Create order', response_model=dict)
async def create_order(
    order_data: OrderCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    billing_service: FromDishka[BillingService],
) -> dict:
    try:
        order, payment = await billing_service.create_order(user_id, order_data)
        return {
            'order': order.model_dump(),
            'payment': payment.model_dump(),
        }
    except Exception as e:
        logger.error(f'Failed to create order: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get('/orders', summary='Get user orders', response_model=OrderListResponse)
async def get_orders(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    billing_service: FromDishka[BillingService],
    page: int = 1,
    page_size: int = 20,
    order_status: OrderStatus | None = None,
) -> OrderListResponse:
    if page < 1:
        raise HTTPException(status_code=400, detail='Page must be >= 1')
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail='Page size must be between 1 and 100')

    try:
        orders, total = await billing_service.get_user_orders(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=order_status,
        )

        return OrderListResponse(
            orders=orders,
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f'Failed to get orders: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get('/orders/{order_id}', summary='Get order details', response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    billing_service: FromDishka[BillingService],
) -> OrderResponse:
    try:
        return await billing_service.get_order(order_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f'Failed to get order: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post('/orders/{order_id}/cancel', summary='Cancel order', response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    billing_service: FromDishka[BillingService],
) -> OrderResponse:
    try:
        return await billing_service.cancel_order(order_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f'Failed to cancel order: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post('/webhooks/stripe', summary='Stripe webhook handler', include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str, Header(alias='stripe-signature')],
    billing_service: FromDishka[BillingService],
    stripe_service: FromDishka[StripeService],
) -> dict:
    payload = await request.body()

    try:
        event = stripe_service.construct_webhook_event(
            payload=payload,
            sig_header=stripe_signature,
        )
    except Exception as e:
        logger.error(f'Webhook signature verification failed: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid signature',
        )

    try:
        await billing_service.process_webhook(
            stripe_event=event,
            raw_payload=payload.decode('utf-8'),
        )

        return {'status': 'success'}

    except Exception as e:
        logger.error(f'Webhook processing failed: {e}')
        return {'status': 'error', 'message': str(e)}


@router.get('/health', summary='Health check')
async def health_check() -> dict:
    return {'status': 'healthy', 'service': 'billing-service'}
