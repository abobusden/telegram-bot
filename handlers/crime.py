# ============================================
# КРИМИНАЛ + РОЗЫСК + УРОВЕНЬ КРИМИНАЛА
# ============================================

import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import (
    get_player, update_player, add_exp,
    add_crime_deal, get_crime_bonus,
)
from keyboards import crime_menu_kb, back_to_crime_kb, jail_kb


router = Router()

CRIMES = {
    "car":   {"name": "🚗 Угон машины",     "lvl": 1,  "min_pay": 500,   "max_pay": 2000,   "risk_win": 1, "cd": 600,  "exp": 20},
    "shop":  {"name": "🏪 Ограбить магазин","lvl": 3,  "min_pay": 1000,  "max_pay": 3000,   "risk_win": 2, "cd": 1200, "exp": 30},
    "drugs": {"name": "💊 Наркотики",       "lvl": 5,  "min_pay": 2000,  "max_pay": 5000,   "risk_win": 3, "cd": 1800, "exp": 50},
    "bank":  {"name": "🏦 Ограбить банк",   "lvl": 10, "min_pay": 10000, "max_pay": 20000,  "risk_win": 4, "cd": 3600, "exp": 100},
}

crime_cooldowns = {}


@router.message(F.text == "⚔️ Криминал")
async def crime_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    crime_level = player.get("crime_level", 1)
    crime_deals = player.get("crime_deals", 0)
    bonus = int((get_crime_bonus(crime_level) - 1) * 100)

    await message.answer(
        f"⚔️ <b>КРИМИНАЛ</b>\n\n"
        f"📍 Район: {player['district']}\n"
        f"🚨 Розыск: {'⭐' * player['wanted'] or 'чисто'}\n\n"
        f"🎯 Уровень криминала: <b>{crime_level}/5</b>\n"
        f"📊 Дел до уровня: {crime_deals}/5\n"
        f"💰 Бонус к доходу: <b>+{bonus}%</b>\n\n"
        f"Выбери дело:",
        reply_markup=crime_menu_kb(player["level"]),
    )


@router.callback_query(F.data == "crime_back")
async def crime_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    crime_level = player.get("crime_level", 1)
    crime_deals = player.get("crime_deals", 0)
    bonus = int((get_crime_bonus(crime_level) - 1) * 100)

    await callback.message.edit_text(
        f"⚔️ <b>КРИМИНАЛ</b>\n\n"
        f"📍 Район: {player['district']}\n"
        f"🚨 Розыск: {'⭐' * player['wanted'] or 'чисто'}\n\n"
        f"🎯 Уровень криминала: <b>{crime_level}/5</b>\n"
        f"📊 Дел до уровня: {crime_deals}/5\n"
        f"💰 Бонус: <b>+{bonus}%</b>",
        reply_markup=crime_menu_kb(player["level"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("crime_"))
async def do_crime(callback: CallbackQuery):
    crime_key = callback.data.replace("crime_", "")
    crime = CRIMES.get(crime_key)

    if not crime:
        await callback.answer("Дело не найдено")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["level"] < crime["lvl"]:
        await callback.answer(f"🔒 Нужен уровень {crime['lvl']}", show_alert=True)
        return

    user_cd = crime_cooldowns.get(callback.from_user.id, {})
    last = user_cd.get(crime_key)
    now = datetime.now()

    if last and now < last:
        left = int((last - now).total_seconds())
        mins, secs = divmod(left, 60)
        await callback.answer(f"⏳ Подожди {mins}:{secs:02d}", show_alert=True)
        return

    base_pay = random.randint(crime["min_pay"], crime["max_pay"])

    crime_level = player.get("crime_level", 1)
    bonus_mult = get_crime_bonus(crime_level)
    pay = int(base_pay * bonus_mult)

    # ×2 по выходным
    from handlers.events import get_multiplier
    mult = get_multiplier()
    pay = pay * mult

    new_wanted = min(5, player["wanted"] + crime["risk_win"])
    new_balance = player["balance"] + pay

    await update_player(
        callback.from_user.id,
        balance=new_balance,
        wanted=new_wanted,
    )

    exp_result = await add_exp(callback.from_user.id, crime["exp"])
    level_up_text = ""
    if exp_result and exp_result["levels_up"] > 0:
        level_up_text = f"\n🎉 <b>УРОВЕНЬ {exp_result['level']}!</b>"

    crime_result = await add_crime_deal(callback.from_user.id)
    crime_up_text = ""
    if crime_result and crime_result["leveled_up"]:
        crime_up_text = f"\n🔥 <b>УРОВЕНЬ КРИМИНАЛА {crime_result['crime_level']}!</b>"

    bonus_text = ""
    if crime_level > 1:
        bonus_text = f"\n💰 Бонус ур.{crime_level}: +{int((bonus_mult - 1) * 100)}%"
    if mult > 1:
        bonus_text += f"\n🔥 ×{mult} (выходной)"

    if callback.from_user.id not in crime_cooldowns:
        crime_cooldowns[callback.from_user.id] = {}
    crime_cooldowns[callback.from_user.id][crime_key] = now + timedelta(seconds=crime["cd"])

    await callback.message.edit_text(
        f"✅ <b>УСПЕХ!</b>\n\n"
        f"{crime['name']}\n"
        f"💰 +${pay}{bonus_text}\n"
        f"📊 +{crime['exp']} опыта\n"
        f"🚨 Розыск: {'⭐' * new_wanted}"
        f"{level_up_text}"
        f"{crime_up_text}\n\n"
        f"⏱ КД: {crime['cd'] // 60} мин",
        reply_markup=back_to_crime_kb(),
    )
    await callback.answer("Дело сделано!")

    player = await get_player(callback.from_user.id)
    if player["wanted"] >= 3:
        if random.random() < 0.6:
            jail_minutes = {3: 30, 4: 60, 5: 120}.get(player["wanted"], 30)
            jail_until = datetime.now() + timedelta(minutes=jail_minutes)

            jail_data[callback.from_user.id] = {
                "until": jail_until,
                "minutes": jail_minutes,
            }

            await callback.message.answer(
                f"🚔 <b>ТЕБЯ ПОЙМАЛИ!</b>\n\n"
                f"🚨 Розыск: {'⭐' * player['wanted']}\n"
                f"⏱ Срок: {jail_minutes} мин\n\n"
                f"Варианты:",
                reply_markup=jail_kb(),
            )
        else:
            await callback.message.answer(
                f"🍀 <b>ПОВЕЗЛО!</b>\n\n"
                f"Копы не нашли тебя.\n"
                f"🚨 Розыск: {'⭐' * player['wanted']}"
            )


jail_data = {}


def is_in_jail(telegram_id: int):
    data = jail_data.get(telegram_id)
    if not data:
        return None
    if datetime.now() >= data["until"]:
        jail_data.pop(telegram_id, None)
        return None
    return data
