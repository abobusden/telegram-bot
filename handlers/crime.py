# ============================================
# КРИМИНАЛ + РОЗЫСК
# ============================================

import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import get_player, update_player, add_exp
from keyboards import crime_menu_kb, back_to_crime_kb


router = Router()

# ============================================
# КРИМИНАЛЬНЫЕ ДЕЙСТВИЯ
# ============================================
CRIMES = {
    "car": {
        "name": "🚗 Угон машины",
        "lvl": 1,
        "min_pay": 500,
        "max_pay": 2000,
        "risk_win": 1,
        "risk_fail": 2,
        "cd": 600,
        "exp": 20,
    },
    "shop": {
        "name": "🏪 Ограбить магазин",
        "lvl": 3,
        "min_pay": 1000,
        "max_pay": 3000,
        "risk_win": 2,
        "risk_fail": 3,
        "cd": 1200,
        "exp": 30,
    },
    "drugs": {
        "name": "💊 Наркотики",
        "lvl": 5,
        "min_pay": 2000,
        "max_pay": 5000,
        "risk_win": 3,
        "risk_fail": 4,
        "cd": 1800,
        "exp": 50,
    },
    "bank": {
        "name": "🏦 Ограбить банк",
        "lvl": 10,
        "min_pay": 10000,
        "max_pay": 20000,
        "risk_win": 4,
        "risk_fail": 5,
        "cd": 3600,
        "exp": 100,
    },
}

crime_cooldowns = {}


# ============================================
# МЕНЮ КРИМИНАЛА
# ============================================
@router.message(F.text == "⚔️ Криминал")
async def crime_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    await message.answer(
        f"⚔️ <b>КРИМИНАЛ</b>\n\n"
        f"📍 Район: {player['district']}\n"
        f"🚨 Розыск: {'⭐' * player['wanted'] or 'чисто'}\n\n"
        f"Выбери дело:",
        reply_markup=crime_menu_kb(player["level"]),
    )


@router.callback_query(F.data == "crime_back")
async def crime_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    await callback.message.edit_text(
        f"⚔️ <b>КРИМИНАЛ</b>\n\n"
        f"📍 Район: {player['district']}\n"
        f"🚨 Розыск: {'⭐' * player['wanted'] or 'чисто'}",
        reply_markup=crime_menu_kb(player["level"]),
    )
    await callback.answer()


# ============================================
# ВЫПОЛНЕНИЕ ПРЕСТУПЛЕНИЯ
# ============================================
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

    # Шанс успеха
    chance = 60
    if player["weapon"]:
        weapon_bonus = {"pistol": 10, "smg": 15, "shotgun": 18, "rifle": 20}
        chance += weapon_bonus.get(player["weapon"], 0)
    if player["level"] <= 5:
        chance += 5
    elif player["level"] <= 10:
        chance += 10
    else:
        chance += 15
    chance -= player["wanted"] * 5
    chance = max(5, min(95, chance))

    success = random.random() * 100 < chance
    level_up_text = ""

    if success:
        pay = random.randint(crime["min_pay"], crime["max_pay"])
        new_wanted = min(5, player["wanted"] + crime["risk_win"])
        new_balance = player["balance"] + pay

        await update_player(
            callback.from_user.id,
            balance=new_balance,
            wanted=new_wanted,
        )

        # ✅ Опыт + автоуровень
        exp_result = await add_exp(callback.from_user.id, crime["exp"])
        if exp_result and exp_result["levels_up"] > 0:
            level_up_text = f"\n\n🎉 <b>УРОВЕНЬ {exp_result['level']}!</b>"

        result_text = (
            f"✅ <b>УСПЕХ!</b>\n\n"
            f"{crime['name']}\n"
            f"💰 +${pay}\n"
            f"📊 +{crime['exp']} опыта\n"
            f"🚨 Розыск: {'⭐' * new_wanted}"
        )
    else:
        new_wanted = min(5, player["wanted"] + crime["risk_fail"])

        await update_player(callback.from_user.id, wanted=new_wanted)

        result_text = (
            f"❌ <b>ПРОВАЛ!</b>\n\n"
            f"{crime['name']}\n"
            f"🚨 Розыск: {'⭐' * new_wanted}"
        )

    if callback.from_user.id not in crime_cooldowns:
        crime_cooldowns[callback.from_user.id] = {}
    crime_cooldowns[callback.from_user.id][crime_key] = now + timedelta(seconds=crime["cd"])

    await callback.message.edit_text(
        result_text + level_up_text + f"\n\n⏱ КД: {crime['cd'] // 60} мин",
        reply_markup=back_to_crime_kb(),
    )
    await callback.answer()

    # ============================================
    # ПРОВЕРКА НА ТЮРЬМУ (3+ ⭐)
    # ============================================
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
                f"Жди или зови адвоката",
            )
        else:
            await callback.message.answer(
                f"🍀 <b>ПОВЕЗЛО!</b>\n\n"
                f"Копы не нашли тебя.\n"
                f"🚨 Розыск: {'⭐' * player['wanted']}"
            )


# ============================================
# ХРАНИЛИЩЕ ТЮРЬМЫ
# ============================================
jail_data = {}


def is_in_jail(telegram_id: int):
    """Возвращает данные тюрьмы или None."""
    data = jail_data.get(telegram_id)
    if not data:
        return None
    if datetime.now() >= data["until"]:
        jail_data.pop(telegram_id, None)
        return None
    return data
