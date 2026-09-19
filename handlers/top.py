# ============================================
# ТОП ИГРОКОВ И БАНД
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import (
    get_player,
    get_top_by_balance, get_top_by_level,
    get_top_by_race, get_top_by_pvp,
    get_all_gangs_stats,
)
from keyboards import top_menu_kb, back_to_top_kb


router = Router()


# ============================================
# ГЛАВНОЕ МЕНЮ ТОПА
# ============================================
@router.message(F.text == "🏆 Топ")
async def top_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    await message.answer(
        f"🏆 <b>ТОПЫ</b>\n\n"
        f"Выбери категорию:",
        reply_markup=top_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "top_back")
async def top_back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        f"🏆 <b>ТОПЫ</b>\n\n"
        f"Выбери категорию:",
        reply_markup=top_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ТОП ПО ДЕНЬГАМ
# ============================================
@router.callback_query(F.data == "top_balance")
async def top_balance(callback: CallbackQuery):
    top = await get_top_by_balance(15)
    player = await get_player(callback.from_user.id)

    text = "💰 <b>ТОП ПО ДЕНЬГАМ</b>\n\n"

    medals = {0: "🥇", 1: "🥈", 2: "🥉"}

    for i, p in enumerate(top):
        medal = medals.get(i, f"{i+1}.")
        text += f"{medal} {p['nickname']} — ${p['balance']:,}\n"

    if player:
        text += f"\n📍 Ты: ${player['balance']:,}"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_top_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ТОП ПО УРОВНЮ
# ============================================
@router.callback_query(F.data == "top_level")
async def top_level(callback: CallbackQuery):
    top = await get_top_by_level(15)
    player = await get_player(callback.from_user.id)

    text = "⭐ <b>ТОП ПО УРОВНЮ</b>\n\n"

    medals = {0: "🥇", 1: "🥈", 2: "🥉"}

    for i, p in enumerate(top):
        medal = medals.get(i, f"{i+1}.")
        text += f"{medal} {p['nickname']} — Ур.{p['level']} ({p['exp']} exp)\n"

    if player:
        text += f"\n📍 Ты: Ур.{player['level']} ({player['exp']} exp)"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_top_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ТОП ПО БАНДАМ
# ============================================
@router.callback_query(F.data == "top_gangs")
async def top_gangs(callback: CallbackQuery):
    gangs = await get_all_gangs_stats()

    text = "🚩 <b>ТОП БАНД</b>\n\n"

    medals = {0: "🥇", 1: "🥈", 2: "🥉"}

    for i, g in enumerate(gangs):
        medal = medals.get(i, f"{i+1}.")
        text += (
            f"{medal} {g['emoji']} {g['name']} — {g['score']} очков\n"
            f"   👥 {g['members']} | ⭐ {g['total_level']} | ⚔️ {g['total_pvp']}\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=back_to_top_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ТОП ПО ГОНКАМ
# ============================================
@router.callback_query(F.data == "top_race")
async def top_race(callback: CallbackQuery):
    top = await get_top_by_race(15)
    player = await get_player(callback.from_user.id)

    text = "🏁 <b>ТОП ПО ГОНКАМ</b>\n\n"

    if not top:
        text += "Пока никто не побеждал в гонках.\n"
    else:
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}

        for i, p in enumerate(top):
            medal = medals.get(i, f"{i+1}.")
            text += f"{medal} {p['nickname']} — {p['race_wins']} побед\n"

    if player:
        text += f"\n📍 Ты: {player.get('race_wins', 0)} побед"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_top_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ТОП ПО PVP
# ============================================
@router.callback_query(F.data == "top_pvp")
async def top_pvp(callback: CallbackQuery):
    top = await get_top_by_pvp(15)
    player = await get_player(callback.from_user.id)

    text = "⚔️ <b>ТОП ПО PVP</b>\n\n"

    if not top:
        text += "Пока никто не побеждал в PvP.\n"
    else:
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}

        for i, p in enumerate(top):
            medal = medals.get(i, f"{i+1}.")
            text += f"{medal} {p['nickname']} — {p['pvp_wins']} побед\n"

    if player:
        text += f"\n📍 Ты: {player.get('pvp_wins', 0)} побед"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_top_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
