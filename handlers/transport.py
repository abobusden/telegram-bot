# ============================================
# ТРАНСПОРТ (автосалон + гараж) — с фото и ПТС
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import (
    transport_menu_kb, autosalon_kb, garage_kb,
    back_to_transport_kb, car_info_kb,
)


router = Router()

# ============================================
# 10 МАШИН (с фото)
# ============================================
CARS = {
    "sedan": {
        "name": "🚗 Sedan",
        "price": 5000,
        "speed": 3,
        "photo": "https://i.ibb.co/jZH7h8Fr/Screenshot-20260913-110605.jpg",
        "category": "Легковая",
        "bonus": "Универсальная, дёшево",
    },
    "minivan": {
        "name": "🚐 Минивэн",
        "price": 8000,
        "speed": 4,
        "photo": "https://i.ibb.co/6RH0DzCN/Screenshot-20260913-121445.jpg",
        "category": "Легковая",
        "bonus": "Вместительная",
    },
    "suv": {
        "name": "🚙 Внедорожник",
        "price": 12000,
        "speed": 5,
        "photo": "https://i.ibb.co/WpRxHcrX/Screenshot-20260913-124146.jpg",
        "category": "Легковая",
        "bonus": "Проходимая",
    },
    "sportcar": {
        "name": "🏎 Спорткар",
        "price": 25000,
        "speed": 9,
        "photo": "https://i.ibb.co/S7vLRrWg/Screenshot-20260913-124328.jpg",
        "category": "Спорткар",
        "bonus": "Быстрая, статус",
    },
    "tuned": {
        "name": "🏎 Тюнингованная",
        "price": 35000,
        "speed": 8,
        "photo": "https://i.ibb.co/bg3gF9NN/Screenshot-20260913-124636.jpg",
        "category": "Спорткар",
        "bonus": "Тюнинг, стиль",
    },
    "supercar": {
        "name": "🏎 Суперкар",
        "price": 50000,
        "speed": 10,
        "photo": "https://i.ibb.co/5hvRtSDD/IMG-20260913-124922-303.jpg",
        "category": "Спорткар",
        "bonus": "Максимальная скорость",
    },
    "moto": {
        "name": "🏍 Мотоцикл",
        "price": 8000,
        "speed": 6,
        "photo": "https://i.ibb.co/6csXwMZT/Screenshot-20260913-125218.jpg",
        "category": "Мотоцикл",
        "bonus": "Дёшево, быстро",
    },
    "chopper": {
        "name": "🏍 Чоппер",
        "price": 15000,
        "speed": 5,
        "photo": "https://i.ibb.co/s9kvpCYD/Screenshot-20260913-125647.jpg",
        "category": "Мотоцикл",
        "bonus": "Стиль, статус",
    },
    "sportbike": {
        "name": "🏍 Спорт-байк",
        "price": 18000,
        "speed": 9,
        "photo": "https://i.ibb.co/fzL6t2YD/Screenshot-20260913-125858.jpg",
        "category": "Мотоцикл",
        "bonus": "Скорость + стиль",
    },
    "truck": {
        "name": "🚚 Грузовик",
        "price": 30000,
        "speed": 3,
        "photo": "https://i.ibb.co/DHy2gj0V/Screenshot-20260913-125950.jpg",
        "category": "Грузовой",
        "bonus": "+30% к работе «Грузчик»",
    },
}


# ============================================
# МЕНЮ ТРАНСПОРТА
# ============================================
@router.message(F.text == "🚗 Транспорт")
async def transport_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    car_name = CARS.get(player["car"], {}).get("name", "нет")

    await message.answer(
        f"🚗 <b>ТРАНСПОРТ</b>\n\n"
        f"🚘 Твоя машина: {car_name}\n"
        f"💰 Баланс: ${player['balance']}",
        reply_markup=transport_menu_kb(player["car"]),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "transport_back")
async def transport_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    car_name = CARS.get(player["car"], {}).get("name", "нет")

    await callback.message.delete()
    await callback.message.answer(
        f"🚗 <b>ТРАНСПОРТ</b>\n\n"
        f"🚘 Твоя машина: {car_name}\n"
        f"💰 Баланс: ${player['balance']}",
        reply_markup=transport_menu_kb(player["car"]),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# АВТОСАЛОН
# ============================================
@router.callback_query(F.data == "autosalon")
async def autosalon(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🏎 <b>АВТОСАЛОН</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Выбери машину:",
        reply_markup=autosalon_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ИНФО О МАШИНЕ + ПТС
# ============================================
@router.callback_query(F.data.startswith("car_"))
async def car_info(callback: CallbackQuery):
    car_key = callback.data.replace("car_", "")
    car = CARS.get(car_key)

    if not car:
        await callback.answer("Машина не найдена")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    pts_text = (
        f"📄 <b>ПТС — ПАСПОРТ ТС</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🚘 <b>{car['name']}</b>\n\n"
        f"📂 Категория: {car['category']}\n"
        f"⚡ Скорость: {car['speed']}/10\n"
        f"💰 Цена: ${car['price']:,}\n"
        f"🎁 Бонус: {car['bonus']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Твой баланс: ${player['balance']:,}\n"
    )

    if player["balance"] < car["price"]:
        pts_text += f"\n❌ <b>Не хватает ${car['price'] - player['balance']:,}</b>"
    else:
        pts_text += f"\n✅ <b>Хватает на покупку!</b>"

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=car["photo"],
        caption=pts_text,
        reply_markup=car_info_kb(car_key),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ПОКУПКА МАШИНЫ
# ============================================
@router.callback_query(F.data.startswith("buycar_"))
async def buy_car(callback: CallbackQuery):
    car_key = callback.data.replace("buycar_", "")
    car = CARS.get(car_key)

    if not car:
        await callback.answer("Машина не найдена")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["balance"] < car["price"]:
        await callback.answer("💰 Не хватает денег", show_alert=True)
        return

    new_balance = player["balance"] - car["price"]

    await update_player(
        callback.from_user.id,
        balance=new_balance,
        car=car_key,
    )

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=car["photo"],
        caption=(
            f"✅ <b>КУПЛЕНО!</b>\n\n"
            f"{car['name']}\n"
            f"⚡ Скорость: {car['speed']}/10\n"
            f"💰 -${car['price']:,}\n\n"
            f"💰 Баланс: ${new_balance:,}"
        ),
        reply_markup=back_to_transport_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Куплено!")


# ============================================
# ГАРАЖ
# ============================================
@router.callback_query(F.data == "garage")
async def garage(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if not player["car"]:
        await callback.answer("У тебя нет машины", show_alert=True)
        return

    car = CARS.get(player["car"])

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=car["photo"],
        caption=(
            f"🏠 <b>ГАРАЖ</b>\n\n"
            f"{car['name']}\n"
            f"📂 Категория: {car['category']}\n"
            f"⚡ Скорость: {car['speed']}/10\n"
            f"🎁 Бонус: {car['bonus']}\n\n"
            f"Апгрейды (пока недоступны)"
        ),
        reply_markup=garage_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "sell_car")
async def sell_car(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if not player["car"]:
        await callback.answer("У тебя нет машины", show_alert=True)
        return

    car = CARS.get(player["car"])
    sell_price = int(car["price"] * 0.7)

    new_balance = player["balance"] + sell_price

    await update_player(
        callback.from_user.id,
        balance=new_balance,
        car=None,
    )

    await callback.message.delete()
    await callback.message.answer(
        f"💸 <b>ПРОДАНО!</b>\n\n"
        f"{car['name']}\n"
        f"💰 +${sell_price:,} (70%)\n\n"
        f"💰 Баланс: ${new_balance:,}",
        reply_markup=back_to_transport_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Продано!")
