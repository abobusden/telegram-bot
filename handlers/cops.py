# ============================================
# КОПЫ, РОЗЫСК, ТЮРЬМА
# ============================================

import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import jail_kb

router = Router()

from handlers.crime import jail_data, is_in_jail


# ============================================
# БЛОК ДЕЙСТВИЙ В ТЮРЬМЕ
# (срабатывает ТОЛЬКО если игрок реально в тюрьме)
# ============================================
@router.message(
    F.text.in_([
        "💼 Работа",
        "⚔️ Криминал",
        "🛒 Магазин",
        "🚗 Транспорт",
        "🏠 Жильё",
        "🗺 Карта",
        "🏢 Здания",
        "🏆 Топ",
    ]),
    F.func(lambda message: is_in_jail(message.from_user.id) is not None),
)
async def block_in_jail(message: Message):
    data = is_in_jail(message.from_user.id)
    if not data:
        return

    if datetime.now() >= data["until"]:
        jail_data.pop(message.from_user.id, None)
        return

    left = int((data["until"] - datetime.now()).total_seconds())
    mins, secs = divmod(left, 60)

    await message.answer(
        text=(
            f"🚔 <b>ТЫ В ТЮРЬМЕ</b>\n\n"
            f"⏱ Осталось: {mins}:{secs:02d}\n\n"
            f"Варианты:"
        ),
        reply_markup=jail_kb(),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# ЭКРАН ТЮРЬМЫ
# ============================================
@router.message(F.text == "🚔 Тюрьма")
async def jail_screen(message: Message):
    data = is_in_jail(message.from_user.id)
    if not data:
        await message.answer("Ты не в тюрьме")
        return

    if datetime.now() >= data["until"]:
        jail_data.pop(message.from_user.id, None)
        await message.answer("Ты уже вышел из тюрьмы!")
        return

    left = int((data["until"] - datetime.now()).total_seconds())
    mins, secs = divmod(left, 60)

    await message.answer(
        text=(
            f"🚔 <b>ТЮРЬМА</b>\n\n"
            f"⏱ Осталось: {mins}:{secs:02d}\n\n"
            f"Варианты:"
        ),
        reply_markup=jail_kb(),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# АДВОКАТ ($2000)
# ============================================
@router.callback_query(F.data == "jail_lawyer")
async def jail_lawyer(callback: CallbackQuery):
    data = is_in_jail(callback.from_user.id)
    if not data:
        await callback.answer("Ты не в тюрьме")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Ошибка данных")
        return

    LAWYER_PRICE = 2000

    if player["balance"] < LAWYER_PRICE:
        await callback.answer(
            f"💰 Нужно ${LAWYER_PRICE}. У тебя ${player['balance']}",
            show_alert=True,
        )
        return

    await update_player(
        callback.from_user.id,
        balance=player["balance"] - LAWYER_PRICE,
        wanted=0,
    )
    jail_data.pop(callback.from_user.id, None)

    await callback.message.delete()
    await callback.message.answer(
        f"👨‍⚖️ <b>АДВОКАТ</b>\n\n"
        f"💰 -${LAWYER_PRICE}\n"
        f"✅ Ты на свободе!\n"
        f"🚨 Розыск: 0",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Свобода!")


# ============================================
# ПОБЕГ (30%)
# ============================================
@router.callback_query(F.data == "jail_escape")
async def jail_escape(callback: CallbackQuery):
    data = is_in_jail(callback.from_user.id)
    if not data:
        await callback.answer("Ты не в тюрьме")
        return

    player = await get_player(callback.from_user.id)

    if random.random() < 0.30:
        # ✅ Побег удался
        jail_data.pop(callback.from_user.id, None)
        await callback.message.delete()
        await callback.message.answer(
            f"🏃 <b>ПОБЕГ УДАЛСЯ!</b>\n\n"
            f"✅ Ты сбежал из тюрьмы!\n"
            f"🚨 Розыск: {'⭐' * player['wanted']}",
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("Сбежал!")
    else:
        # ❌ Побег провалился
        new_wanted = min(5, player["wanted"] + 1)
        new_until = data["until"] + timedelta(minutes=15)

        jail_data[callback.from_user.id]["until"] = new_until
        await update_player(callback.from_user.id, wanted=new_wanted)

        await callback.message.delete()
        await callback.message.answer(
            f"❌ <b>ПОБЕГ ПРОВАЛЕН!</b>\n\n"
            f"🚨 Розыск +1: {'⭐' * new_wanted}\n"
            f"⏱ Срок +15 мин\n\n"
            f"Варианты:",
            reply_markup=jail_kb(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("Не вышло...", show_alert=True)


# ============================================
# ЖДАТЬ
# ============================================
@router.callback_query(F.data == "jail_wait")
async def jail_wait(callback: CallbackQuery):
    data = is_in_jail(callback.from_user.id)
    if not data:
        await callback.answer("Ты не в тюрьме")
        return

    if datetime.now() >= data["until"]:
        jail_data.pop(callback.from_user.id, None)
        await callback.answer("Срок истёк! Попробуй нажать заново.", show_alert=True)
        return

    left = int((data["until"] - datetime.now()).total_seconds())
    mins, secs = divmod(left, 60)

    await callback.answer(f"⏱ Осталось {mins}:{secs:02d}", show_alert=True)
