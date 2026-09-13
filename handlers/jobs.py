# ============================================
# РАБОТЫ (NPC + ТАКСИ PvP)
# ============================================

import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import get_player, update_player, add_exp
from keyboards import (
    jobs_menu_kb, back_to_jobs_kb,
    taxi_menu_kb, taxi_orders_kb,
)


router = Router()

# ============================================
# NPC-РАБОТЫ
# ============================================
JOBS = {
    "pizza":   {"name": "🍔 Пицца",   "lvl": 1,  "pay": 100, "cd": 180,  "fail_pay": 50,  "exp": 10},
    "courier": {"name": "📦 Курьер",  "lvl": 1,  "pay": 150, "cd": 300,  "fail_pay": 50,  "exp": 15},
    "loader":  {"name": "🏗 Грузчик", "lvl": 5,  "pay": 300, "cd": 1200, "fail_pay": 100, "exp": 25},
    "trucker": {"name": "🚚 Дальнобой","lvl": 10,"pay": 800, "cd": 3600, "fail_pay": 200, "exp": 50},
}

job_cooldowns = {}
taxi_state = {}
taxi_hourly = {}


# ============================================
# МЕНЮ РАБОТ
# ============================================
@router.message(F.text == "💼 Работа")
async def jobs_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    await message.answer(
        "💼 <b>РАБОТЫ</b>\n\n"
        "Выбери подработку:\n"
        "• NPC-работы — нажал и получил\n"
        "• 🚕 Такси — вози игроков (PvP)",
        reply_markup=jobs_menu_kb(player["level"]),
    )


@router.callback_query(F.data == "jobs_back")
async def jobs_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    await callback.message.edit_text(
        "💼 <b>РАБОТЫ</b>\n\nВыбери подработку:",
        reply_markup=jobs_menu_kb(player["level"]),
    )
    await callback.answer()


# ============================================
# NPC-РАБОТА
# ============================================
@router.callback_query(F.data.startswith("job_"))
async def do_job(callback: CallbackQuery):
    job_key = callback.data.replace("job_", "")
    job = JOBS.get(job_key)

    if not job:
        await callback.answer("Работа не найдена")
        return

    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["level"] < job["lvl"]:
        await callback.answer(f"🔒 Нужен уровень {job['lvl']}", show_alert=True)
        return

    user_cd = job_cooldowns.get(callback.from_user.id, {})
    last = user_cd.get(job_key)
    now = datetime.now()

    if last and now < last:
        left = int((last - now).total_seconds())
        mins, secs = divmod(left, 60)
        await callback.answer(f"⏳ Подожди {mins}:{secs:02d}", show_alert=True)
        return

    success = random.random() < 0.9
    level_up_text = ""

    if success:
        pay = job["pay"]
        if job_key == "loader" and player["car"] == "truck":
            pay = int(pay * 1.3)

        new_balance = player["balance"] + pay
        await update_player(callback.from_user.id, balance=new_balance)

        # ✅ Добавляем опыт + автоуровень
        exp_result = await add_exp(callback.from_user.id, job["exp"])
        if exp_result and exp_result["levels_up"] > 0:
            level_up_text = f"\n\n🎉 <b>УРОВЕНЬ {exp_result['level']}!</b>"

        result_text = (
            f"✅ <b>УСПЕХ!</b>\n\n"
            f"{job['name']}\n"
            f"💰 +${pay}\n"
            f"📊 +{job['exp']} опыта"
        )
    else:
        penalty = job["fail_pay"]
        new_balance = max(0, player["balance"] - penalty)
        await update_player(callback.from_user.id, balance=new_balance)

        result_text = (
            f"❌ <b>ПРОВАЛ!</b>\n\n"
            f"{job['name']}\n"
            f"💰 -${penalty} (штраф)"
        )

    if callback.from_user.id not in job_cooldowns:
        job_cooldowns[callback.from_user.id] = {}
    job_cooldowns[callback.from_user.id][job_key] = now + timedelta(seconds=job["cd"])

    await callback.message.edit_text(
        result_text + level_up_text + f"\n\n⏱ Следующая работа через {job['cd'] // 60} мин",
        reply_markup=back_to_jobs_kb(),
    )
    await callback.answer()


# ============================================
# МЕНЮ ТАКСИ
# ============================================
@router.callback_query(F.data == "taxi_menu")
async def taxi_menu(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    now = datetime.now()
    hourly = taxi_hourly.get(callback.from_user.id)
    if not hourly or now >= hourly["reset_at"]:
        taxi_hourly[callback.from_user.id] = {
            "count": 0,
            "reset_at": now + timedelta(hours=1),
        }
        hourly = taxi_hourly[callback.from_user.id]

    state = taxi_state.get(callback.from_user.id, {})

    if state.get("on_shift"):
        await callback.message.edit_text(
            f"🚕 <b>ТАКСИСТ</b>\n\n"
            f"Статус: 🟢 На смене\n"
            f"💰 Заработано: ${state.get('earned', 0)}\n"
            f"📊 Опыт: +{state.get('exp', 0)}\n"
            f"📦 Заказов: {state.get('orders', 0)}\n"
            f"⏱ За час: {hourly['count']}/10",
            reply_markup=taxi_orders_kb(),
        )
    else:
        left = int((hourly["reset_at"] - now).total_seconds())
        mins, secs = divmod(left, 60)

        if hourly["count"] >= 10:
            status_text = (
                f"⏳ <b>Лимит исчерпан</b>\n\n"
                f"Ты выполнил 10 заказов за час.\n"
                f"⏱ Сброс через: {mins}:{secs:02d}\n\n"
                f"Приходи позже!"
            )
        else:
            status_text = (
                "🚕 <b>ТАКСИ</b>\n\n"
                "Работай таксистом:\n"
                "• Клиент-игрок платит $150 (+20 опыта)\n"
                "• NPC-клиент платит $200 (+15 опыта)\n\n"
                f"⏱ Лимит: {hourly['count']}/10 заказов в час\n"
                f"Осталось: {10 - hourly['count']} заказов"
            )

        await callback.message.edit_text(
            status_text,
            reply_markup=taxi_menu_kb(hourly["count"]),
        )
    await callback.answer()


@router.callback_query(F.data == "taxi_start_shift")
async def taxi_start_shift(callback: CallbackQuery):
    now = datetime.now()

    hourly = taxi_hourly.get(callback.from_user.id)
    if not hourly or now >= hourly["reset_at"]:
        taxi_hourly[callback.from_user.id] = {
            "count": 0,
            "reset_at": now + timedelta(hours=1),
        }
        hourly = taxi_hourly[callback.from_user.id]

    if hourly["count"] >= 10:
        left = int((hourly["reset_at"] - now).total_seconds())
        mins, secs = divmod(left, 60)
        await callback.answer(
            f"⏳ Лимит 10/10. Сброс через: {mins}:{secs:02d}",
            show_alert=True,
        )
        return

    taxi_state[callback.from_user.id] = {
        "on_shift": True,
        "earned": 0,
        "exp": 0,
        "orders": 0,
    }

    await callback.message.edit_text(
        "🚕 <b>ТАКСИСТ</b>\n\n"
        "Статус: 🟢 На смене\n"
        "💰 Заработано: $0\n"
        "📊 Опыт: +0\n"
        "📦 Заказов: 0\n"
        f"⏱ За час: {hourly['count']}/10\n\n"
        "⏳ Ждём заказ...",
        reply_markup=taxi_orders_kb(),
    )
    await callback.answer("Смена началась!")


@router.callback_query(F.data == "taxi_stop_shift")
async def taxi_stop_shift(callback: CallbackQuery):
    state = taxi_state.get(callback.from_user.id, {})
    earned = state.get("earned", 0)
    exp_gained = state.get("exp", 0)
    orders = state.get("orders", 0)

    taxi_state.pop(callback.from_user.id, None)

    hourly = taxi_hourly.get(callback.from_user.id, {})
    count = hourly.get("count", 0)

    await callback.message.edit_text(
        f"🚕 <b>СМЕНА ЗАВЕРШЕНА</b>\n\n"
        f"💰 Заработано: ${earned}\n"
        f"📊 Опыт: +{exp_gained}\n"
        f"📦 Заказов: {orders}\n\n"
        f"⏱ За час: {count}/10\n"
        f"Можешь начать новую смену.",
        reply_markup=back_to_jobs_kb(),
    )
    await callback.answer("Смена окончена")


# ============================================
# NPC-ЗАКАЗ (с опытом + автоуровень)
# ============================================
@router.callback_query(F.data == "taxi_wait_order")
async def taxi_wait_order(callback: CallbackQuery):
    state = taxi_state.get(callback.from_user.id, {})
    if not state.get("on_shift"):
        await callback.answer("Сначала начни смену")
        return

    now = datetime.now()

    hourly = taxi_hourly.get(callback.from_user.id)
    if not hourly or now >= hourly["reset_at"]:
        taxi_hourly[callback.from_user.id] = {
            "count": 0,
            "reset_at": now + timedelta(hours=1),
        }
        hourly = taxi_hourly[callback.from_user.id]

    if hourly["count"] >= 10:
        left = int((hourly["reset_at"] - now).total_seconds())
        mins, secs = divmod(left, 60)
        taxi_state.pop(callback.from_user.id, None)

        await callback.message.edit_text(
            f"🚕 <b>ЛИМИТ ИСЧЕРПАН</b>\n\n"
            f"Ты выполнил 10 заказов за час.\n"
            f"⏱ Следующие через: {mins}:{secs:02d}\n\n"
            f"💰 Заработано: ${state.get('earned', 0)}\n"
            f"📊 Опыт: +{state.get('exp', 0)}\n"
            f"📦 Заказов: {state.get('orders', 0)}",
            reply_markup=back_to_jobs_kb(),
        )
        await callback.answer("Лимит исчерпан")
        return

    last_order = state.get("last_order")
    if last_order and now < last_order:
        left = int((last_order - now).total_seconds())
        await callback.answer(f"⏳ Подожди {left} сек", show_alert=True)
        return

    if random.random() >= 0.8:
        state["last_order"] = now + timedelta(seconds=30)
        taxi_state[callback.from_user.id] = state

        await callback.message.edit_text(
            f"🚕 <b>NPC-ЗАКАЗ</b>\n\n"
            f"😔 Клиентов нет.\n"
            f"Попробуй через 30 сек.\n\n"
            f"💰 ${state.get('earned', 0)} | 📦 {state.get('orders', 0)}\n"
            f"⏱ За час: {hourly['count']}/10",
            reply_markup=taxi_orders_kb(),
        )
        await callback.answer("Клиентов нет")
        return

    pay = 200
    exp_gain = 15

    player = await get_player(callback.from_user.id)
    new_balance = player["balance"] + pay
    await update_player(callback.from_user.id, balance=new_balance)

    # ✅ Опыт + автоуровень
    exp_result = await add_exp(callback.from_user.id, exp_gain)
    level_up_text = ""
    if exp_result and exp_result["levels_up"] > 0:
        level_up_text = f"\n🎉 <b>УРОВЕНЬ {exp_result['level']}!</b>"

    state["earned"] = state.get("earned", 0) + pay
    state["exp"] = state.get("exp", 0) + exp_gain
    state["orders"] = state.get("orders", 0) + 1
    state["last_order"] = now + timedelta(seconds=30)
    taxi_state[callback.from_user.id] = state

    hourly["count"] += 1
    taxi_hourly[callback.from_user.id] = hourly

    await callback.message.edit_text(
        f"🚕 <b>NPC-ЗАКАЗ</b>\n\n"
        f"👤 Клиент: NPC\n"
        f"💰 +${pay}\n"
        f"📊 +{exp_gain} опыта{level_up_text}\n\n"
        f"💰 ${state['earned']} | 📦 {state['orders']}\n"
        f"⏱ За час: {hourly['count']}/10\n"
        f"⏱ Следующий через 30 сек",
        reply_markup=taxi_orders_kb(),
    )
    await callback.answer("Заказ выполнен!")


# ============================================
# ВЫЗОВ ТАКСИ (КЛИЕНТ)
# ============================================
@router.callback_query(F.data == "taxi_call")
async def taxi_call(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if player["balance"] < 150:
        await callback.answer("💰 Нужно $150", show_alert=True)
        return

    new_balance = player["balance"] - 150
    await update_player(callback.from_user.id, balance=new_balance)

    await callback.message.edit_text(
        "🚕 <b>NPC-ТАКСИ</b>\n\n"
        "Таксистов-игроков нет, едет NPC.\n"
        "💰 -$150\n\n"
        "✅ Ты переехал в другой район!",
        reply_markup=back_to_jobs_kb(),
    )
    await callback.answer("Поехали!")


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer("🔒 Уровень недостаточен", show_alert=True)
