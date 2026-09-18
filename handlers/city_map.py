# ============================================
# КАРТА + ЗДАНИЯ
# ============================================

import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from handlers.crime import is_in_jail
from keyboards import (
    map_menu_kb, travel_taxi_kb, travel_cancel_kb,
    district_view_kb, back_to_map_kb,
    shop_menu_kb, hospital_menu_kb, hospital_back_kb,
    bank_menu_kb, bank_create_kb,
    arsenal_menu_kb, autoservice_menu_kb, autoservice_back_kb,
    casino_menu_kb, race_menu_kb, home_menu_kb, transport_menu_kb,
)


router = Router()


# ============================================
# РАЙОНЫ
# ============================================
DISTRICTS = {
    "ganton": {
        "name": "🟢 Ganton",
        "faction": "Grove Street",
        "buildings": [
            {"name": "🏪 Магазин 24/7", "callback": "open_shop"},
            {"name": "🏥 Больница", "callback": "open_hospital"},
            {"name": "🏨 Мотель", "callback": "open_home"},
        ],
    },
    "idlewood": {
        "name": "🟣 Idlewood",
        "faction": "Ballas",
        "buildings": [
            {"name": "🏪 Магазин 24/7", "callback": "open_shop"},
            {"name": "🏥 Больница", "callback": "open_hospital"},
            {"name": "🔫 Арсенал", "callback": "open_arsenal"},
        ],
    },
    "east_ls": {
        "name": "🔵 East LS",
        "faction": "Los Vagos",
        "buildings": [
            {"name": "🏪 Магазин 24/7", "callback": "open_shop"},
            {"name": "🔧 Автосервис", "callback": "open_autoservice"},
            {"name": "🏁 Трек", "callback": "open_race"},
        ],
    },
    "el_corona": {
        "name": "⚪ El Corona",
        "faction": "Ацтеки",
        "buildings": [
            {"name": "🏪 Магазин 24/7", "callback": "open_shop"},
            {"name": "🏥 Больница", "callback": "open_hospital"},
            {"name": "🏨 Отель", "callback": "open_home"},
        ],
    },
    "downtown": {
        "name": "💼 Downtown",
        "faction": "Нейтрал",
        "buildings": [
            {"name": "🏪 Магазин 24/7", "callback": "open_shop"},
            {"name": "🏥 Больница", "callback": "open_hospital"},
            {"name": "🏦 Банк", "callback": "open_bank"},
            {"name": "🔫 Арсенал", "callback": "open_arsenal"},
            {"name": "🚗 Автосалон", "callback": "open_transport"},
        ],
    },
    "beach": {
        "name": "🏖 Пляж",
        "faction": "Нейтрал",
        "buildings": [
            {"name": "🏪 Магазин 24/7", "callback": "open_shop"},
            {"name": "🎰 Казино", "callback": "open_casino"},
            {"name": "🏁 Трек", "callback": "open_race"},
        ],
    },
}

DISTANCES = {
    "ganton":    {"idlewood": 3, "east_ls": 6, "el_corona": 4, "downtown": 5, "beach": 8},
    "idlewood":  {"ganton": 3, "east_ls": 5, "el_corona": 3, "downtown": 4, "beach": 7},
    "east_ls":   {"ganton": 6, "idlewood": 5, "el_corona": 6, "downtown": 4, "beach": 5},
    "el_corona": {"ganton": 4, "idlewood": 3, "east_ls": 6, "downtown": 3, "beach": 8},
    "downtown":  {"ganton": 5, "idlewood": 4, "east_ls": 4, "el_corona": 3, "beach": 6},
    "beach":     {"ganton": 8, "idlewood": 7, "east_ls": 5, "el_corona": 8, "downtown": 6},
}

CAR_MULTIPLIERS = {
    "sedan": 1.5, "truck": 1.5, "minivan": 1.4,
    "suv": 1.2, "chopper": 1.2,
    "moto": 1.0,
    "tuned": 0.7,
    "sportcar": 0.5, "sportbike": 0.5,
    "supercar": 0.3,
}

WALK_MULTIPLIER = 2.0
TAXI_MULTIPLIER = 0.5

ENGINE_MULTIPLIERS = {0: 1.0, 1: 0.9, 2: 0.8, 3: 0.7}
NITRO_MULTIPLIER = 0.7

TAXI_PRICE_NPC = 350
TAXI_PRICE_PLAYER = 500
TAXI_CANCEL_PENALTY = 100

active_travels = {}


# ============================================
# РАСЧЁТ ВРЕМЕНИ
# ============================================
def get_travel_time(from_district: str, to_district: str, player: dict) -> float:
    base = DISTANCES.get(from_district, {}).get(to_district, 5)

    if player.get("car"):
        mult = CAR_MULTIPLIERS.get(player["car"], 1.5)
        engine = player.get("engine_level", 0)
        mult *= ENGINE_MULTIPLIERS.get(engine, 1.0)
        if player.get("nitro", 0):
            mult *= NITRO_MULTIPLIER
    else:
        mult = WALK_MULTIPLIER

    return base * mult


def get_taxi_time(from_district: str, to_district: str) -> float:
    base = DISTANCES.get(from_district, {}).get(to_district, 5)
    return base * TAXI_MULTIPLIER


# ============================================
# МЕНЮ КАРТЫ
# ============================================
@router.message(F.text == "🗺 Карта")
async def map_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    if is_in_jail(message.from_user.id):
        await message.answer("🚔 Ты в тюрьме, карта недоступна.")
        return

    travel = active_travels.get(message.from_user.id)
    if travel:
        now = datetime.now()
        left = int((travel["until"] - now).total_seconds())
        if left > 0:
            mins, secs = divmod(left, 60)
            await message.answer(
                f"🚶 <b>ТЫ В ПУТИ</b>\n\n"
                f"📍 {DISTRICTS[travel['from']]['name']} → {DISTRICTS[travel['to']]['name']}\n\n"
                f"⏱ Осталось: {mins}:{secs:02d}\n\n"
                f"Подожди окончания поездки!",
                parse_mode=ParseMode.HTML,
            )
            return

    current = player.get("district_key") or "ganton"

    await message.answer(
        f"🗺 <b>КАРТА LOS SANTOS</b>\n\n"
        f"📍 Ты в: {DISTRICTS[current]['name']}\n\n"
        f"Куда ехать?",
        reply_markup=map_menu_kb(current, player),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "map_back")
async def map_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    current = player.get("district_key") or "ganton"

    await callback.message.delete()
    await callback.message.answer(
        f"🗺 <b>КАРТА LOS SANTOS</b>\n\n"
        f"📍 Ты в: {DISTRICTS[current]['name']}\n\n"
        f"Куда ехать?",
        reply_markup=map_menu_kb(current, player),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ПЕРЕЕЗД
# ============================================
@router.callback_query(F.data.startswith("travel_"))
async def travel(callback: CallbackQuery):
    existing = active_travels.get(callback.from_user.id)
    if existing:
        await callback.answer("⚠️ Ты уже в пути!", show_alert=True)
        return

    to_district = callback.data.replace("travel_", "")
    player = await get_player(callback.from_user.id)
    current = player.get("district_key") or "ganton"

    if to_district == current:
        await callback.answer("Ты уже здесь")
        return

    if to_district not in DISTRICTS:
        await callback.answer("Район не найден")
        return

    time_min = get_travel_time(current, to_district, player)
    seconds = int(time_min * 60)

    if player.get("car"):
        transport = f"🚗 {player['car']}"
    else:
        transport = "🚶 Пешком"

    active_travels[callback.from_user.id] = {
        "from": current,
        "to": to_district,
        "until": datetime.now() + timedelta(seconds=seconds),
        "type": "walk",
        "started": datetime.now(),
    }

    await callback.message.edit_text(
        f"🚶 <b>ТЫ В ПУТИ</b>\n\n"
        f"📍 {DISTRICTS[current]['name']} → {DISTRICTS[to_district]['name']}\n"
        f"🚗 Транспорт: {transport}\n\n"
        f"⏱ Осталось: {seconds // 60}:{seconds % 60:02d}",
        reply_markup=None,
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()

    asyncio.create_task(update_travel_timer(callback.from_user.id, callback.message))


# ============================================
# ТАКСИ
# ============================================
@router.callback_query(F.data == "map_taxi_menu")
async def map_taxi_menu(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    current = player.get("district_key") or "ganton"

    await callback.message.edit_text(
        f"🚕 <b>ТАКСИ</b>\n\n"
        f"📍 Откуда: {DISTRICTS[current]['name']}\n\n"
        f"Куда ехать?",
        reply_markup=travel_taxi_kb(current),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("taxi_to_"))
async def taxi_to(callback: CallbackQuery):
    existing = active_travels.get(callback.from_user.id)
    if existing:
        await callback.answer("⚠️ Ты уже в пути!", show_alert=True)
        return

    to_district = callback.data.replace("taxi_to_", "")
    player = await get_player(callback.from_user.id)
    current = player.get("district_key") or "ganton"

    if to_district == current:
        await callback.answer("Ты уже здесь")
        return

    time_min = get_taxi_time(current, to_district)
    seconds = int(time_min * 60)

    taxi_type = "npc"
    price = TAXI_PRICE_NPC

    if player["balance"] < price:
        await callback.answer(f"💰 Нужно ${price}", show_alert=True)
        return

    await update_player(callback.from_user.id, balance=player["balance"] - price)

    active_travels[callback.from_user.id] = {
        "from": current,
        "to": to_district,
        "until": datetime.now() + timedelta(seconds=seconds),
        "type": "taxi",
        "taxi_type": taxi_type,
        "price": price,
        "started": datetime.now(),
    }

    await callback.message.edit_text(
        f"🚕 <b>ТЫ В ТАКСИ</b>\n\n"
        f"📍 {DISTRICTS[current]['name']} → {DISTRICTS[to_district]['name']}\n"
        f"💰 Оплачено: ${price}\n\n"
        f"⏱ Осталось: {seconds // 60}:{seconds % 60:02d}",
        reply_markup=travel_cancel_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()

    asyncio.create_task(update_travel_timer(callback.from_user.id, callback.message))


# ============================================
# ОТМЕНА ПОЕЗДКИ
# ============================================
@router.callback_query(F.data == "travel_cancel")
async def travel_cancel(callback: CallbackQuery):
    travel = active_travels.get(callback.from_user.id)
    if not travel:
        await callback.answer("Ты не в пути")
        return

    if travel["type"] == "taxi":
        player = await get_player(callback.from_user.id)
        await update_player(
            callback.from_user.id,
            balance=player["balance"] + travel["price"] - TAXI_CANCEL_PENALTY,
        )

    active_travels.pop(callback.from_user.id, None)

    await callback.message.edit_text(
        f"❌ <b>ПОЕЗДКА ОТМЕНЕНА</b>\n\n"
        f"Штраф: ${TAXI_CANCEL_PENALTY if travel['type'] == 'taxi' else 0}",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Отменено")


# ============================================
# ПРОСМОТР РАЙОНА (с кнопками зданий)
# ============================================
@router.callback_query(F.data == "district_view")
async def district_view(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    current = player.get("district_key") or "ganton"
    district = DISTRICTS[current]

    buttons = []
    for b in district["buildings"]:
        buttons.append([InlineKeyboardButton(text=b["name"], callback_data=b["callback"])])

    buttons.append([InlineKeyboardButton(text="🗺 Карта", callback_data="map_back")])
    buttons.append([InlineKeyboardButton(text="🔙 В город", callback_data="to_city")])

    await callback.message.edit_text(
        f"📍 <b>ТЫ В: {district['name']}</b>\n\n"
        f"🚩 Территория: {district['faction']}\n\n"
        f"🏢 Здания:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# КНОПКА «ЗДАНИЯ» — текущий район
# ============================================
@router.message(F.text == "🏢 Здания")
async def buildings_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    current = player.get("district_key") or "ganton"
    district = DISTRICTS[current]

    if not district.get("buildings"):
        await message.answer(
            f"🏢 <b>ЗДАНИЯ</b>\n\n"
            f"📍 Район: {district['name']}\n\n"
            f"В этом районе нет зданий.",
            reply_markup=back_to_map_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    buttons = []
    for b in district["buildings"]:
        buttons.append([InlineKeyboardButton(text=b["name"], callback_data=b["callback"])])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="to_city")])

    await message.answer(
        f"🏢 <b>ЗДАНИЯ</b>\n\n"
        f"📍 Район: {district['name']}\n\n"
        f"Выбери здание:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# ХЕНДЛЕРЫ ОТКРЫТИЯ ЗДАНИЙ
# ============================================
@router.callback_query(F.data == "open_shop")
async def open_shop(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer(
        f"🏪 <b>МАГАЗИН 24/7</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n"
        f"❤️ HP: {player['hp']}/100\n\n"
        f"Выбери товар:",
        reply_markup=shop_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "open_hospital")
async def open_hospital(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if player["hp"] >= 100:
        await callback.message.delete()
        await callback.message.answer(
            f"🏥 <b>БОЛЬНИЦА</b>\n\n"
            f"❤️ HP: {player['hp']}/100\n\n"
            f"Ты здоров! Лечение не нужно.",
            reply_markup=hospital_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    else:
        text = (
            f"🏥 <b>БОЛЬНИЦА</b>\n\n"
            f"❤️ Твоё HP: {player['hp']}/100\n\n"
            f"💰 Лечение: $500\n"
            f"❤️ Восстановит: 100/100\n"
        )
        if player["balance"] < 500:
            text += f"\n❌ <b>Не хватает денег!</b>\n💰 У тебя: ${player['balance']}"

        await callback.message.delete()
        await callback.message.answer(
            text,
            reply_markup=hospital_menu_kb(player["balance"], player["hp"]),
            parse_mode=ParseMode.HTML,
        )
    await callback.answer()


@router.callback_query(F.data == "open_bank")
async def open_bank(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if not player.get("bank_account"):
        await callback.message.delete()
        await callback.message.answer(
            f"🏦 <b>БАНК</b>\n\n"
            f"У тебя нет банковского счёта.\n\n"
            f"Создать счёт?",
            reply_markup=bank_create_kb(),
            parse_mode=ParseMode.HTML,
        )
    else:
        bank_balance = player.get("bank_balance", 0) or 0
        deposit = player.get("bank_deposit", 0) or 0
        await callback.message.delete()
        await callback.message.answer(
            f"🏦 <b>БАНК</b>\n\n"
            f"💳 Счёт: <code>{player['bank_account']}</code>\n"
            f"💰 На счёте: ${bank_balance}\n"
            f"💼 Вклад: ${deposit}",
            reply_markup=bank_menu_kb(bank_balance, deposit),
            parse_mode=ParseMode.HTML,
        )
    await callback.answer()


@router.callback_query(F.data == "open_arsenal")
async def open_arsenal(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    weapon = player.get("weapon") or "нет"

    await callback.message.delete()
    await callback.message.answer(
        f"🔫 <b>АРСЕНАЛ</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n"
        f"🔫 Оружие: {weapon}\n\n"
        f"Выбери товар:",
        reply_markup=arsenal_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "open_autoservice")
async def open_autoservice(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if not player.get("car"):
        await callback.message.delete()
        await callback.message.answer(
            f"🔧 <b>АВТОСЕРВИС</b>\n\n"
            f"❌ У тебя нет машины!\n\n"
            f"Сначала купи машину в автосалоне.",
            reply_markup=autoservice_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    else:
        engine = player.get("engine_level", 0)
        nitro = player.get("nitro", 0)
        nitro_text = "да" if nitro else "нет"

        await callback.message.delete()
        await callback.message.answer_photo(
            photo="https://i.ibb.co/ns0ZMzHf/Screenshot-20260918-175758.jpg",
            caption=(
                f"🔧 <b>АВТОСЕРВИС</b>\n\n"
                f"🚗 Машина: {player['car']}\n"
                f"🔧 Двигатель: ур.{engine}\n"
                f"💨 Нитро: {nitro_text}\n\n"
                f"💰 Баланс: ${player['balance']}"
            ),
            reply_markup=autoservice_menu_kb(engine, nitro),
            parse_mode=ParseMode.HTML,
        )
    await callback.answer()


@router.callback_query(F.data == "open_casino")
async def open_casino(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🎰 <b>КАЗИНО</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Выбери игру:",
        reply_markup=casino_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "open_race")
async def open_race(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    car = player.get("car")
    car_name = car if car else "нет"

    await callback.message.delete()
    await callback.message.answer_photo(
        photo="https://i.ibb.co/M5x6W1Ty/Screenshot-20260918-141348.jpg",
        caption=(
            f"🏁 <b>ТРЕК</b>\n\n"
            f"📍 Район: {player['district']}\n"
            f"🚗 Машина: {car_name}\n\n"
            f"Добро пожаловать на гонки!"
        ),
        reply_markup=race_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "open_home")
async def open_home(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🏨 <b>ЖИЛЬЁ</b>\n\n"
        f"💰 Баланс: ${player['balance']}",
        reply_markup=home_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "open_transport")
async def open_transport(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🚗 <b>АВТОСАЛОН</b>\n\n"
        f"💰 Баланс: ${player['balance']}",
        reply_markup=transport_menu_kb(player.get("car")),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ТАЙМЕР ПОЕЗДКИ
# ============================================
async def update_travel_timer(telegram_id: int, message: Message):
    while True:
        await asyncio.sleep(20)

        travel = active_travels.get(telegram_id)
        if not travel:
            return

        now = datetime.now()
        if now >= travel["until"]:
            await update_player(
                telegram_id,
                district_key=travel["to"],
                district=DISTRICTS[travel["to"]]["name"],
            )
            active_travels.pop(telegram_id, None)

            district = DISTRICTS[travel["to"]]

            buttons = []
            for b in district["buildings"]:
                buttons.append([InlineKeyboardButton(text=b["name"], callback_data=b["callback"])])
            buttons.append([InlineKeyboardButton(text="🗺 Карта", callback_data="map_back")])
            buttons.append([InlineKeyboardButton(text="🔙 В город", callback_data="to_city")])

            try:
                await message.edit_text(
                    f"✅ <b>ТЫ ПРИБЫЛ!</b>\n\n"
                    f"📍 Ты в: {district['name']}\n"
                    f"🚩 Территория: {district['faction']}\n\n"
                    f"🏢 Здания:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                    parse_mode=ParseMode.HTML,
                )
            except:
                pass
            return

        left = int((travel["until"] - now).total_seconds())
        mins, secs = divmod(left, 60)

        try:
            if travel["type"] == "taxi":
                await message.edit_text(
                    f"🚕 <b>ТЫ В ТАКСИ</b>\n\n"
                    f"📍 {DISTRICTS[travel['from']]['name']} → {DISTRICTS[travel['to']]['name']}\n"
                    f"💰 Оплачено: ${travel['price']}\n\n"
                    f"⏱ Осталось: {mins}:{secs:02d}",
                    reply_markup=travel_cancel_kb(),
                    parse_mode=ParseMode.HTML,
                )
            else:
                await message.edit_text(
                    f"🚶 <b>ТЫ В ПУТИ</b>\n\n"
                    f"📍 {DISTRICTS[travel['from']]['name']} → {DISTRICTS[travel['to']]['name']}\n\n"
                    f"⏱ Осталось: {mins}:{secs:02d}",
                    reply_markup=None,
                    parse_mode=ParseMode.HTML,
                )
        except:
            pass
