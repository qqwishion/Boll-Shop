import asyncio
import logging

from aiogram import Bot, Dispatcher
from bool_shop.bot_token import TOKEN
from bool_shop.handlers import admin_handlers, order_handlers, user_handlers
from bool_shop.db import init_db

logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def main():
    await init_db()  # проверка и создание таблицы
    print("🚀 База данных инициализирована, запускаем бота...")
    dp.include_router(user_handlers.router)
    dp.include_router(order_handlers.router)
    dp.include_router(admin_handlers.router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown")

