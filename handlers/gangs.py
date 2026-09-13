# ============================================
# БАНДЫ (вступить, выйти, сменить)
# ============================================

from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import (
    get_player, update_player,
    set_gang_cooldown, get_gang_cooldown,
)
from config import FACTIONS
from keyboards import gang_menu_kb, gang_choose_kb, back_to_gang_kb


router = Router()

GANG_CD_HOURS = 1  # КД 1 час


# ============================================
# МЕНЮ БАНДЫ
# ============================================
@router.message(F.text == "🚩 Банды")
async def gang_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    faction = player.get("faction")
    cd = await get_gang_cooldown(message.from_user.id)

    if faction:
        gang_data = FACTIONS.get(faction)
        await message.answer(
            f"🚩 <b>ТВОЯ БАНДА</b>\n\n"
            f"{gang_data['emoji']} {gang_data['name']}\n"
            f"📍 Район: {gang_data['district']}\n\n"
            f"Что хочешь?",
            reply_markup=gang_menu_kb(),
            parse_mode=ParseMode.HTML,
        )
    elif cd:
        left = int((cd - datetime.now()).total_seconds())
        hours, rem = divmod(left, 3600)
        mins, secs = divmod(rem, 60)
        await message.answer(
            f"🚩 <b>БАНДЫ</b>\n\n"
            f"Ты — одиночка\n\n"
            f"⏳ КД на вход в банду: <b>{hours:02d}:{mins:02d}:{secs:02d}</b>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.answer(
            f"🚩 <b>БАНДЫ</b>\n\n"
            f"Ты — одиночка\n\n"
            f"Выбери банду:",
            reply_markup=gang_choose_kb(),
            parse_mode=ParseMode.HTML,
        )


@router.callback_query(F.data == "gang_back")
async def gang_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    faction = player.get("faction")
    cd = await get_gang_cooldown(callback.from_user.id)

    if faction:
        gang_data = FACTIONS.get(faction)
        await callback.message.edit_text(
            f"🚩 <b>ТВОЯ БАНДА</b>\n\n"
            f"{gang_data['emoji']} {gang_data['name']}\n"
            f"📍 Район: {gang_data['district']}",
            reply_markup=gang_menu_kb(),
            parse_mode=ParseMode.HTML,
        )
    elif cd:
        left = int((cd - datetime.now()).total_seconds())
        hours, rem = divmod(left, 3600)
        mins, secs = divmod(rem, 60)
        await callback.message.edit_text(
            f"🚩 <b>БАНДЫ</b>\n\n"
            f"Ты — одиночка\n\n"
            f"⏳ КД: {hours:02d}:{mins:02d}:{secs:02d}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await callback.message.edit_text(
            f"🚩 <b>БАНДЫ</b>\n\n"
            f"Ты — одиночка\n\n"
            f"Выбери банду:",
            reply_markup=gang_choose_kb(),
            parse_mode=ParseMode.HTML,
        )
    await callback.answer()


# ============================================
# ВСТУПИТЬ В БАНДУ
# ============================================
@router.callback_query(F.data.startswith("join_gang_"))
async def join_gang(callback: CallbackQuery):
    gang_key = callback.data.replace("join_gang_", "")
    gang = FACTIONS.get(gang_key)

    if not gang:
        await callback.answer("Банда не найдена")
        return

    player = await get_player(callback.from_user.id)
    if player.get("faction"):
        await callback.answer("Ты уже в банде")
        return

    cd = await get_gang_cooldown(callback.from_user.id)
    if cd:
        left = int((cd - datetime.now()).total_seconds())
        hours, rem = divmod(left, 3600)
        mins, secs = divmod(rem, 60)
        await callback.answer(f"⏳ КД: {hours:02d}:{mins:02d}:{secs:02d}", show_alert=True)
        return

    await update_player(
        callback.from_user.id,
        faction=gang_key,
        district=gang["district"],
    )

    await callback.message.delete()
    await callback.message.answer(
        f"✅ <b>ТЫ В БАНДЕ!</b>\n\n"
        f"{gang['emoji']} {gang['name']}\n"
        f"📍 Район: {gang['district']}",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Вступил!")


# ============================================
# ВЫЙТИ ИЗ БАНДЫ
# ============================================
@router.callback_query(F.data == "leave_gang")
async def leave_gang(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player.get("faction"):
        await callback.answer("Ты не в банде")
        return

    cd_until = datetime.now() + timedelta(hours=GANG_CD_HOURS)
    await set_gang_cooldown(callback.from_user.id, cd_until)

    await update_player(callback.from_user.id, faction=None)

    await callback.message.delete()
    await callback.message.answer(
        f"🚪 <b>ТЫ ВЫШЕЛ ИЗ БАНДЫ</b>\n\n"
        f"Теперь ты одиночка.\n"
        f"⏳ КД на вход в новую банду: 1 час",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Вышел")


# ============================================
# СМЕНИТЬ БАНДУ
# ============================================
@router.callback_query(F.data == "change_gang")
async def change_gang(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player.get("faction"):
        await callback.answer("Ты не в банде")
        return

    cd_until = datetime.now() + timedelta(hours=GANG_CD_HOURS)
    await set_gang_cooldown(callback.from_user.id, cd_until)

    await update_player(callback.from_user.id, faction=None)

    await callback.message.delete()
    await callback.message.answer(
        f"🔄 <b>СМЕНА БАНДЫ</b>\n\n"
        f"Ты вышел из банды.\n"
        f"⏳ КД 1 час на вход в новую.",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Вышел, КД 1 час")
