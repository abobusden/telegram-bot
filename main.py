import asyncio
import logging
import os
from threading import Thread

from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import router
from database import init_db

# ===== FLASK (для Render) =====
app = Flask('')


@app.route('/')
def home():
    return "Sky World Bot is running!"


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


# ===== БОТ =====
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задан! Добавь его в Render → Environment.")
        return

    init_db()
    print("✅ База данных готова.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    print("🚀 Бот Sky World запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("⛔ Бот остановлен.")
