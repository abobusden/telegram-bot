# ============================================
# PVP (дуэли с игроками + NPC)
# ============================================

import random
import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import (
    get_player, update_player, add_exp,
    add_pvp_win, add_pvp_loss,
    get_online_players,
)
from keyboards import (
    pvp_menu_kb, pvp_opponents_kb, pvp_bet_kb,
    pvp_challenge_kb, pvp_back_kb,
)


router = Router()

# Хранилище вызовов
active_challenges = {}


# ============================================
# МЕНЮ PVP
# ============================================
@router.message(F.text == "⚔️ PvP")
async def pvp_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    wins = player.get("pvp_wins", 0)
    losses = player.get("pvp_losses", 0)
    total = wins + losses
    winrate = int(wins / total * 100) if total > 0 else 0

    await message.answer(
        f"⚔️ <b>PVP</b>\n\n"
        f"🏆 Побед: {wins}\n"
        f"❌ Поражений: {losses}\n"
        f"📊 Винрейт: {winrate}%\n\n"
        f"💰 Твой баланс: ${player['balance']}",
        reply_markup=pvp_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "pvp_back")
async def pvp_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    wins = player.get("pvp_wins", 0)
    losses = player.get("pvp_losses", 0)
    total = wins + losses
    winrate = int(wins / total * 100) if total > 0 else 0

    await callback.message.delete()
    await callback.message.answer(
        f"⚔️ <b>PVP</b>\n\n"
        f"🏆 Побед: {wins}\n"
        f"❌ Поражений: {losses}\n"
        f"📊 Винрейт: {winrate}%\n\n"
        f"💰 Твой баланс: ${player['balance']}",
        reply_markup=pvp_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ПОИСК СОПЕРНИКА
# ============================================
@router.callback_query(F.data == "pvp_search")
async def pvp_search(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    msg = await callback.message.answer(
        f"⚔️ <b>ПОИСК СОПЕРНИКА...</b>\n\n"
        f"⏳ Ищем игрока онлайн...",
        reply_markup=pvp_back_kb(),
        parse_mode=ParseMode.HTML,
    )

    # Ждём 3 секунды
    await asyncio.sleep(3)

    # Ищем игроков онлайн
    opponents = await get_online_players(callback.from_user.id, limit=5)

    if opponents:
        await msg.edit_text(
            f"⚔️ <b>СОПЕРНИКИ НАЙДЕНЫ</b>\n\n"
            f"Выбери, с кем драться:",
            reply_markup=pvp_opponents_kb(opponents),
            parse_mode=ParseMode.HTML,
        )
    else:
        # NPC
        await msg.edit_text(
            f"⚔️ <b>ИГРОКОВ НЕТ</b>\n\n"
            f"⏳ Ищем NPC...",
            reply_markup=pvp_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        await asyncio.sleep(2)

        await msg.edit_text(
            f"⚔️ <b>NPC НАЙДЕН</b>\n\n"
            f"👤 Соперник: NPC\n"
            f"⭐ Уровень: ~{player['level']}\n\n"
            f"Выбери ставку:",
            reply_markup=pvp_bet_kb(),
            parse_mode=ParseMode.HTML,
        )
    await callback.answer()


# ============================================
# ВЫБОР СТАВКИ
# ============================================
@router.callback_query(F.data.startswith("pvp_bet_"))
async def pvp_bet(callback: CallbackQuery):
    bet = int(callback.data.replace("pvp_bet_", ""))
    player = await get_player(callback.from_user.id)

    if player["balance"] < bet:
        await callback.answer(f"💰 Нужно ${bet}", show_alert=True)
        return

    active_challenges[callback.from_user.id] = {
        "target_id": None,
        "bet": bet,
        "until": datetime.now() + timedelta(seconds=60),
    }

    await callback.message.edit_text(
        f"⚔️ <b>СТАВКА: ${bet}</b>\n\n"
        f"👤 Соперник: NPC\n"
        f"💰 Твоя ставка: ${bet}\n\n"
        f"Начать бой?",
        reply_markup=pvp_challenge_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# БОЙ С NPC
# ============================================
@router.callback_query(F.data == "pvp_fight")
async def pvp_fight(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    challenge = active_challenges.get(callback.from_user.id)

    if not challenge:
        await callback.answer("Вызов истёк")
        return

    bet = challenge["bet"]

    if player["balance"] < bet:
        await callback.answer("💰 Не хватает денег", show_alert=True)
        return

    result = simulate_fight(player)

    if result["winner"] == "player":
        new_balance = player["balance"] + bet
        await update_player(callback.from_user.id, balance=new_balance, hp=20)
        await add_pvp_win(callback.from_user.id)

        await callback.message.edit_text(
            f"⚔️ <b>БОЙ ЗАВЕРШЁН</b>\n\n"
            f"🏆 <b>ПОБЕДА!</b>\n\n"
            f"💰 +${bet}\n"
            f"❤️ HP: 20/100\n"
            f"📊 +30 опыта",
            reply_markup=pvp_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    elif result["winner"] == "npc":
        new_balance = max(0, player["balance"] - bet)
        await update_player(callback.from_user.id, balance=new_balance, hp=20)
        await add_pvp_loss(callback.from_user.id)

        await callback.message.edit_text(
            f"⚔️ <b>БОЙ ЗАВЕРШЁН</b>\n\n"
            f"❌ <b>ПОРАЖЕНИЕ</b>\n\n"
            f"💰 -${bet}\n"
            f"❤️ HP: 20/100",
            reply_markup=pvp_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    else:
        await update_player(callback.from_user.id, hp=20)
        await callback.message.edit_text(
            f"⚔️ <b>НИЧЬЯ</b>\n\n"
            f"💰 Ставка возвращена\n"
            f"❤️ HP: 20/100",
            reply_markup=pvp_back_kb(),
            parse_mode=ParseMode.HTML,
        )

    await add_exp(callback.from_user.id, 30)
    active_challenges.pop(callback.from_user.id, None)
    await callback.answer()


# ============================================
# СИМУЛЯЦИЯ БОЯ
# ============================================
def simulate_fight(player):
    player_hp = 100
    npc_hp = 100

    player_damage_base = 20
    if player["weapon"]:
        weapon_bonus = {"pistol": 10, "smg": 15, "shotgun": 18, "rifle": 20}
        player_damage_base += weapon_bonus.get(player["weapon"], 0)

    npc_damage_base = 20 + random.randint(0, 15)

    turn = 0
    max_turns = 20

    while player_hp > 0 and npc_hp > 0 and turn < max_turns:
        turn += 1

        dmg = player_damage_base + random.randint(1, 20)
        npc_hp -= dmg

        if npc_hp <= 0:
            return {"winner": "player"}

        dmg = npc_damage_base + random.randint(1, 20)
        player_hp -= dmg

    if player_hp <= 0 and npc_hp <= 0:
        return {"winner": "draw"}
    elif player_hp <= 0:
        return {"winner": "npc"}
    elif npc_hp <= 0:
        return {"winner": "player"}
    else:
        return {"winner": "draw"}
