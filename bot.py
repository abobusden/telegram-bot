# ============================================
# GTA CRIME BOT — с Flask-заглушкой для Render
# ============================================

import asyncio
import logging
import os
from threading import Thread

from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import start


# ============================================
# FLASK-ЗАГЛУШКА (для Render Web Service)
# ============================================
app = Flask(__name__)


@app.route('/')
def home():
    return "🚀 GTA Crime Bot is running!"


@app.route('/health')
def health():
    return "OK", 200


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ============================================
# ЗАПУСК БОТА
# ============================================
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start.router)

    print("🚀 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Flask в фоне (для Render)
    Thread(target=run_flask, daemon=True).start()

    # Бот
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Бот остановлен")
