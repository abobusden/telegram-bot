# ============================================
# ПРОФИЛЬ
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import get_player
from keyboards import profile_kb


router = Router()


@router.message(F.text == "👤 Профиль")
async def profile(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    gender = "👨" if player["gender"] == "male" else "👩"

    await message.answer(
        f"👤 <b>{player['nickname']}</b> | {gender}\n"
        f"🚩 Банда: {player['faction'] or 'нет'}\n"
        f"📍 Район: {player['district']}\n"
        f"🏠 Жильё: {player['home'] or 'нет'}\n"
        f"🚗 Машина: {player['car'] or 'нет'}\n"
        f"🔫 Оружие: {player['weapon'] or 'нет'}\n"
        f"🚨 Розыск: {'⭐' * player['wanted'] or '0'}\n\n"
        f"💰 ${player['balance']} | ❤️ {player['hp']}/100\n"
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/100",
        reply_markup=profile_kb(),
    )


async def profile_screen(callback: CallbackQuery):
    """Для возврата из инвентаря."""
    player = await get_player(callback.from_user.id)
    gender = "👨" if player["gender"] == "male" else "👩"

    await callback.message.edit_text(
        f"👤 <b>{player['nickname']}</b> | {gender}\n"
        f"🚩 Банда: {player['faction'] or 'нет'}\n"
        f"📍 Район: {player['district']}\n"
        f"🏠 Жильё: {player['home'] or 'нет'}\n"
        f"🚗 Машина: {player['car'] or 'нет'}\n"
        f"🔫 Оружие: {player['weapon'] or 'нет'}\n"
        f"🚨 Розыск: {'⭐' * player['wanted'] or '0'}\n\n"
        f"💰 ${player['balance']} | ❤️ {player['hp']}/100\n"
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/100",
        reply_markup=profile_kb(),
    )
