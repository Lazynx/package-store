from typing import AsyncIterable

from dishka import Provider, Scope, from_context, provide
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.billing_service import BillingService
from config import PackagePricing, Settings
from infrastructure.broker.events import OrderEventPublisher
from infrastructure.repositories.order import OrderRepository, PaymentAuditRepository, WebhookEventRepository
from infrastructure.resources.broker import new_broker
from infrastructure.resources.database import new_session_maker
from infrastructure.stripe.service import StripeService


class AppProvider(Provider):
    config = from_context(provides=Settings, scope=Scope.APP)
    broker = from_context(provides=RabbitBroker, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_session_maker(self, config: Settings) -> async_sessionmaker[AsyncSession]:
        return new_session_maker(config.postgres)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with session_maker() as session:
            yield session


    @provide(scope=Scope.APP)
    def get_broker(self, config: Settings) -> RabbitBroker:
        return new_broker(config.rabbitmq)

    @provide(scope=Scope.APP)
    def get_event_publisher(self, broker: RabbitBroker) -> OrderEventPublisher:
        return OrderEventPublisher(broker)

    @provide(scope=Scope.REQUEST)
    def get_order_repository(self, session: AsyncSession) -> OrderRepository:
        return OrderRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_webhook_repository(self, session: AsyncSession) -> WebhookEventRepository:
        return WebhookEventRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_audit_repository(self, session: AsyncSession) -> PaymentAuditRepository:
        return PaymentAuditRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_stripe_service(self, config: Settings) -> StripeService:
        return StripeService(
            secret_key=config.stripe.secret_key,
            webhook_secret=config.stripe.webhook_secret,
        )

    @provide(scope=Scope.REQUEST)
    def get_package_pricing(self, config: Settings) -> PackagePricing:
        return PackagePricing(
            basic_price=config.pricing.basic_price,
            standard_price=config.pricing.standard_price,
            premium_price=config.pricing.premium_price,
        )

    @provide(scope=Scope.REQUEST)
    def get_billing_service(
            self,
            order_repo: OrderRepository,
            webhook_repo: WebhookEventRepository,
            audit_repo: PaymentAuditRepository,
            stripe_service: StripeService,
            event_publisher: OrderEventPublisher,
            pricing: PackagePricing,
    ) -> BillingService:
        return BillingService(
            order_repo=order_repo,
            webhook_repo=webhook_repo,
            audit_repo=audit_repo,
            stripe_service=stripe_service,
            event_publisher=event_publisher,
            pricing=pricing,
        )
