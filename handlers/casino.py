# ============================================
# КАЗИНО (кубик + слоты)
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import (
    casino_menu_kb, casino_back_kb,
    casino_bet_cancel_kb,
)
from states import Casino


router = Router()

BET_MIN = 100
BET_MAX = 10000

DICE_EMOJI = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}


# ============================================
# МЕНЮ КАЗИНО
# ============================================
@router.message(F.text == "🎰 Казино")
async def casino_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    await message.answer(
        f"🎰 <b>КАЗИНО</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Выбери игру:",
        reply_markup=casino_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "casino_back")
async def casino_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🎰 <b>КАЗИНО</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Выбери игру:",
        reply_markup=casino_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# КУБИК — ставка
# ============================================
@router.callback_query(F.data == "casino_dice")
async def casino_dice(callback: CallbackQuery, state: FSMContext):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🎲 <b>КУБИК</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Введи ставку в чат.\n\n"
        f"Пример: <code>1000</code>\n\n"
        f"Минимум: ${BET_MIN}\n"
        f"Максимум: ${BET_MAX}",
        reply_markup=casino_bet_cancel_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Casino.dice_bet)
    await callback.answer()


@router.message(Casino.dice_bet)
async def process_dice_bet(message: Message, state: FSMContext):
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

    # Списываем ставку
    await update_player(message.from_user.id, balance=player["balance"] - bet)

    # Отправляем 2 кубика
    dice_msg1 = await message.answer_dice(emoji="🎲")
    dice_msg2 = await message.answer_dice(emoji="🎲")

    # Ждём анимацию
    import asyncio
    await asyncio.sleep(4)

    player_dice = dice_msg1.dice.value
    casino_dice = dice_msg2.dice.value

    player_emoji = DICE_EMOJI[player_dice]
    casino_emoji = DICE_EMOJI[casino_dice]

    # Результат
    if player_dice > casino_dice:
        win = bet * 2
        new_balance = player["balance"] - bet + win
        await update_player(message.from_user.id, balance=new_balance)

        result = (
            f"╔══════════════════╗\n"
            f"║   🎲 БРОСОК 🎲   ║\n"
            f"╠══════════════════╣\n"
            f"║ Ты:     {player_emoji}      ║\n"
            f"║ Казино: {casino_emoji}      ║\n"
            f"╠══════════════════╣\n"
            f"║ 🏆 ТЫ ВЫИГРАЛ!  ║\n"
            f"║ 💰 +${bet}        ║\n"
            f"╚══════════════════╝"
        )
    elif casino_dice > player_dice:
        result = (
            f"╔══════════════════╗\n"
            f"║   🎲 БРОСОК 🎲   ║\n"
            f"╠══════════════════╣\n"
            f"║ Ты:     {player_emoji}      ║\n"
            f"║ Казино: {casino_emoji}      ║\n"
            f"╠══════════════════╣\n"
            f"║ ❌ ПРОИГРЫШ      ║\n"
            f"║ 💰 -${bet}        ║\n"
            f"╚══════════════════╝"
        )
    else:
        # Ничья — возврат
        await update_player(message.from_user.id, balance=player["balance"])
        result = (
            f"╔══════════════════╗\n"
            f"║   🎲 БРОСОК 🎲   ║\n"
            f"╠══════════════════╣\n"
            f"║ Ты:     {player_emoji}      ║\n"
            f"║ Казино: {casino_emoji}      ║\n"
            f"╠══════════════════╣\n"
            f"║ 🤝 НИЧЬЯ         ║\n"
            f"║ 💰 Ставка возвращена ║\n"
            f"╚══════════════════╝"
        )

    await message.answer(result, reply_markup=casino_back_kb())


# ============================================
# СЛОТЫ — ставка
# ============================================
@router.callback_query(F.data == "casino_slots")
async def casino_slots(callback: CallbackQuery, state: FSMContext):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"🎰 <b>СЛОТЫ</b>\n\n"
        f"💰 Баланс: ${player['balance']}\n\n"
        f"Введи ставку в чат.\n\n"
        f"Пример: <code>1000</code>\n\n"
        f"Минимум: ${BET_MIN}\n"
        f"Максимум: ${BET_MAX}",
        reply_markup=casino_bet_cancel_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Casino.slots_bet)
    await callback.answer()


@router.message(Casino.slots_bet)
async def process_slots_bet(message: Message, state: FSMContext):
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

    # Списываем ставку
    await update_player(message.from_user.id, balance=player["balance"] - bet)

    # Отправляем слоты
    slots_msg = await message.answer_dice(emoji="🎰")

    import asyncio
    await asyncio.sleep(3)

    values = slots_msg.dice.value

    # Результат — Telegram API: value 1-64
    # 1-43 = проигрыш
    # 44-63 = выигрыш ×2
    # 64 = джекпот (BAR BAR BAR)

    if values == 64:
        # Джекпот
        win = bet * 10
        new_balance = player["balance"] - bet + win
        await update_player(message.from_user.id, balance=new_balance)

        result = (
            f"╔══════════════════╗\n"
            f"║   🎰 СЛОТЫ 🎰    ║\n"
            f"╠══════════════════╣\n"
            f"║   🎰 🎰 🎰       ║\n"
            f"╠══════════════════╣\n"
            f"║ 💎 ДЖЕКПОТ ×10!  ║\n"
            f"║ 💰 +${win}      ║\n"
            f"╚══════════════════╝"
        )
    elif values >= 44:
        # Выигрыш ×2
        win = bet * 2
        new_balance = player["balance"] - bet + win
        await update_player(message.from_user.id, balance=new_balance)

        result = (
            f"╔══════════════════╗\n"
            f"║   🎰 СЛОТЫ 🎰    ║\n"
            f"╠══════════════════╣\n"
            f"║   🍒 🍒 🍒       ║\n"
            f"╠══════════════════╣\n"
            f"║ 🏆 ВЫИГРЫШ ×2!   ║\n"
            f"║ 💰 +${bet}        ║\n"
            f"╚══════════════════╝"
        )
    else:
        # Проигрыш
        result = (
            f"╔══════════════════╗\n"
            f"║   🎰 СЛОТЫ 🎰    ║\n"
            f"╠══════════════════╣\n"
            f"║   🍒 🍋 🍇       ║\n"
            f"╠══════════════════╣\n"
            f"║ ❌ ПРОИГРЫШ      ║\n"
            f"║ 💰 -${bet}        ║\n"
            f"╚══════════════════╝"
        )

    await message.answer(result, reply_markup=casino_back_kb())
