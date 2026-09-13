# ============================================
# КОПЫ, РОЗЫСК, ТЮРЬМА
# ============================================

from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import jail_kb

router = Router()

# Импорт из crime.py
from handlers.crime import jail_data, is_in_jail


# ============================================
# ПРОВЕРКА ТЮРЬМЫ ПРИ КНОПКАХ
# (хендлер срабатывает ТОЛЬКО если игрок в тюрьме)
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
    """Если игрок в тюрьме — блокируем действия."""
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
# АДВОКАТ
# ============================================
@router.callback_query(F.data == "jail_lawyer")
async def jail_lawyer(callback: CallbackQuery):
    data = is_in_jail(callback.from_user.id)
    if not data:
        await callback.answer("Ты не в тюрьме")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Ошибка данных игрока", show_alert=True)
        return

    current_balance = player.get("balance", 0)
    if current_balance < 10000:
        await callback.answer("💰 Нужно $10000", show_alert=True)
        return

    await update_player(
        callback.from_user.id,
        balance=current_balance - 10000,
        wanted=0,
    )
    jail_data.pop(callback.from_user.id, None)

    await callback.message.edit_text(
        text=(
            "👨‍⚖️ <b>АДВОКАТ</b>\n\n"
            "💰 -$10000\n"
            "✅ Ты на свободе!\n"
            "🚨 Розыск: 0"
        ),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Свобода!")


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
        await callback.answer("Срок уже истек! Попробуй кнопку заново.", show_alert=True)
        return

    left = int((data["until"] - datetime.now()).total_seconds())
    mins, secs = divmod(left, 60)

    await callback.answer(f"⏱ Осталось {mins}:{secs:02d}", show_alert=True)
