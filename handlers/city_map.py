# ============================================
# КАРТА (перемещение между районами)
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
)


router = Router()


# ============================================
# РАЙОНЫ
# ============================================
DISTRICTS = {
    "ganton": {
        "name": "🟢 Ganton",
        "faction": "Grove Street",
        "buildings": ["🏪 Магазин 24/7", "🏥 Больница", "🏨 Мотель"],
    },
    "idlewood": {
        "name": "🟣 Idlewood",
        "faction": "Ballas",
        "buildings": ["🏪 Магазин 24/7", "🔫 Арсенал", "🍔 Кафе"],
    },
    "east_ls": {
        "name": "🔵 East LS",
        "faction": "Los Vagos",
        "buildings": ["🏪 Магазин 24/7", "💪 Качалка", "🔧 Автосервис"],
    },
    "el_corona": {
        "name": "⚪ El Corona",
        "faction": "Ацтеки",
        "buildings": ["🏪 Магазин 24/7", "🏨 Отель", "🍔 Кафе"],
    },
    "downtown": {
        "name": "💼 Downtown",
        "faction": "Нейтрал",
        "buildings": ["🏪 Магазин 24/7", "🏦 Банк", "🔫 Арсенал", "🚗 Автосалон"],
    },
    "beach": {
        "name": "🏖 Пляж",
        "faction": "Нейтрал",
        "buildings": ["🏪 Магазин 24/7", "🎰 Казино", "🏁 Гонки"],
    },
}

# Матрица расстояний (в минутах)
DISTANCES = {
    "ganton":    {"idlewood": 3, "east_ls": 6, "el_corona": 4, "downtown": 5, "beach": 8},
    "idlewood":  {"ganton": 3, "east_ls": 5, "el_corona": 3, "downtown": 4, "beach": 7},
    "east_ls":   {"ganton": 6, "idlewood": 5, "el_corona": 6, "downtown": 4, "beach": 5},
    "el_corona": {"ganton": 4, "idlewood": 3, "east_ls": 6, "downtown": 3, "beach": 8},
    "downtown":  {"ganton": 5, "idlewood": 4, "east_ls": 4, "el_corona": 3, "beach": 6},
    "beach":     {"ganton": 8, "idlewood": 7, "east_ls": 5, "el_corona": 8, "downtown": 6},
}

# Множители скорости транспорта
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

# Цены такси
TAXI_PRICE_NPC = 350
TAXI_PRICE_PLAYER = 500
TAXI_CANCEL_PENALTY = 100

# Хранилище поездок (в оперативке)
active_travels = {}   # {telegram_id: {...}}


# ============================================
# РАСЧЁТ ВРЕМЕНИ
# ============================================
def get_travel_time(from_district: str, to_district: str, player: dict) -> float:
    """Возвращает время поездки в минутах."""
    base = DISTANCES.get(from_district, {}).get(to_district, 5)

    # Множитель транспорта
    if player.get("car"):
        mult = CAR_MULTIPLIERS.get(player["car"], 1.5)
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

    await callback.message.edit_text(
        f"🗺 <b>КАРТА LOS SANTOS</b>\n\n"
        f"📍 Ты в: {DISTRICTS[current]['name']}\n\n"
        f"Куда ехать?",
        reply_markup=map_menu_kb(current, player),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ПЕРЕЕЗД (пешком / на машине)
# ============================================
@router.callback_query(F.data.startswith("travel_"))
async def travel(callback: CallbackQuery):
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

    # Транспорт
    if player.get("car"):
        transport = f"🚗 {player['car']}"
    else:
        transport = "🚶 Пешком"

    # Сохраняем поездку
    active_travels[callback.from_user.id] = {
        "from": current,
        "to": to_district,
        "until": datetime.now() + timedelta(seconds=seconds),
        "type": "walk",  # или car
        "started": datetime.now(),
    }

    await callback.message.edit_text(
        f"🚶 <b>ТЫ В ПУТИ</b>\n\n"
        f"📍 {DISTRICTS[current]['name']} → {DISTRICTS[to_district]['name']}\n"
        f"🚗 Транспорт: {transport}\n\n"
        f"⏱ Осталось: {seconds // 60}:{seconds % 60:02d}",
        reply_markup=travel_cancel_kb() if player.get("car") else None,
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()

    # Запускаем обновление таймера
    asyncio.create_task(update_travel_timer(callback.from_user.id, callback.message))


# ============================================
# ТАКСИ
# ============================================
@router.callback_query(F.data == "taxi_menu")
async def taxi_menu(callback: CallbackQuery):
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
    to_district = callback.data.replace("taxi_to_", "")
    player = await get_player(callback.from_user.id)
    current = player.get("district_key") or "ganton"

    if to_district == current:
        await callback.answer("Ты уже здесь")
        return

    time_min = get_taxi_time(current, to_district)
    seconds = int(time_min * 60)

    # Ищем игрока-таксиста (пока заглушка — только NPC)
    # TODO: реальный поиск игроков
    taxi_type = "npc"
    price = TAXI_PRICE_NPC

    if player["balance"] < price:
        await callback.answer(f"💰 Нужно ${price}", show_alert=True)
        return

    # Списываем деньги
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

    # Только для такси — штраф
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
# ПРИБЫТИЕ
# ============================================
@router.callback_query(F.data == "district_view")
async def district_view(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    current = player.get("district_key") or "ganton"
    district = DISTRICTS[current]

    buildings_text = "\n".join(f"[ {b} ]" for b in district["buildings"])

    await callback.message.edit_text(
        f"📍 <b>ТЫ В: {district['name']}</b>\n\n"
        f"🚩 Территория: {district['faction']}\n\n"
        f"🏢 Здания:\n{buildings_text}",
        reply_markup=district_view_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ТАЙМЕР ОБНОВЛЕНИЯ
# ============================================
async def update_travel_timer(telegram_id: int, message: Message):
    """Обновляет таймер каждые 20 сек. По окончании — прибытие."""
    while True:
        await asyncio.sleep(20)

        travel = active_travels.get(telegram_id)
        if not travel:
            return

        now = datetime.now()
        if now >= travel["until"]:
            # Прибытие
            player = await get_player(telegram_id)
            await update_player(
                telegram_id,
                district_key=travel["to"],
                district=DISTRICTS[travel["to"]]["name"],
            )
            active_travels.pop(telegram_id, None)

            district = DISTRICTS[travel["to"]]
            buildings_text = "\n".join(f"[ {b} ]" for b in district["buildings"])

            try:
                await message.edit_text(
                    f"✅ <b>ТЫ ПРИБЫЛ!</b>\n\n"
                    f"📍 Ты в: {district['name']}\n"
                    f"🚩 Территория: {district['faction']}\n\n"
                    f"🏢 Здания:\n{buildings_text}",
                    reply_markup=district_view_kb(),
                    parse_mode=ParseMode.HTML,
                )
            except:
                pass
            return

        # Обновляем таймер
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
                    reply_markup=travel_cancel_kb(),
                    parse_mode=ParseMode.HTML,
                )
        except:
            pass
