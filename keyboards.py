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
