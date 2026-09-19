# ============================================
# РЕГИСТРАЦИЯ + РЕФЕРАЛЬНАЯ СИСТЕМА
# ============================================

import re
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from config import FACTIONS, DEFAULT_DISTRICT
from database import (
    get_player, nickname_exists, create_player, update_player,
)
from keyboards import (
    start_kb, gender_kb, faction_kb, to_city_kb,
    main_menu_kb,
)
from states import Reg


router = Router()


# ============================================
# /start — с фото + обработка реферальной ссылки
# ============================================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    player = await get_player(message.from_user.id)

    # Обработка реферальной ссылки
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            await state.update_data(referred_by=referrer_id)
        except:
            pass

    if player:
        need_exp = player["level"] * 100
        await message.answer(
            f"👋 С возвращением, <b>{player['nickname']}</b>!\n\n"
            f"💰 ${player['balance']} | ❤️ {player['hp']}/100\n"
            f"⭐ Ур.{player['level']} | 📊 {player['exp']}/{need_exp}",
            reply_markup=to_city_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    await message.answer_photo(
        photo="https://i.ibb.co/Ps9HY2wR/IMG-20260919-102054-132.jpg",
        caption=(
            "🌴 <b>ДОБРО ПОЖАЛОВАТЬ В LOS SANTOS</b> 🌴\n\n"
            "Самолёт приземлился. Ты вышел.\n"
            "В кармане — $500. В голове — план.\n"
            "Город не ждёт. Город решает.\n\n"
            "Кем ты станешь?"
        ),
        reply_markup=start_kb(),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# Создать персонажа
# ============================================
@router.callback_query(F.data == "reg_start")
async def reg_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption(
        caption=(
            "📝 <b>Введи уличное имя</b>\n\n"
            "• 3–16 символов\n"
            "• Буквы, цифры, _\n"
            "• Без пробелов\n\n"
            "Пример: <code>BigSmoke_88</code>"
        ),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Reg.nickname)
    await callback.answer()


# ============================================
# Ввод ника
# ============================================
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
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Reg.gender)


# ============================================
# Выбор пола
# ============================================
@router.callback_query(Reg.gender, F.data.startswith("gender_"))
async def reg_gender(callback: CallbackQuery, state: FSMContext):
    gender = "male" if callback.data == "gender_male" else "female"
    await state.update_data(gender=gender)

    await callback.message.edit_text(
        "🚩 <b>Вступить в банду?</b>\n\n"
        "Можно сейчас, можно потом.\n"
        "Всегда сможешь выйти или сменить.",
        reply_markup=faction_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Reg.faction)
    await callback.answer()


# ============================================
# Выбор банды + реферальный бонус
# ============================================
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

    referred_by = data.get("referred_by")

    await create_player(
        callback.from_user.id,
        data["nickname"],
        data["gender"],
        faction,
        district,
        referred_by=referred_by,
    )

    # Реферальный бонус
    if referred_by:
        from handlers.referral import REFERRAL_BONUS_ME, REFERRAL_BONUS_FRIEND

        referrer = await get_player(referred_by)
        if referrer:
            await update_player(
                referred_by,
                balance=referrer["balance"] + REFERRAL_BONUS_ME,
                referral_count=(referrer.get("referral_count", 0) or 0) + 1,
            )

            new_player = await get_player(callback.from_user.id)
            await update_player(
                callback.from_user.id,
                balance=new_player["balance"] + REFERRAL_BONUS_FRIEND,
            )

            try:
                await callback.bot.send_message(
                    referred_by,
                    f"🎁 <b>НОВЫЙ РЕФЕРАЛ!</b>\n\n"
                    f"👤 {data['nickname']} зарегистрировался по твоей ссылке.\n"
                    f"💰 +${REFERRAL_BONUS_ME}",
                    parse_mode=ParseMode.HTML,
                )
            except:
                pass

    player = await get_player(callback.from_user.id)
    gender_text = "👨" if player["gender"] == "male" else "👩"
    need_exp = player["level"] * 100

    await callback.message.edit_text(
        f"✅ <b>ПЕРСОНАЖ СОЗДАН</b>\n\n"
        f"👤 {player['nickname']} | {gender_text}\n"
        f"🚩 Банда: {faction_text}\n"
        f"📍 Район: {player['district']}\n"
        f"💰 ${player['balance']} | ❤️ {player['hp']}\n"
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/{need_exp}",
        reply_markup=to_city_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.clear()
    await callback.answer("Персонаж создан!")


# ============================================
# В город
# ============================================
@router.callback_query(F.data == "to_city")
async def to_city(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    need_exp = player["level"] * 100

    await callback.message.delete()
    await callback.message.answer(
        f"👤 {player['nickname']} | 🚩 {player['district']}\n"
        f"💰 ${player['balance']} | ❤️ {player['hp']}/100 | 🚨 {player['wanted']}\n"
        f"⭐ Ур.{player['level']} | 📊 {player['exp']}/{need_exp}\n\n"
        f"Выбери действие:",
        reply_markup=main_menu_kb(page=1),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
