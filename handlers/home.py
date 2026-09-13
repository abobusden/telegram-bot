# ============================================
# ЖИЛЬЁ (отели + дома) — с фото
# ============================================

from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import (
    home_menu_kb, hotels_kb, houses_kb,
    back_to_home_kb,
)


router = Router()

# ============================================
# ОТЕЛИ (аренда)
# ============================================
HOTELS = {
    "motel": {
        "name": "🏨 Мотель \"У Джеффа\"",
        "price": 100,
        "hp_regen": 2,
        "duration": 24,
        "photo": "https://i.ibb.co/3mmrGd6c/Screenshot-20260913-140528.jpg",
    },
    "downtown": {
        "name": "🏨 Отель Downtown",
        "price": 500,
        "hp_regen": 5,
        "duration": 24,
        "photo": "https://i.ibb.co/0yNgWGdK/Screenshot-20260913-140557.jpg",
    },
    "ritz": {
        "name": "🏨 Отель Ritz",
        "price": 2000,
        "hp_regen": 10,
        "duration": 24,
        "photo": "https://i.ibb.co/chxCMpvy/Screenshot-20260913-141056.jpg",
    },
}

# ============================================
# ДОМА (навсегда)
# ============================================
HOUSES = {
    "ganton_house": {
        "name": "🏡 Дом в Гантоне",
        "price": 5000,
        "hp_regen": 5,
        "photo": "https://i.ibb.co/LDFy5c2B/Screenshot-20260913-140029.jpg",
    },
    "mansion": {
        "name": "🏰 Особняк",
        "price": 50000,
        "hp_regen": 15,
        "photo": "https://i.ibb.co/wrxzQWfZ/Screenshot-20260913-140113.jpg",
    },
    "business": {
        "name": "🏢 Бизнес-центр",
        "price": 500000,
        "hp_regen": 10,
        "income": 3000,
        "photo": "https://i.ibb.co/p625588X/Screenshot-20260913-140345.jpg",
    },
}

# Хранилище аренды
rent_data = {}


# ============================================
# МЕНЮ ЖИЛЬЯ
# ============================================
@router.message(F.text == "🏠 Жильё")
async def home_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    home = player["home"]
    status = "🚶 На улице"

    if home:
        if home in HOTELS:
            rent = rent_data.get(message.from_user.id)
            if rent and datetime.now() < rent["until"]:
                left = int((rent["until"] - datetime.now()).total_seconds())
                hours, mins = divmod(left // 60, 60)
                status = f"🏨 {HOTELS[home]['name']}\n⏱ Осталось: {hours}ч {mins}мин"
        elif home in HOUSES:
            status = f"🏡 {HOUSES[home]['name']} (твой навсегда)"

    await message.answer(
        f"🏠 <b>ЖИЛЬЁ</b>\n\n"
        f"📍 Статус: {status}\n"
        f"💰 Баланс: ${player['balance']}",
        reply_markup=home_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "home_back")
async def home_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    home = player["home"]
    status = "🚶 На улице"

    if home:
        if home in HOTELS:
            rent = rent_data.get(callback.from_user.id)
            if rent and datetime.now() < rent["until"]:
                left = int((rent["until"] - datetime.now()).total_seconds())
                hours, mins = divmod(left // 60, 60)
                status = f"🏨 {HOTELS[home]['name']}\n⏱ Осталось: {hours}ч {mins}мин"
        elif home in HOUSES:
            status = f"🏡 {HOUSES[home]['name']} (навсегда)"

    await callback.message.delete()
    await callback.message.answer(
        f"🏠 <b>ЖИЛЬЁ</b>\n\n"
        f"📍 Статус: {status}\n"
        f"💰 Баланс: ${player['balance']}",
        reply_markup=home_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# СПИСОК ОТЕЛЕЙ
# ============================================
@router.callback_query(F.data == "hotels_menu")
async def hotels_menu(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🏨 <b>ОТЕЛИ (аренда)</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Выбери отель:",
        reply_markup=hotels_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# АРЕНДА ОТЕЛЯ
# ============================================
@router.callback_query(F.data.startswith("hotel_"))
async def rent_hotel(callback: CallbackQuery):
    hotel_key = callback.data.replace("hotel_", "")
    hotel = HOTELS.get(hotel_key)

    if not hotel:
        await callback.answer("Отель не найден")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["balance"] < hotel["price"]:
        await callback.answer(f"💰 Нужно ${hotel['price']}", show_alert=True)
        return

    new_balance = player["balance"] - hotel["price"]

    await update_player(
        callback.from_user.id,
        balance=new_balance,
        home=hotel_key,
    )

    rent_data[callback.from_user.id] = {
        "until": datetime.now() + timedelta(hours=hotel["duration"]),
        "type": hotel_key,
    }

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=hotel["photo"],
        caption=(
            f"✅ <b>ЗАСЕЛЁН!</b>\n\n"
            f"{hotel['name']}\n"
            f"⏱ На {hotel['duration']} ч\n"
            f"❤️ HP реген: +{hotel['hp_regen']}/час\n"
            f"💰 -${hotel['price']}\n\n"
            f"💰 Баланс: ${new_balance}"
        ),
        reply_markup=back_to_home_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Заселён!")


# ============================================
# СПИСОК ДОМОВ
# ============================================
@router.callback_query(F.data == "houses_menu")
async def houses_menu(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🏡 <b>ДОМА (навсегда)</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Выбери дом:",
        reply_markup=houses_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ПОКУПКА ДОМА
# ============================================
@router.callback_query(F.data.startswith("house_"))
async def buy_house(callback: CallbackQuery):
    house_key = callback.data.replace("house_", "")
    house = HOUSES.get(house_key)

    if not house:
        await callback.answer("Дом не найден")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["balance"] < house["price"]:
        await callback.answer(f"💰 Нужно ${house['price']:,}", show_alert=True)
        return

    new_balance = player["balance"] - house["price"]

    await update_player(
        callback.from_user.id,
        balance=new_balance,
        home=house_key,
    )

    income_text = ""
    if "income" in house:
        income_text = f"\n💰 Доход: +${house['income']}/час"

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=house["photo"],
        caption=(
            f"✅ <b>КУПЛЕНО!</b>\n\n"
            f"{house['name']}\n"
            f"❤️ HP реген: +{house['hp_regen']}/час{income_text}\n"
            f"💰 -${house['price']:,}\n\n"
            f"💰 Баланс: ${new_balance:,}"
        ),
        reply_markup=back_to_home_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Куплено!")


# ============================================
# ПОСПАТЬ
# ============================================
@router.callback_query(F.data == "sleep")
async def sleep(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if not player["home"]:
        await callback.answer("Сначала купи/сними жильё", show_alert=True)
        return

    from handlers.jobs import job_cooldowns, taxi_state
    from handlers.crime import crime_cooldowns

    if callback.from_user.id in job_cooldowns:
        job_cooldowns[callback.from_user.id] = {}

    if callback.from_user.id in crime_cooldowns:
        crime_cooldowns[callback.from_user.id] = {}

    if callback.from_user.id in taxi_state:
        taxi_state[callback.from_user.id]["last_order"] = None

    await update_player(callback.from_user.id, hp=100)

    await callback.message.delete()
    await callback.message.answer(
        f"🛏 <b>ТЫ ПОСПАЛ</b>\n\n"
        f"✅ Все кулдауны сброшены\n"
        f"❤️ HP восстановлен: 100/100",
        reply_markup=back_to_home_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Проснулся!")
