# ============================================
# ВСЕ КЛАВИАТУРЫ БОТА
# ============================================

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from config import FACTIONS, SUPPORT_USERNAME


# ============================================
# REPLY-МЕНЮ (2 страницы)
# ============================================
def main_menu_kb(page: int = 1):
    if page == 2:
        keyboard = [
            [KeyboardButton(text="🗺 Карта"), KeyboardButton(text="🏢 Здания")],
            [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="⚔️ PvP")],
            [KeyboardButton(text="🚩 Банды"), KeyboardButton(text="🛏 Поспать")],
            [KeyboardButton(text="⬅️ Назад")],
        ]
    else:
        keyboard = [
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="⚔️ Криминал"), KeyboardButton(text="🛒 Магазин")],
            [KeyboardButton(text="🏠 Жильё"), KeyboardButton(text="🚗 Транспорт")],
            [KeyboardButton(text="➡️ Вперёд")],
        ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# ============================================
# РЕГИСТРАЦИЯ
# ============================================
def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 Создать персонажа", callback_data="reg_start")],
    ])


def gender_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male"),
         InlineKeyboardButton(text="👩 Женский", callback_data="gender_female")],
    ])


def faction_kb():
    buttons = []
    for key, data in FACTIONS.items():
        buttons.append([InlineKeyboardButton(
            text=f"{data['emoji']} {data['name']} — {data['district']}",
            callback_data=f"faction_{key}",
        )])
    buttons.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data="faction_skip")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def to_city_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗺 В город", callback_data="to_city")],
    ])


# ============================================
# ПРОФИЛЬ
# ============================================
def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])


def inventory_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="inv_back")],
    ])


# ============================================
# РАБОТЫ
# ============================================
def jobs_menu_kb(level: int):
    buttons = []
    jobs = [
        ("pizza", "🍔 Пицца — $100", 1),
        ("courier", "📦 Курьер — $150", 1),
        ("loader", "🏗 Грузчик — $300", 5),
        ("trucker", "🚚 Дальнобой — $800", 10),
    ]
    for key, text, lvl in jobs:
        if level >= lvl:
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"job_{key}")])
        else:
            buttons.append([InlineKeyboardButton(
                text=f"🔒 {text} (ур.{lvl})",
                callback_data="noop",
            )])
    buttons.append([InlineKeyboardButton(text="🚕 Такси (PvP)", callback_data="taxi_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_jobs_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К работам", callback_data="jobs_back")],
    ])


def taxi_menu_kb(hourly_count: int = 0):
    buttons = []
    if hourly_count >= 10:
        buttons.append([InlineKeyboardButton(text="⏳ Лимит исчерпан (10/10)", callback_data="noop")])
    else:
        buttons.append([InlineKeyboardButton(text=f"🚕 Начать смену ({hourly_count}/10)", callback_data="taxi_start_shift")])
    buttons.append([InlineKeyboardButton(text="🔙 К работам", callback_data="jobs_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def taxi_orders_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Ждать NPC-заказ", callback_data="taxi_wait_order")],
        [InlineKeyboardButton(text="🚪 Закончить смену", callback_data="taxi_stop_shift")],
    ])


def taxi_client_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Вызвать такси", callback_data="taxi_call")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="jobs_back")],
    ])


def taxi_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="jobs_back")],
    ])


# ============================================
# КРИМИНАЛ
# ============================================
def crime_menu_kb(level: int):
    buttons = []
    crimes = [
        ("car", "🚗 Угон — $500+", 1),
        ("shop", "🏪 Грабёж — $1000+", 3),
        ("drugs", "💊 Наркотики — $2000+", 5),
        ("bank", "🏦 Банк — $10000+", 10),
    ]
    for key, text, lvl in crimes:
        if level >= lvl:
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"crime_{key}")])
        else:
            buttons.append([InlineKeyboardButton(text=f"🔒 {text} (ур.{lvl})", callback_data="noop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_crime_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К криминалу", callback_data="crime_back")],
    ])


# ============================================
# ТЮРЬМА
# ============================================
def jail_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍⚖️ Адвокат — $2000", callback_data="jail_lawyer")],
        [InlineKeyboardButton(text="🏃 Побег (30%)", callback_data="jail_escape")],
        [InlineKeyboardButton(text="⏳ Ждать", callback_data="jail_wait")],
    ])


# ============================================
# МАГАЗИН (без лечения!)
# ============================================
def shop_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔫 Пистолет — $500 (+10%)", callback_data="buy_pistol")],
        [InlineKeyboardButton(text="🔫🔫 SMG — $2000 (+15%)", callback_data="buy_smg")],
        [InlineKeyboardButton(text="🎯 Дробовик — $3500 (+18%)", callback_data="buy_shotgun")],
        [InlineKeyboardButton(text="💥 Автомат — $8000 (+20%)", callback_data="buy_rifle")],
        [InlineKeyboardButton(text="🛡 Броня — $1500 (+30%)", callback_data="buy_armor")],
        [InlineKeyboardButton(text="💊 Аптечка — $300 (+50 HP)", callback_data="buy_medkit")],
        [InlineKeyboardButton(text="🍔 Еда — $50 (+20 HP)", callback_data="buy_food")],
    ])


def shop_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В магазин", callback_data="shop_back")],
    ])


# ============================================
# ТРАНСПОРТ
# ============================================
def transport_menu_kb(current_car=None):
    buttons = []
    buttons.append([InlineKeyboardButton(text="🏎 Автосалон", callback_data="autosalon")])
    if current_car:
        buttons.append([InlineKeyboardButton(text="🏠 Мой гараж", callback_data="garage")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def autosalon_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Sedan — $5,000 (3/10)", callback_data="car_sedan")],
        [InlineKeyboardButton(text="🚐 Минивэн — $8,000 (4/10)", callback_data="car_minivan")],
        [InlineKeyboardButton(text="🚙 Внедорожник — $12,000 (5/10)", callback_data="car_suv")],
        [InlineKeyboardButton(text="🏎 Спорткар — $25,000 (9/10)", callback_data="car_sportcar")],
        [InlineKeyboardButton(text="🏎 Тюнингованная — $35,000 (8/10)", callback_data="car_tuned")],
        [InlineKeyboardButton(text="🏎 Суперкар — $50,000 (10/10)", callback_data="car_supercar")],
        [InlineKeyboardButton(text="🏍 Мотоцикл — $8,000 (6/10)", callback_data="car_moto")],
        [InlineKeyboardButton(text="🏍 Чоппер — $15,000 (5/10)", callback_data="car_chopper")],
        [InlineKeyboardButton(text="🏍 Спорт-байк — $18,000 (9/10)", callback_data="car_sportbike")],
        [InlineKeyboardButton(text="🚚 Грузовик — $30,000 (+30% грузчик)", callback_data="car_truck")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="transport_back")],
    ])


def car_info_kb(car_key: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купить", callback_data=f"buycar_{car_key}")],
        [InlineKeyboardButton(text="🔙 Назад в салон", callback_data="autosalon")],
    ])


def garage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Продать машину (70%)", callback_data="sell_car")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="transport_back")],
    ])


def back_to_transport_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К транспорту", callback_data="transport_back")],
    ])


# ============================================
# ЖИЛЬЁ
# ============================================
def home_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏨 Отели (аренда)", callback_data="hotels_menu")],
        [InlineKeyboardButton(text="🏡 Дома (навсегда)", callback_data="houses_menu")],
        [InlineKeyboardButton(text="🛏 Поспать (сброс КД)", callback_data="sleep")],
    ])


def hotels_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏨 Мотель — $100/24ч", callback_data="hotel_motel")],
        [InlineKeyboardButton(text="🏨 Downtown — $500/24ч", callback_data="hotel_downtown")],
        [InlineKeyboardButton(text="🏨 Ritz — $2000/24ч", callback_data="hotel_ritz")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="home_back")],
    ])


def houses_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏡 Гантон — $5,000", callback_data="house_ganton_house")],
        [InlineKeyboardButton(text="🏰 Особняк — $50,000", callback_data="house_mansion")],
        [InlineKeyboardButton(text="🏢 Бизнес-центр — $500,000", callback_data="house_business")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="home_back")],
    ])


def back_to_home_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К жилью", callback_data="home_back")],
    ])


# ============================================
# БАНДЫ
# ============================================
def gang_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сменить банду", callback_data="change_gang")],
        [InlineKeyboardButton(text="🚪 Выйти из банды", callback_data="leave_gang")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="gang_back")],
    ])


def gang_choose_kb():
    buttons = []
    for key, data in FACTIONS.items():
        buttons.append([InlineKeyboardButton(
            text=f"{data['emoji']} {data['name']} — {data['district']}",
            callback_data=f"join_gang_{key}",
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="gang_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_gang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К бандам", callback_data="gang_back")],
    ])


# ============================================
# PVP
# ============================================
def pvp_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Найти соперника", callback_data="pvp_search")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pvp_back")],
    ])


def pvp_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В меню PvP", callback_data="pvp_back")],
    ])


def pvp_opponents_kb(opponents: list):
    buttons = []
    for opp in opponents[:5]:
        buttons.append([InlineKeyboardButton(
            text=f"👤 {opp['nickname']} (Ур.{opp['level']})",
            callback_data=f"pvp_opp_{opp['telegram_id']}",
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pvp_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pvp_bet_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Ставка $100", callback_data="pvp_bet_100")],
        [InlineKeyboardButton(text="💰 Ставка $500", callback_data="pvp_bet_500")],
        [InlineKeyboardButton(text="💰 Ставка $1000", callback_data="pvp_bet_1000")],
        [InlineKeyboardButton(text="💰 Ставка $5000", callback_data="pvp_bet_5000")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pvp_back")],
    ])


def pvp_challenge_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Начать бой", callback_data="pvp_fight")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="pvp_back")],
    ])


# ============================================
# КАРТА
# ============================================
def map_menu_kb(current: str, player: dict):
    buttons = []

    districts_order = ["ganton", "idlewood", "east_ls", "el_corona", "downtown", "beach"]
    for key in districts_order:
        if key == current:
            continue

        from handlers.city_map import DISTANCES, DISTRICTS, CAR_MULTIPLIERS, WALK_MULTIPLIER

        base = DISTANCES.get(current, {}).get(key, 5)

        if player.get("car"):
            mult = CAR_MULTIPLIERS.get(player["car"], 1.5)
        else:
            mult = WALK_MULTIPLIER

        time_min = base * mult
        time_str = f"{time_min:.1f}м" if time_min < 10 else f"{int(time_min)}м"

        name = DISTRICTS[key]["name"]

        buttons.append([InlineKeyboardButton(
            text=f"{name} — {time_str}",
            callback_data=f"travel_{key}",
        )])

    buttons.append([InlineKeyboardButton(text="🚕 Вызвать такси", callback_data="map_taxi_menu")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="to_city")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def travel_taxi_kb(current: str):
    buttons = []
    districts_order = ["ganton", "idlewood", "east_ls", "el_corona", "downtown", "beach"]

    from handlers.city_map import DISTRICTS, get_taxi_time

    for key in districts_order:
        if key == current:
            continue

        time_min = get_taxi_time(current, key)
        time_str = f"{time_min:.1f}м" if time_min < 10 else f"{int(time_min)}м"
        name = DISTRICTS[key]["name"]

        buttons.append([InlineKeyboardButton(
            text=f"{name} — {time_str}",
            callback_data=f"taxi_to_{key}",
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="map_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def travel_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить поездку", callback_data="travel_cancel")],
    ])


def district_view_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗺 Карта", callback_data="map_back")],
        [InlineKeyboardButton(text="🔙 В город", callback_data="to_city")],
    ])


def back_to_map_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К карте", callback_data="map_back")],
    ])
