# ============================================
# ВСЕ КЛАВИАТУРЫ БОТА
# ============================================

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from config import FACTIONS, SUPPORT_USERNAME


# ============================================
# REPLY-МЕНЮ (снизу)
# ============================================
def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="⚔️ Криминал"), KeyboardButton(text="🛒 Магазин")],
            [KeyboardButton(text="🏠 Жильё"), KeyboardButton(text="🚗 Транспорт")],
            [KeyboardButton(text="🗺 Карта"), KeyboardButton(text="🏢 Здания")],
            [KeyboardButton(text="🏆 Топ")],
        ],
        resize_keyboard=True,
    )


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
        buttons.append([InlineKeyboardButton(
            text="⏳ Лимит исчерпан (10/10)",
            callback_data="noop",
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text=f"🚕 Начать смену ({hourly_count}/10)",
            callback_data="taxi_start_shift",
        )])

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
            buttons.append([InlineKeyboardButton(
                text=f"🔒 {text} (ур.{lvl})",
                callback_data="noop",
            )])
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
        [InlineKeyboardButton(text="👨‍⚖️ Адвокат — $10000", callback_data="jail_lawyer")],
        [InlineKeyboardButton(text="⏳ Ждать", callback_data="jail_wait")],
    ])


# ============================================
# МАГАЗИН
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
        [InlineKeyboardButton(text="🏥 Лечение (полный HP) — $50", callback_data="buy_heal")],
    ])


def shop_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В магазин", callback_data="shop_back")],
    ])


# ============================================
# ИНВЕНТАРЬ
# ============================================
def inventory_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="inv_back")],
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


def garage_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Продать машину (70%)", callback_data="sell_car")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="transport_back")],
    ])


def back_to_transport_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К транспорту", callback_data="transport_back")],
    ])
