# ============================================
# МАГАЗИН (оружие, броня, еда)
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import shop_menu_kb, shop_back_kb


router = Router()

# Хранилище брони (ВВЕРХУ!)
armor_data = {}

# ============================================
# ТОВАРЫ
# ============================================
ITEMS = {
    "pistol":  {"name": "🔫 Пистолет",   "price": 500,  "type": "weapon", "bonus": 10},
    "smg":     {"name": "🔫🔫 SMG",      "price": 2000, "type": "weapon", "bonus": 15},
    "shotgun": {"name": "🎯 Дробовик",   "price": 3500, "type": "weapon", "bonus": 18},
    "rifle":   {"name": "💥 Автомат",    "price": 8000, "type": "weapon", "bonus": 20},
    "armor":   {"name": "🛡 Броня",      "price": 1500, "type": "armor"},
    "medkit":  {"name": "💊 Аптечка",    "price": 300,  "type": "heal", "hp": 50},
    "food":    {"name": "🍔 Еда",        "price": 50,   "type": "heal", "hp": 20},
    "heal":    {"name": "🏥 Лечение (полный HP)", "price": 50, "type": "full_heal"},
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
        text=(
            f"🛒 <b>МАГАЗИН</b>\n\n"
            f"💰 Баланс: ${player.get('balance', 0)}\n\n"
            f"Выбери товар:"
        ),
        reply_markup=shop_menu_kb(),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "shop_back")
async def shop_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    await callback.message.edit_text(
        text=(
            f"🛒 <b>МАГАЗИН</b>\n\n"
            f"💰 Баланс: ${player.get('balance', 0)}\n\n"
            f"Выбери товар:"
        ),
        reply_markup=shop_menu_kb(),
        parse_mode=ParseMode.HTML
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

    current_balance = player.get("balance", 0)

    if current_balance < item["price"]:
        await callback.answer("💰 Не хватает денег", show_alert=True)
        return

    new_balance = current_balance - item["price"]

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

    elif item["type"] == "heal":
        current_hp = player.get("hp", 100)
        new_hp = min(100, current_hp + item["hp"])
        await update_player(
            callback.from_user.id,
            balance=new_balance,
            hp=new_hp,
        )
        result = f"✅ Куплено: {item['name']}\n❤️ +{item['hp']} HP (сейчас {new_hp}/100)"

    elif item["type"] == "full_heal":
        await update_player(
            callback.from_user.id,
            balance=new_balance,
            hp=100,
        )
        result = f"✅ {item['name']}\n❤️ HP: 100/100"

    await callback.message.edit_text(
        text=f"<b>{result}</b>\n\n💰 Баланс: ${new_balance}",
        reply_markup=shop_back_kb(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Куплено!")
