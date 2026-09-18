# ============================================
# МАГАЗИН 24/7
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import shop_menu_kb, shop_back_kb


router = Router()

# Хранилище брони (для совместимости)
armor_data = {}

# Товары
ITEMS = {
    "food":   {"name": "🍔 Еда",    "price": 50,  "type": "heal",   "hp": 20},
    "medkit": {"name": "💊 Аптечка", "price": 300, "type": "heal",   "hp": 50},
    "water":  {"name": "🥤 Вода",   "price": 20,  "type": "heal",   "hp": 5},
    "coffee": {"name": "☕ Кофе",   "price": 200, "type": "cooldown"},
}


# ============================================
# МЕНЮ МАГАЗИНА
# ============================================
@router.message(F.text == "🛒 Магазин")
async def shop_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    await message.answer(
        f"🏪 <b>МАГАЗИН 24/7</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Выбери товар:",
        reply_markup=shop_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "shop_back")
async def shop_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🏪 <b>МАГАЗИН 24/7</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Выбери товар:",
        reply_markup=shop_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ПОКУПКА
# ============================================
@router.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: CallbackQuery):
    item_key = callback.data.replace("buy_", "")
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

    # Лечение
    if item["type"] == "heal":
        new_hp = min(100, player["hp"] + item["hp"])
        await update_player(
            callback.from_user.id,
            balance=new_balance,
            hp=new_hp,
        )
        result = f"✅ Куплено: {item['name']}\n❤️ +{item['hp']} HP (сейчас {new_hp}/100)"

    # Кофе — сброс КД
    elif item["type"] == "cooldown":
        from handlers.jobs import job_cooldowns
        if callback.from_user.id in job_cooldowns:
            job_cooldowns[callback.from_user.id] = {}
        await update_player(callback.from_user.id, balance=new_balance)
        result = f"✅ Куплено: {item['name']}\n⏱ Все КД на работы сброшены"

    await callback.message.edit_text(
        f"{result}\n\n💰 Баланс: ${new_balance}",
        reply_markup=shop_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Куплено!")
