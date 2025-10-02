from dishka import Provider, Scope, from_context, provide
from faststream.rabbit import RabbitBroker

from application.event_handler import OrderEventHandler
from config import Settings
from infrastructure.resources.broker import new_broker
from infrastructure.telegram import TelegramNotifier


class AppProvider(Provider):
    config = from_context(provides=Settings, scope=Scope.APP)
    broker = from_context(provides=RabbitBroker, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_broker(self, config: Settings) -> RabbitBroker:
        return new_broker(config.rabbitmq)

    @provide(scope=Scope.APP)
    def get_notifier(self, config: Settings) -> TelegramNotifier:
        return TelegramNotifier(config.telegram)

    @provide(scope=Scope.APP)
    def get_handler(self, notifier: TelegramNotifier) -> OrderEventHandler:
        return OrderEventHandler(notifier)
