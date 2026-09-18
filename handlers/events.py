# ============================================
# ИВЕНТЫ (донат + бонус + ×2)
# ============================================

from datetime import datetime, timedelta

import pytz
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import (
    donate_menu_kb, daily_bonus_kb,
    support_author_kb, back_to_donate_kb,
)


router = Router()

MOSCOW_TZ = pytz.timezone("Europe/Moscow")

# Бонусы по дням
DAILY_BONUSES = {1: 300, 2: 600, 3: 900, 4: 1200, 5: 1500, 6: 2250, 7: 3000}

# Цены звёзд
STARS_PACKS = {
    5: 5000,
    10: 12000,
    25: 35000,
    50: 80000,
    100: 200000,
}

SUPPORT_USERNAME = "pegvi"


# ============================================
# ПРОВЕРКА ВЫХОДНОГО
# ============================================
def is_weekend() -> bool:
    now = datetime.now(MOSCOW_TZ)
    return now.weekday() >= 5


def get_multiplier() -> int:
    return 2 if is_weekend() else 1


# ============================================
# МЕНЮ ДОНАТА
# ============================================
@router.message(F.text == "💎 Донат")
async def donate_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    await message.answer(
        f"💎 <b>ДОНАТ</b>\n\n"
        f"Выбери действие:",
        reply_markup=donate_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "donate_back")
async def donate_back(callback: CallbackQuery):
    await callback.message.edit_text(
        f"💎 <b>ДОНАТ</b>\n\n"
        f"Выбери действие:",
        reply_markup=donate_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ЕЖЕДНЕВНЫЙ БОНУС
# ============================================
@router.callback_query(F.data == "daily_bonus")
async def daily_bonus(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Ошибка")
        return

    now = datetime.now(MOSCOW_TZ)
    last_bonus = player.get("last_bonus")
    streak = player.get("daily_streak", 0) or 0

    # Проверка: можно ли брать бонус?
    if last_bonus:
        try:
            last_dt = datetime.fromisoformat(last_bonus)
            if last_dt.tzinfo is None:
                last_dt = MOSCOW_TZ.localize(last_dt)
        except:
            last_dt = None

        if last_dt:
            elapsed = now - last_dt

            # Меньше 24 часов → нельзя
            if elapsed.total_seconds() < 24 * 3600:
                left = 24 * 3600 - int(elapsed.total_seconds())
                hours, rem = divmod(left, 3600)
                mins, secs = divmod(rem, 60)
                await callback.answer(
                    f"⏳ Следующий бонус через {hours:02d}:{mins:02d}:{secs:02d}",
                    show_alert=True,
                )
                return

            # Больше 48 часов → сброс
            if elapsed.total_seconds() > 48 * 3600:
                streak = 0
    else:
        streak = 0

    next_day = streak + 1
    if next_day > 7:
        next_day = 1

    bonus = DAILY_BONUSES[next_day]

    await callback.message.edit_text(
        f"🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС</b>\n\n"
        f"День: {next_day}/7\n\n"
        f"Твой бонус: ${bonus}\n\n"
        f"Забрать?",
        reply_markup=daily_bonus_kb(next_day),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("claim_bonus_"))
async def claim_bonus(callback: CallbackQuery):
    day = int(callback.data.replace("claim_bonus_", ""))
    player = await get_player(callback.from_user.id)

    bonus = DAILY_BONUSES.get(day, 300)
    now = datetime.now(MOSCOW_TZ)

    await update_player(
        callback.from_user.id,
        balance=player["balance"] + bonus,
        daily_streak=day,
        last_bonus=now.isoformat(),
    )

    await callback.message.edit_text(
        f"✅ <b>БОНУС ПОЛУЧЕН!</b>\n\n"
        f"💰 +${bonus}\n"
        f"📅 День: {day}/7\n\n"
        f"Возвращайся завтра за бонусом!",
        reply_markup=back_to_donate_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Бонус получен!")


# ============================================
# ПОДДЕРЖКА АВТОРА
# ============================================
@router.callback_query(F.data == "support_author")
async def support_author(callback: CallbackQuery):
    await callback.message.edit_text(
        f"⭐ <b>ПОДДЕРЖКА АВТОРА</b>\n\n"
        f"Спасибо, что играешь!\n"
        f"Выбери сумму поддержки:\n\n"
        f"За каждую покупку — игровые деньги в подарок 🎁",
        reply_markup=support_author_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_stars_"))
async def buy_stars(callback: CallbackQuery):
    stars = int(callback.data.replace("buy_stars_", ""))
    bonus = STARS_PACKS.get(stars, 0)

    await callback.message.answer_invoice(
        title=f"Поддержка автора — {stars}⭐",
        description=f"Спасибо! Взамен — ${bonus} в игре.",
        payload=f"stars_{stars}",
        currency="XTR",   # Telegram Stars
        prices=[LabeledPrice(label="Stars", amount=stars)],
    )
    await callback.answer()


# ============================================
# ОБРАБОТКА ПЛАТЕЖА
# ============================================
@router.pre_checkout_query()
async def pre_checkout(query):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload

    if payload.startswith("stars_"):
        stars = int(payload.replace("stars_", ""))
        bonus = STARS_PACKS.get(stars, 0)

        player = await get_player(message.from_user.id)
        if player:
            await update_player(
                message.from_user.id,
                balance=player["balance"] + bonus,
            )

            await message.answer(
                f"⭐ <b>СПАСИБО ЗА ПОДДЕРЖКУ!</b>\n\n"
                f"💎 Получено: {stars}⭐\n"
                f"💰 Бонус: +${bonus}\n\n"
                f"Ты лучший! 🎉",
                parse_mode=ParseMode.HTML,
              )
