from pathlib import Path

from pydantic import SecretStr
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


class TelegramConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='TELEGRAM_',
        env_file=ENV_FILE,
    )
    bot_token: SecretStr = SecretStr('')
    chat_id: str = '0'


class Settings(BaseSettings):
    secret_key: SecretStr = SecretStr('')
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    telegram: TelegramConfig = TelegramConfig()

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        case_sensitive=False,
    )

settings = Settings()

