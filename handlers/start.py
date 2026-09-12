import re
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import FACTIONS, DEFAULT_DISTRICT
from database import get_player, nickname_exists, create_player
from keyboards import start_kb, gender_kb, faction_kb, to_city_kb, main_menu_kb, profile_kb
from states import Reg


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
        "• 3–16 символов\n• Буквы, цифры, _\n• Без пробелов\n\n"
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
    await message.answer(f"✅ Ник: <b>{nick}</b>\n\n👤 Выбери пол:", reply_markup=gender_kb())
    await state.set_state(Reg.gender)


@router.callback_query(Reg.gender, F.data.startswith("gender_"))
async def reg_gender(callback: CallbackQuery, state: FSMContext):
    gender = "male" if callback.data == "gender_male" else "female"
    await state.update_data(gender=gender)
    await callback.message.edit_text(
        "🚩 <b>Вступить в банду?</b>\n\n"
        "Можно сейчас, можно потом.\nВсегда сможешь выйти или сменить.",
        reply_markup=faction_kb(),
    )
    await state.set_state(Reg.faction)
    await callback.answer()


@router.callback_query(Reg.faction, F.data.startswith("faction_"))
async def reg_faction(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.replace("faction_", "")
    data = await state.get_data()
    if choice == "skip":
        faction, district, faction_text = None, DEFAULT_DISTRICT, "нет (одиночка)"
    else:
        faction = choice
        district = FACTIONS[choice]["district"]
        faction_text = f"{FACTIONS[choice]['emoji']} {FACTIONS[choice]['name']}"
    await create_player(callback.from_user.id, data["nickname"], data["gender"], faction, district)
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
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/100\n\nВыбери действие:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.message(F.text == "👤 Профиль")
async def profile(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return
    gender = "👨" if player["gender"] == "male" else "👩"
    await message.answer(
        f"👤 <b>{player['nickname']}</b> | {gender}\n"
        f"🚩 Банда: {player['faction'] or 'нет'}\n"
        f"📍 Район: {player['district']}\n"
        f"🏠 Жильё: {player['home'] or 'нет'}\n"
        f"🚗 Машина: {player['car'] or 'нет'}\n"
        f"🔫 Оружие: {player['weapon'] or 'нет'}\n"
        f"🚨 Розыск: {player['wanted']}\n\n"
        f"💰 ${player['balance']} | ❤️ {player['hp']}/100\n"
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/100",
        reply_markup=profile_kb(),
    )
