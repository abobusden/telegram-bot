# ============================================
# ЗАПУСК БОТА
# ============================================

import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import (
    start, menu, jobs, crime, cops, shop, inventory,
    transport, home, gangs, pvp, city_map,
    arsenal, hospital, autoservice, bank, casino, race,
    death, events, top, referral, admin,
)


async def handle(request):
    return web.Response(text="🚀 GTA Crime Bot is running!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web server started on port {port}")


async def main():
    logging.basicConfig(level=logging.INFO)

    await start_web_server()

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # ⚠️ admin — ПЕРВЫМ, чтобы его команды никто не перебил
    dp.include_router(admin.router)

    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(shop.router)
    dp.include_router(arsenal.router)
    dp.include_router(hospital.router)
    dp.include_router(autoservice.router)
    dp.include_router(bank.router)
    dp.include_router(casino.router)
    dp.include_router(race.router)
    dp.include_router(death.router)
    dp.include_router(events.router)
    dp.include_router(top.router)
    dp.include_router(referral.router)
    dp.include_router(inventory.router)
    dp.include_router(transport.router)
    dp.include_router(home.router)
    dp.include_router(gangs.router)
    dp.include_router(pvp.router)
    dp.include_router(city_map.router)
    dp.include_router(cops.router)
    dp.include_router(jobs.router)
    dp.include_router(crime.router)

    print("🚀 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Бот остановлен")
