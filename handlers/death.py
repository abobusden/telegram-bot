# ============================================
# СМЕРТЬ И ЛЕЧЕНИЕ
# ============================================

import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import death_kb


router = Router()

death_waiting = {}


async def show_death_screen(telegram_id: int, send_func):
    player = await get_player(telegram_id)
    if not player:
        return

    await send_func(
        f"💀 <b>ВЫ ПОГИБЛИ</b>\n\n"
        f"HP: {player['hp']}/100\n\n"
        f"Выбери действие:",
        reply_markup=death_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "death_heal")
async def death_heal(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["hp"] > 0:
        await callback.answer("Ты ещё жив!", show_alert=True)
        return

    if player["balance"] < 500:
        await callback.answer("💰 Нужно $500", show_alert=True)
        return

    await update_player(
        callback.from_user.id,
        balance=player["balance"] - 500,
        hp=100,
    )

    death_waiting.pop(callback.from_user.id, None)

    await callback.message.delete()
    await callback.message.answer(
        f"🏥 <b>ПРОЛЕЧЕН!</b>\n\n"
        f"❤️ HP: 100/100\n"
        f"💰 -$500\n\n"
        f"Ты снова в строю!",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Пролечен!")


@router.callback_query(F.data == "death_wait")
async def death_wait(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Ошибка")
        return

    if player["hp"] > 0:
        await callback.answer("Ты ещё жив!", show_alert=True)
        return

    until = datetime.now() + timedelta(minutes=20)
    death_waiting[callback.from_user.id] = {"until": until}

    await callback.message.edit_text(
        f"⏳ <b>ВОССТАНОВЛЕНИЕ</b>\n\n"
        f"Ждём 20 мин...\n"
        f"Осталось: 20:00",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()

    asyncio.create_task(update_death_timer(callback.from_user.id, callback.message))


async def update_death_timer(telegram_id: int, message: Message):
    while True:
        await asyncio.sleep(60)

        data = death_waiting.get(telegram_id)
        if not data:
            return

        now = datetime.now()
        if now >= data["until"]:
            await update_player(telegram_id, hp=20)
            death_waiting.pop(telegram_id, None)

            try:
                await message.edit_text(
                    f"✅ <b>ТЫ ОКЛЕМАЛСЯ</b>\n\n"
                    f"❤️ HP: 20/100\n\n"
                    f"Советую подлечиться!",
                    parse_mode=ParseMode.HTML,
                )
            except:
                pass
            return

        left = int((data["until"] - now).total_seconds())
        mins, secs = divmod(left, 60)

        try:
            await message.edit_text(
                f"⏳ <b>ВОССТАНОВЛЕНИЕ</b>\n\n"
                f"Ждём 20 мин...\n"
                f"Осталось: {mins}:{secs:02d}",
                parse_mode=ParseMode.HTML,
            )
        except:
            pass


async def check_death(telegram_id: int, send_func):
    player = await get_player(telegram_id)
    if not player:
        return False

    if player["hp"] <= 0:
        if player["hp"] < 0:
            await update_player(telegram_id, hp=0)

        await show_death_screen(telegram_id, send_func)
        return True

    return False


async def regen_hp(telegram_id: int):
    player = await get_player(telegram_id)
    if not player:
        return

    if player["hp"] >= 100:
        return

    new_hp = min(100, player["hp"] + 1)
    await update_player(telegram_id, hp=new_hp)
