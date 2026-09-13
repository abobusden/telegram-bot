# ============================================
# КОПЫ, РОЗЫСК, ТЮРЬМА
# ============================================

from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import get_player, update_player
from keyboards import jail_kb


router = Router()

# ============================================
# ИМПОРТ ИЗ crime.py
# ============================================
from handlers.crime import jail_data, is_in_jail


# ============================================
# ПРОВЕРКА ТЮРЬМЫ ПРИ ЛЮБОМ ДЕЙСТВИИ
# ============================================
@router.message(F.text.in_(["💼 Работа", "⚔️ Криминал", "🛒 Магазин",
                            "🚗 Транспорт", "🏠 Жильё", "🗺 Карта",
                            "🏢 Здания", "🏆 Топ"]))
async def block_in_jail(message: Message):
    """Если игрок в тюрьме — блокируем действия."""
    data = is_in_jail(message.from_user.id)
    if not data:
        return  # не в тюрьме — пропускаем

    left = int((data["until"] - datetime.now()).total_seconds())
    mins, secs = divmod(left, 60)

    await message.answer(
        f"🚔 <b>ТЫ В ТЮРЬМЕ</b>\n\n"
        f"⏱ Осталось: {mins}:{secs:02d}\n\n"
        f"Варианты:",
        reply_markup=jail_kb(),
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

    left = int((data["until"] - datetime.now()).total_seconds())
    mins, secs = divmod(left, 60)

    await message.answer(
        f"🚔 <b>ТЮРЬМА</b>\n\n"
        f"⏱ Осталось: {mins}:{secs:02d}\n\n"
        f"Варианты:",
        reply_markup=jail_kb(),
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
    if player["balance"] < 10000:
        await callback.answer("💰 Нужно $10000", show_alert=True)
        return

    # Списываем и освобождаем
    await update_player(
        callback.from_user.id,
        balance=player["balance"] - 10000,
        wanted=0,
    )
    jail_data.pop(callback.from_user.id, None)

    await callback.message.edit_text(
        "👨‍⚖️ <b>АДВОКАТ</b>\n\n"
        "💰 -$10000\n"
        "✅ Ты на свободе!\n"
        "🚨 Розыск: 0",
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

    left = int((data["until"] - datetime.now()).total_seconds())
    mins, secs = divmod(left, 60)

    await callback.answer(f"⏱ Осталось {mins}:{secs:02d}", show_alert=True)
