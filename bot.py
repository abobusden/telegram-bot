# ============================================
# GTA CRIME BOT — ВСЁ В ОДНОМ ФАЙЛЕ
# ============================================

import asyncio
import logging
import re

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)


# ============================================
# ⚙️ КОНФИГ
# ============================================
# ⚠️ ВСТАВЬ СЮДА СВОЙ ТОКЕН ОТ @BotFather
BOT_TOKEN = "СЮДА_ВСТАВЬ_ТОКЕН"

SUPPORT_USERNAME = "pegvi"
DB_PATH = "gta_bot.db"

START_BALANCE = 500
START_HP = 100
START_LEVEL = 1
START_EXP = 0


# ============================================
# 🚩 БАНДЫ
# ============================================
FACTIONS = {
    "grove":   {"name": "Grove Street Families", "emoji": "🟢", "district": "Ganton"},
    "ballas":  {"name": "Ballas",                 "emoji": "🟣", "district": "Idlewood"},
    "vagos":   {"name": "Los Vagos",              "emoji": "🔵", "district": "East Los Santos"},
    "aztecas": {"name": "Ацтеки",                 "emoji": "⚪", "district": "El Corona"},
}
DEFAULT_DISTRICT = "Ganton"


# ============================================
# 🗄 БАЗА ДАННЫХ
# ============================================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                nickname TEXT UNIQUE NOT NULL,
                gender TEXT NOT NULL,
                faction TEXT,
                district TEXT NOT NULL,
                balance INTEGER DEFAULT 500,
                hp INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                wanted INTEGER DEFAULT 0,
                weapon TEXT,
                car TEXT,
                home TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def get_player(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM players WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def nickname_exists(nickname: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM players WHERE LOWER(nickname) = LOWER(?)", (nickname,)
        ) as cur:
            return await cur.fetchone() is not None


async def create_player(telegram_id, nickname, gender, faction, district):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO players
                (telegram_id, nickname, gender, faction, district,
                 balance, hp, level, exp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_id, nickname, gender, faction, district,
            START_BALANCE, START_HP, START_LEVEL, START_EXP,
        ))
        await db.commit()


# ============================================
# 🎛 КЛАВИАТУРЫ
# ============================================
def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="⚔️ Криминал"), KeyboardButton(text="🛒 Магазин")],
            [KeyboardButton(text="🏠 Жильё"), KeyboardButton(text="🚗 Транспорт")],
            [KeyboardButton(text="🗺 Карта"), KeyboardButton(text="🏢 Здания")],
            [KeyboardButton(text="🏆 Топ")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие...",
    )


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 Создать персонажа", callback_data="reg_start")],
    ])


def gender_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male"),
            InlineKeyboardButton(text="👩 Женский", callback_data="gender_female"),
        ],
    ])


def faction_kb() -> InlineKeyboardMarkup:
    buttons = []
    for key, data in FACTIONS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{data['emoji']} {data['name']} — {data['district']}",
                callback_data=f"faction_{key}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data="faction_skip")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def to_city_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗺 В город", callback_data="to_city")],
    ])


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])


# ============================================
# 🧠 FSM
# ============================================
class Reg(StatesGroup):
    nickname = State()
    gender = State()
    faction = State()


# ============================================
# 🚀 ХЕНДЛЕРЫ
# ============================================
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    player = await get_player(message.from_user.id)

    if player:
        await message.answer(
            f"👋 С возвращением, <b>{player['nickname']}</b>!\n\n"
            f"💰 ${player['balance']} | ❤️ {player['hp']}/100\n"
            f"⭐ Ур.{player['level']} | 📊 {player['exp']}/100",
            reply_markup=to_city_kb(),
        )
        return

    await message.answer(
        "🌴 <b>LOS SANTOS</b> 🌴\n\n"
        "Ты сошёл с трапа самолёта.\n"
        "В кармане — $500. В голове — план.\n\n"
        "Кем ты станешь в этом городе?",
        reply_markup=start_kb(),
    )


@router.callback_query(F.data == "reg_start")
async def reg_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 <b>Введи уличное имя</b>\n\n"
        "• 3–16 символов\n"
        "• Буквы, цифры, _\n"
        "• Без пробелов\n\n"
        "Пример: <code>BigSmoke_88</code>",
    )
    await state.set_state(Reg.nickname)
    await callback.answer()


@router.message(Reg.nickname)
async def reg_nickname(message: Message, state: FSMContext):
    nick = message.text.strip()

    if not (3 <= len(nick) <= 16):
        await message.answer("❌ Ник должен быть 3–16 символов. Попробуй ещё:")
        return
    if not re.match(r"^[A-Za-zА-Яа-я0-9_]+$", nick):
        await message.answer("❌ Только буквы, цифры и _. Без пробелов. Попробуй ещё:")
        return
    if await nickname_exists(nick):
        await message.answer("❌ Этот ник уже занят. Попробуй другой:")
        return

    await state.update_data(nickname=nick)
    await message.answer(
        f"✅ Ник: <b>{nick}</b>\n\n👤 Выбери пол:",
        reply_markup=gender_kb(),
    )
    await state.set_state(Reg.gender)


@router.callback_query(Reg.gender, F.data.startswith("gender_"))
async def reg_gender(callback: CallbackQuery, state: FSMContext):
    gender = "male" if callback.data == "gender_male" else "female"
    await state.update_data(gender=gender)

    await callback.message.edit_text(
        "🚩 <b>Вступить в банду?</b>\n\n"
        "Можно сейчас, можно потом.\n"
        "Всегда сможешь выйти или сменить.",
        reply_markup=faction_kb(),
    )
    await state.set_state(Reg.faction)
    await callback.answer()


@router.callback_query(Reg.faction, F.data.startswith("faction_"))
async def reg_faction(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.replace("faction_", "")
    data = await state.get_data()

    if choice == "skip":
        faction = None
        district = DEFAULT_DISTRICT
        faction_text = "нет (одиночка)"
    else:
        faction = choice
        district = FACTIONS[choice]["district"]
        faction_text = f"{FACTIONS[choice]['emoji']} {FACTIONS[choice]['name']}"

    await create_player(
        telegram_id=callback.from_user.id,
        nickname=data["nickname"],
        gender=data["gender"],
        faction=faction,
        district=district,
    )

    player = await get_player(callback.from_user.id)
    gender_text = "👨" if player["gender"] == "male" else "👩"

    await callback.message.edit_text(
        f"✅ <b>ПЕРСОНАЖ СОЗДАН</b>\n\n"
        f"👤 {player['nickname']} | {gender_text}\n"
        f"🚩 Банда: {faction_text}\n"
        f"📍 Район: {player['district']}\n"
        f"💰 ${player['balance']} | ❤️ {player['hp']}\n"
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/100",
        reply_markup=to_city_kb(),
    )
    await state.clear()
    await callback.answer("Персонаж создан!")


@router.callback_query(F.data == "to_city")
async def to_city(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer(
        f"👤 {player['nickname']} | 🚩 {player['district']}\n"
        f"💰 ${player['balance']} | ❤️ {player['hp']}/100 | 🚨 {player['wanted']}\n"
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/100\n\n"
        f"Выбери действие:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# ============================================
# 👤 ПРОФИЛЬ
# ============================================
@router.message(F.text == "👤 Профиль")
async def profile(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    gender = "👨" if player["gender"] == "male" else "👩"
    faction = player["faction"] or "нет"
    home = player["home"] or "нет"
    weapon = player["weapon"] or "нет"
    car = player["car"] or "нет"

    await message.answer(
        f"👤 <b>{player['nickname']}</b> | {gender}\n"
        f"🚩 Банда: {faction}\n"
        f"📍 Район: {player['district']}\n"
        f"🏠 Жильё: {home}\n"
        f"🚗 Машина: {car}\n"
        f"🔫 Оружие: {weapon}\n"
        f"🚨 Розыск: {player['wanted']}\n\n"
        f"💰 ${player['balance']} | ❤️ {player['hp']}/100\n"
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/100",
        reply_markup=profile_kb(),
    )


# ============================================
# 🚀 ЗАПУСК
# ============================================
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    print("🚀 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Бот остановлен")
