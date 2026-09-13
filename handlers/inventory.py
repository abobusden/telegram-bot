# ============================================
# ИНВЕНТАРЬ (пока в профиле)
# ============================================

from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import get_player
from keyboards import inventory_kb


router = Router()

WEAPON_NAMES = {
    "pistol": "🔫 Пистолет (+10%)",
    "smg": "🔫🔫 SMG (+15%)",
    "shotgun": "🎯 Дробовик (+18%)",
    "rifle": "💥 Автомат (+20%)",
}


@router.callback_query(F.data == "inventory")
async def inventory(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    weapon = WEAPON_NAMES.get(player["weapon"], "нет")

    text = (
        f"🎒 <b>ИНВЕНТАРЬ</b>\n\n"
        f"🔫 Оружие: {weapon}\n"
        f"❤️ HP: {player['hp']}/100\n"
        f"🚨 Розыск: {'⭐' * player['wanted'] or 'чисто'}\n\n"
        f"💰 Баланс: ${player['balance']}"
    )

    await callback.message.edit_text(text, reply_markup=inventory_kb())
    await callback.answer()


@router.callback_query(F.data == "inv_back")
async def inv_back(callback: CallbackQuery):
    from handlers.menu import profile_screen
    await profile_screen(callback)
