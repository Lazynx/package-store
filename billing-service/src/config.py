from decimal import Decimal
from pathlib import Path

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / '.env'

class RabbitMQConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='RABBITMQ_',
        env_file=ENV_FILE,
    )
    host: str = 'localhost'
    port: int = 5672
    login: str = 'guest'
    password: str = 'guest'


class PostgresConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='BILLING_POSTGRES_',
        env_file=ENV_FILE,
    )
    host: str= 'localhost'
    port: int = 5432
    login: str = 'postgres'
    password: str = 'postgres'
    database: str = 'test_task'

    @computed_field
    @property
    def database_url(self) -> str:
        return f'postgresql+asyncpg://{self.login}:{self.password}@{self.host}:{self.port}/{self.database}'


class StripeConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='STRIPE_',
        env_file=ENV_FILE,
    )
    secret_key: SecretStr = SecretStr('<KEY>')
    publishable_key: str = ''
    webhook_secret: SecretStr = SecretStr('<KEY>')


class PackagePricing(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='PACKAGE_',
        env_file=ENV_FILE,
    )

    basic_price: Decimal = Decimal('9.99')
    standard_price: Decimal = Decimal('29.99')
    premium_price: Decimal = Decimal('99.99')


class Settings(BaseSettings):
    secret_key: SecretStr = SecretStr('')
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    postgres: PostgresConfig = PostgresConfig()
    stripe: StripeConfig = StripeConfig()
    pricing: PackagePricing = PackagePricing()

    auth_service_url: str = 'http://test-task-auth-service:8000'

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        case_sensitive=False,
    )

settings = Settings()

