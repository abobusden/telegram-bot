# ============================================
# АРСЕНАЛ (оружие + броня)
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import arsenal_menu_kb, arsenal_back_kb


router = Router()

armor_data = {}

ITEMS = {
    "pistol":  {"name": "🔫 Пистолет", "price": 500,  "type": "weapon", "bonus": 10},
    "smg":     {"name": "🔫🔫 SMG",    "price": 2000, "type": "weapon", "bonus": 15},
    "shotgun": {"name": "🎯 Дробовик", "price": 3500, "type": "weapon", "bonus": 18},
    "rifle":   {"name": "💥 Автомат",  "price": 8000, "type": "weapon", "bonus": 20},
    "armor":   {"name": "🛡 Броня",    "price": 1500, "type": "armor"},
}


@router.message(F.text == "🔫 Арсенал")
async def arsenal_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    weapon = player.get("weapon") or "нет"

    await message.answer(
        f"🔫 <b>АРСЕНАЛ</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n"
        f"🔫 Твоё оружие: {weapon}\n\n"
        f"Выбери товар:",
        reply_markup=arsenal_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "arsenal_back")
async def arsenal_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    weapon = player.get("weapon") or "нет"

    await callback.message.delete()
    await callback.message.answer(
        f"🔫 <b>АРСЕНАЛ</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n"
        f"🔫 Твоё оружие: {weapon}\n\n"
        f"Выбери товар:",
        reply_markup=arsenal_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ars_"))
async def buy_arsenal(callback: CallbackQuery):
    item_key = callback.data.replace("ars_", "")
    item = ITEMS.get(item_key)

    if not item:
        await callback.answer("Товар не найден")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["balance"] < item["price"]:
        await callback.answer("💰 Не хватает денег", show_alert=True)
        return

    new_balance = player["balance"] - item["price"]

    if item["type"] == "weapon":
        await update_player(
            callback.from_user.id,
            balance=new_balance,
            weapon=item_key,
        )
        result = f"✅ Куплено: {item['name']}\n+{item['bonus']}% к криминалу"

    elif item["type"] == "armor":
        await update_player(callback.from_user.id, balance=new_balance)
        armor_data[callback.from_user.id] = True
        result = f"✅ Куплено: {item['name']}\n+30% защита"

    await callback.message.edit_text(
        f"{result}\n\n💰 Баланс: ${new_balance}",
        reply_markup=arsenal_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Куплено!")
