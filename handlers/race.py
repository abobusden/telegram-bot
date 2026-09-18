# ============================================
# ГОНКИ (Трек)
# ============================================

import random
import asyncio
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from database import get_player, update_player, add_exp
from keyboards import (
    race_menu_kb, race_bet_cancel_kb,
    race_confirm_kb, race_result_kb, race_back_kb,
)
from states import Race


router = Router()

RACE_PHOTO = "https://i.ibb.co/M5x6W1Ty/Screenshot-20260918-141348.jpg"

BET_MIN = 100
BET_MAX = 10000

CAR_SPEEDS = {
    "sedan": 3, "truck": 3,
    "minivan": 4,
    "suv": 5, "chopper": 5,
    "moto": 6,
    "tuned": 8,
    "sportcar": 9, "sportbike": 9,
    "supercar": 10,
}

ENGINE_BONUS = {0: 0, 1: 0.5, 2: 1.0, 3: 1.5}


@router.message(F.text == "🏁 Трек")
async def race_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    car = player.get("car")
    car_name = car if car else "нет"

    await message.answer_photo(
        photo=RACE_PHOTO,
        caption=(
            f"🏁 <b>ТРЕК</b>\n\n"
            f"📍 Район: {player['district']}\n"
            f"🚗 Машина: {car_name}\n\n"
            f"Добро пожаловать на гонки!"
        ),
        reply_markup=race_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "race_back")
async def race_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    car = player.get("car")
    car_name = car if car else "нет"

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=RACE_PHOTO,
        caption=(
            f"🏁 <b>ТРЕК</b>\n\n"
            f"📍 Район: {player['district']}\n"
            f"🚗 Машина: {car_name}\n\n"
            f"Добро пожаловать на гонки!"
        ),
        reply_markup=race_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "race_fast")
async def race_fast(callback: CallbackQuery, state: FSMContext):
    player = await get_player(callback.from_user.id)

    if not player.get("car"):
        await callback.answer("🚗 Сначала купи машину!", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(
        f"🏁 <b>БЫСТРЫЙ ЗАЕЗД</b>\n\n"
        f"🚗 Машина: {player['car']}\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Введи ставку в чат.\n\n"
        f"Пример: <code>1000</code>\n\n"
        f"Минимум: ${BET_MIN}\n"
        f"Максимум: ${BET_MAX}",
        reply_markup=race_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Race.bet)
    await callback.answer()


@router.message(Race.bet)
async def process_bet(message: Message, state: FSMContext):
    try:
        bet = int(message.text.strip())
    except:
        await message.answer("❌ Введи число (например 1000):")
        return

    if bet < BET_MIN:
        await message.answer(f"❌ Минимум ${BET_MIN}. Попробуй ещё:")
        return

    if bet > BET_MAX:
        await message.answer(f"❌ Максимум ${BET_MAX}. Попробуй ещё:")
        return

    player = await get_player(message.from_user.id)

    if player["balance"] < bet:
        await message.answer(f"❌ Недостаточно (у тебя ${player['balance']}). Попробуй меньше:")
        return

    await state.clear()

    await message.answer(
        f"🏁 <b>ЗАЕЗД С NPC</b>\n\n"
        f"🚗 Машина: {player['car']}\n"
        f"💰 Ставка: ${bet}\n"
        f"🏆 Приз: ${bet * 2}\n\n"
        f"Начать заезд?",
        reply_markup=race_confirm_kb(bet),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("race_start_"))
async def race_start(callback: CallbackQuery):
    bet = int(callback.data.replace("race_start_", ""))
    player = await get_player(callback.from_user.id)

    if player["balance"] < bet:
        await callback.answer("💰 Не хватает денег", show_alert=True)
        return

    await update_player(callback.from_user.id, balance=player["balance"] - bet)

    car_speed = CAR_SPEEDS.get(player.get("car"), 3)
    engine_bonus = ENGINE_BONUS.get(player.get("engine_level", 0), 0)
    nitro_bonus = 1 if player.get("nitro", 0) else 0

    player_time = 20 - car_speed - engine_bonus - nitro_bonus + random.uniform(-2, 2)
    npc_speed = random.randint(3, 7)
    npc_time = 20 - npc_speed + random.uniform(-2, 2)

    await callback.message.delete()
    msg = await callback.message.answer(
        f"🏁 <b>ЗАЕЗД...</b>\n\n"
        f"🚗 Ты:   ░░░░░░░░░░ 0%\n"
        f"🤖 NPC:  ░░░░░░░░░░ 0%",
        parse_mode=ParseMode.HTML,
    )

    for i in range(1, 4):
        await asyncio.sleep(1)

        player_progress = min(100, int(i * 30 + random.randint(0, 10)))
        npc_progress = min(100, int(i * 25 + random.randint(0, 15)))

        p_bar = "█" * (player_progress // 10) + "░" * (10 - player_progress // 10)
        n_bar = "█" * (npc_progress // 10) + "░" * (10 - npc_progress // 10)

        try:
            await msg.edit_text(
                f"🏁 <b>ЗАЕЗД...</b>\n\n"
                f"🚗 Ты:   {p_bar} {player_progress}%\n"
                f"🤖 NPC:  {n_bar} {npc_progress}%",
                parse_mode=ParseMode.HTML,
            )
        except:
            pass

    await asyncio.sleep(1)

    player_time = round(player_time, 1)
    npc_time = round(npc_time, 1)

    from handlers.events import get_multiplier
    mult = get_multiplier()

    if player_time < npc_time:
        win = bet * 2
        win = win * mult

        await update_player(
            callback.from_user.id,
            balance=player["balance"] - bet + win,
        )
        await add_exp(callback.from_user.id, 30)

        bonus_text = f" ×{mult}" if mult > 1 else ""

        result_text = (
            f"╔══════════════════╗\n"
            f"║    🏁 ФИНИШ 🏁   ║\n"
            f"╠══════════════════╣\n"
            f"║ Ты:    {player_time} сек  ║\n"
            f"║ NPC:   {npc_time} сек  ║\n"
            f"╠══════════════════╣\n"
            f"║ 🏆 ТЫ ВЫИГРАЛ!   ║\n"
            f"║ 💰 +${win}{bonus_text}   ║\n"
            f"╚══════════════════╝"
        )
    elif npc_time < player_time:
        result_text = (
            f"╔══════════════════╗\n"
            f"║    🏁 ФИНИШ 🏁   ║\n"
            f"╠══════════════════╣\n"
            f"║ Ты:    {player_time} сек  ║\n"
            f"║ NPC:   {npc_time} сек  ║\n"
            f"╠══════════════════╣\n"
            f"║ ❌ ТЫ ПРОИГРАЛ   ║\n"
            f"║ 💰 -${bet}        ║\n"
            f"╚══════════════════╝"
        )
    else:
        await update_player(callback.from_user.id, balance=player["balance"])
        result_text = (
            f"╔══════════════════╗\
