from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from config import FACTIONS, SUPPORT_USERNAME


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


def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])
# ============================================
# КНОПКИ ДЛЯ РАБОТ
# ============================================
def jobs_menu_kb(level: int):
    buttons = []

    # NPC-работы
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
            buttons.append([InlineKeyboardButton(text=f"🔒 {text} (ур.{lvl})", callback_data="noop")])

    # Такси
    buttons.append([InlineKeyboardButton(text="🚕 Такси (PvP)", callback_data="taxi_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_jobs_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К работам", callback_data="jobs_back")],
    ])


def taxi_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Начать смену", callback_data="taxi_start_shift")],
        [InlineKeyboardButton(text="🔙 К работам", callback_data="jobs_back")],
    ])


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


def jail_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍⚖️ Адвокат — $10000", callback_data="jail_lawyer")],
        [InlineKeyboardButton(text="⏳ Ждать", callback_data="jail_wait")],
    ])
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


def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])


def inventory_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="inv_back")],
    ])
