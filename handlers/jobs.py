# ============================================
# РАБОТЫ (NPC + ТАКСИ PvP)
# ============================================

import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import get_player, update_player
from keyboards import (
    jobs_menu_kb, back_to_jobs_kb,
    taxi_menu_kb, taxi_orders_kb,
)


router = Router()

# ============================================
# NPC-РАБОТЫ
# ============================================
JOBS = {
    "pizza": {
        "name": "🍔 Пицца",
        "lvl": 1,
        "pay": 100,
        "cd": 180,        # 3 минуты
        "fail_pay": 50,
        "exp": 10,
    },
    "courier": {
        "name": "📦 Курьер",
        "lvl": 1,
        "pay": 150,
        "cd": 300,        # 5 минут
        "fail_pay": 50,
        "exp": 15,
    },
    "loader": {
        "name": "🏗 Грузчик",
        "lvl": 5,
        "pay": 300,
        "cd": 1200,       # 20 минут
        "fail_pay": 100,
        "exp": 25,
    },
    "trucker": {
        "name": "🚚 Дальнобой",
        "lvl": 10,
        "pay": 800,
        "cd": 3600,       # 1 час
        "fail_pay": 200,
        "exp": 50,
    },
}

# Хранилище кулдаунов и состояний такси (в оперативке)
job_cooldowns = {}          # {telegram_id: {job_key: datetime}}
taxi_state = {}             # {telegram_id: {...}}


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
        "• NPC-работы — просто нажал и получил\n"
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
        "💼 <b>РАБОТЫ</b>\n\n"
        "Выбери подработку:",
        reply_markup=jobs_menu_kb(player["level"]),
    )
    await callback.answer()


# ============================================
# ВЫПОЛНЕНИЕ NPC-РАБОТЫ
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

    # Проверка уровня
    if player["level"] < job["lvl"]:
        await callback.answer(f"🔒 Нужен уровень {job['lvl']}", show_alert=True)
        return

    # Проверка кулдауна
    user_cd = job_cooldowns.get(callback.from_user.id, {})
    last = user_cd.get(job_key)
    now = datetime.now()

    if last and now < last:
        left = int((last - now).total_seconds())
        mins, secs = divmod(left, 60)
        await callback.answer(
            f"⏳ Подожди {mins}:{secs:02d}",
            show_alert=True,
        )
        return

    # Рандом: 90% успех, 10% провал
    success = random.random() < 0.9

    if success:
        pay = job["pay"]
        # Бонус грузовика для грузчика
        if job_key == "loader" and player["car"] == "truck":
            pay = int(pay * 1.3)

        new_balance = player["balance"] + pay
        new_exp = player["exp"] + job["exp"]

        await update_player(
            callback.from_user.id,
            balance=new_balance,
            exp=new_exp,
        )

        result_text = (
            f"✅ <b>УСПЕХ!</b>\n\n"
            f"{job['name']}\n"
            f"💰 +${pay}\n"
            f"📊 +{job['exp']} опыта"
        )
    else:
        penalty = job["fail_pay"]
        new_balance = max(0, player["balance"] - penalty)

        await update_player(
            callback.from_user.id,
            balance=new_balance,
        )

        result_text = (
            f"❌ <b>ПРОВАЛ!</b>\n\n"
            f"{job['name']}\n"
            f"💰 -${penalty} (штраф)"
        )

    # Кулдаун
    if callback.from_user.id not in job_cooldowns:
        job_cooldowns[callback.from_user.id] = {}
    job_cooldowns[callback.from_user.id][job_key] = now + timedelta(seconds=job["cd"])

    await callback.message.edit_text(
        result_text + f"\n\n⏱ Следующая работа через {job['cd'] // 60} мин",
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

    state = taxi_state.get(callback.from_user.id, {})

    if state.get("on_shift"):
        await callback.message.edit_text(
            f"🚕 <b>ТАКСИСТ</b>\n\n"
            f"Статус: 🟢 На смене\n"
            f"💰 Заработано: ${state.get('earned', 0)}\n"
            f"📦 Заказов: {state.get('orders', 0)}",
            reply_markup=taxi_orders_kb(),
        )
    else:
        await callback.message.edit_text(
            "🚕 <b>ТАКСИ</b>\n\n"
            "Ты можешь работать таксистом и возить игроков.\n\n"
            "• Клиент-игрок платит тебе $150\n"
            "• NPC-клиент платит тебе $200",
            reply_markup=taxi_menu_kb(),
        )
    await callback.answer()


@router.callback_query(F.data == "taxi_start_shift")
async def taxi_start_shift(callback: CallbackQuery):
    taxi_state[callback.from_user.id] = {
        "on_shift": True,
        "earned": 0,
        "orders": 0,
    }
    await callback.message.edit_text(
        "🚕 <b>ТАКСИСТ</b>\n\n"
        "Статус: 🟢 На смене\n"
        "💰 Заработано: $0\n"
        "📦 Заказов: 0\n\n"
        "⏳ Ждём заказ...",
        reply_markup=taxi_orders_kb(),
    )
    await callback.answer("Смена началась!")


@router.callback_query(F.data == "taxi_stop_shift")
async def taxi_stop_shift(callback: CallbackQuery):
    state = taxi_state.get(callback.from_user.id, {})
    earned = state.get("earned", 0)
    orders = state.get("orders", 0)

    taxi_state.pop(callback.from_user.id, None)

    await callback.message.edit_text(
        f"🚕 <b>СМЕНА ЗАВЕРШЕНА</b>\n\n"
        f"💰 Заработано: ${earned}\n"
        f"📦 Заказов: {orders}",
        reply_markup=back_to_jobs_kb(),
    )
    await callback.answer("Смена окончена")


# ============================================
# NPC-ЗАКАЗ ДЛЯ ТАКСИСТА
# ============================================
@router.callback_query(F.data == "taxi_wait_order")
async def taxi_wait_order(callback: CallbackQuery):
    state = taxi_state.get(callback.from_user.id, {})
    if not state.get("on_shift"):
        await callback.answer("Сначала начни смену")
        return

    # NPC-клиент платит $200
    pay = 200
    player = await get_player(callback.from_user.id)
    new_balance = player["balance"] + pay

    await update_player(callback.from_user.id, balance=new_balance)

    state["earned"] = state.get("earned", 0) + pay
    state["orders"] = state.get("orders", 0) + 1
    taxi_state[callback.from_user.id] = state

    await callback.message.edit_text(
        f"🚕 <b>NPC-ЗАКАЗ</b>\n\n"
        f"👤 Клиент: NPC\n"
        f"💰 +${pay}\n\n"
        f"💰 Всего заработано: ${state['earned']}\n"
        f"📦 Заказов: {state['orders']}",
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
        f"💰 -$150\n\n"
        "✅ Ты переехал в другой район!",
        reply_markup=back_to_jobs_kb(),
    )
    await callback.answer("Поехали!")


# ============================================
# ЗАГЛУШКА ДЛЯ ЗАБЛОКИРОВАННЫХ КНОПОК
# ============================================
@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer("🔒 Уровень недостаточен", show_alert=True)
