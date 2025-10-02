from aiogram import Bot
from aiogram.enums.parse_mode import ParseMode

from config import TelegramConfig


class TelegramNotifier:
    def __init__(self, config: TelegramConfig):
        self.bot = Bot(token=config.bot_token.get_secret_value())
        self.chat_id = config.chat_id

    async def send_message(self, text: str) -> None:
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )

    async def close(self) -> None:
        await self.bot.session.close()
