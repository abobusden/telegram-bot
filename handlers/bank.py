# ============================================
# БАНК (счёт + вклад + переводы)
# ============================================

import random
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import bank_menu_kb, bank_back_kb
from states import Bank


router = Router()

DEPOSIT_MIN = 1000
INTEREST_RATE = 0.05
INTEREST_PERIOD_HOURS = 24


# ============================================
# ГЕНЕРАЦИЯ НОМЕРА СЧЁТА
# ============================================
async def generate_account():
    """Генерирует уникальный 6-значный номер счёта."""
    import aiosqlite
    from config import DB_PATH

    while True:
        number = str(random.randint(100000, 999999))

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT 1 FROM players WHERE bank_account = ?", (number,)
            ) as cur:
                if not await cur.fetchone():
                    return number


# ============================================
# НАЧИСЛЕНИЕ ПРОЦЕНТОВ
# ============================================
async def apply_interest(telegram_id: int):
    player = await get_player(telegram_id)
    if not player:
        return

    deposit = player.get("bank_deposit", 0) or 0
    if deposit <= 0:
        return

    last = player.get("bank_last_interest")
    if not last:
        return

    try:
        last_dt = datetime.fromisoformat(last)
    except:
        return

    now = datetime.now()
    elapsed = now - last_dt

    if elapsed.total_seconds() < INTEREST_PERIOD_HOURS * 3600:
        return

    days = int(elapsed.total_seconds() // (INTEREST_PERIOD_HOURS * 3600))
    interest = int(deposit * INTEREST_RATE * days)
    new_deposit = deposit + interest

    await update_player(
        telegram_id,
        bank_deposit=new_deposit,
        bank_last_interest=now.isoformat(),
    )


# ============================================
# МЕНЮ БАНКА
# ============================================
@router.message(F.text == "🏦 Банк")
async def bank_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    if not player.get("bank_account"):
        await message.answer(
            f"🏦 <b>БАНК</b>\n\n"
            f"У тебя нет банковского счёта.\n\n"
            f"Создать счёт?",
            reply_markup=bank_create_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    await apply_interest(message.from_user.id)
    player = await get_player(message.from_user.id)

    account = player["bank_account"]
    bank_balance = player.get("bank_balance", 0) or 0
    deposit = player.get("bank_deposit", 0) or 0

    await message.answer(
        f"🏦 <b>БАНК</b>\n\n"
        f"💳 Счёт: <code>{account}</code>\n"
        f"💰 На счёте: ${bank_balance}\n"
        f"💼 Вклад: ${deposit}",
        reply_markup=bank_menu_kb(bank_balance, deposit),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "bank_back")
async def bank_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    account = player["bank_account"]
    bank_balance = player.get("bank_balance", 0) or 0
    deposit = player.get("bank_deposit", 0) or 0

    await callback.message.delete()
    await callback.message.answer(
        f"🏦 <b>БАНК</b>\n\n"
        f"💳 Счёт: <code>{account}</code>\n"
        f"💰 На счёте: ${bank_balance}\n"
        f"💼 Вклад: ${deposit}",
        reply_markup=bank_menu_kb(bank_balance, deposit),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# СОЗДАНИЕ СЧЁТА
# ============================================
@router.callback_query(F.data == "bank_create")
async def bank_create(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if player.get("bank_account"):
        await callback.answer("У тебя уже есть счёт")
        return

    account = await generate_account()

    await update_player(
        callback.from_user.id,
        bank_account=account,
        bank_balance=0,
        bank_deposit=0,
    )

    await callback.message.delete()
    await callback.message.answer(
        f"✅ <b>СЧЁТ СОЗДАН!</b>\n\n"
        f"💳 Номер: <code>{account}</code>\n\n"
        f"Теперь можешь пользоваться банком.",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Создан!")


# ============================================
# ПОПОЛНИТЬ СЧЁТ
# ============================================
@router.callback_query(F.data == "bank_topup")
async def bank_topup(callback: CallbackQuery, state: FSMContext):
    player = await get_player(callback.from_user.id)

    await callback.message.delete()
    await callback.message.answer(
        f"📥 <b>ПОПОЛНИТЬ СЧЁТ</b>\n\n"
        f"💰 В кошельке: ${player['balance']}\n\n"
        f"Введи сумму в чат.\n\n"
        f"Пример: <code>1000</code>",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Bank.topup)
    await callback.answer()


@router.message(Bank.topup)
async def process_topup(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except:
        await message.answer("❌ Введи число:")
        return

    if amount < 1:
        await message.answer("❌ Минимум $1:")
        return

    player = await get_player(message.from_user.id)

    if player["balance"] < amount:
        await message.answer(f"❌ Недостаточно (у тебя ${player['balance']}). Попробуй меньше:")
        return

    new_balance = player["balance"] - amount
    new_bank = (player.get("bank_balance", 0) or 0) + amount

    await update_player(
        message.from_user.id,
        balance=new_balance,
        bank_balance=new_bank,
    )

    await state.clear()

    await message.answer(
        f"✅ <b>СЧЁТ ПОПОЛНЕН!</b>\n\n"
        f"💰 +${amount}\n"
        f"💰 На счёте: ${new_bank}",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# СНЯТЬ СО СЧЁТА
# ============================================
@router.callback_query(F.data == "bank_withdraw_acc")
async def bank_withdraw_acc(callback: CallbackQuery, state: FSMContext):
    player = await get_player(callback.from_user.id)
    bank_balance = player.get("bank_balance", 0) or 0

    if bank_balance <= 0:
        await callback.answer("💰 На счёте пусто", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(
        f"💸 <b>СНЯТЬ СО СЧЁТА</b>\n\n"
        f"💰 На счёте: ${bank_balance}\n\n"
        f"Введи сумму в чат.\n\n"
        f"Пример: <code>1000</code>",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Bank.withdraw)
    await callback.answer()


@router.message(Bank.withdraw)
async def process_withdraw(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except:
        await message.answer("❌ Введи число:")
        return

    if amount < 1:
        await message.answer("❌ Минимум $1:")
        return

    player = await get_player(message.from_user.id)
    bank_balance = player.get("bank_balance", 0) or 0

    if bank_balance < amount:
        await message.answer(f"❌ Недостаточно на счёте (${bank_balance}). Попробуй меньше:")
        return

    new_balance = player["balance"] + amount
    new_bank = bank_balance - amount

    await update_player(
        message.from_user.id,
        balance=new_balance,
        bank_balance=new_bank,
    )

    await state.clear()

    await message.answer(
        f"✅ <b>СНЯТО!</b>\n\n"
        f"💰 +${amount} в кошелёк\n"
        f"💰 На счёте: ${new_bank}",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# ПЕРЕВОД НА ДРУГОЙ СЧЁТ
# ============================================
@router.callback_query(F.data == "bank_transfer")
async def bank_transfer(callback: CallbackQuery, state: FSMContext):
    player = await get_player(callback.from_user.id)
    bank_balance = player.get("bank_balance", 0) or 0

    if bank_balance <= 0:
        await callback.answer("💰 На счёте пусто", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(
        f"💸 <b>ПЕРЕВОД</b>\n\n"
        f"💳 Твой счёт: <code>{player['bank_account']}</code>\n"
        f"💰 На счёте: ${bank_balance}\n\n"
        f"Введи номер счёта получателя (6 цифр):\n\n"
        f"Пример: <code>573920</code>",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Bank.transfer_account)
    await callback.answer()


@router.message(Bank.transfer_account)
async def process_transfer_account(message: Message, state: FSMContext):
    account = message.text.strip()

    if not account.isdigit() or len(account) != 6:
        await message.answer("❌ Номер счёта — 6 цифр. Попробуй ещё:")
        return

    player = await get_player(message.from_user.id)

    if account == player["bank_account"]:
        await message.answer("❌ Нельзя перевести самому себе. Попробуй другой:")
        return

    # Ищем получателя
    import aiosqlite
    from config import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT nickname FROM players WHERE bank_account = ?", (account,)
        ) as cur:
            row = await cur.fetchone()

    if not row:
        await message.answer(f"❌ Счёт {account} не найден. Попробуй другой:")
        return

    await state.update_data(recipient_account=account, recipient_name=row["nickname"])
    await state.set_state(Bank.transfer_amount)

    await message.answer(
        f"💸 <b>ПЕРЕВОД</b>\n\n"
        f"💳 Получатель: {row['nickname']}\n"
        f"💳 Счёт: <code>{account}</code>\n\n"
        f"Введи сумму:",
        parse_mode=ParseMode.HTML,
    )


@router.message(Bank.transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except:
        await message.answer("❌ Введи число:")
        return

    if amount < 1:
        await message.answer("❌ Минимум $1:")
        return

    player = await get_player(message.from_user.id)
    bank_balance = player.get("bank_balance", 0) or 0

    if bank_balance < amount:
        await message.answer(f"❌ Недостаточно (${bank_balance}). Попробуй меньше:")
        return

    data = await state.get_data()

    await state.clear()

    await message.answer(
        f"💸 <b>ПОДТВЕРЖДЕНИЕ</b>\n\n"
        f"💳 Откуда: <code>{player['bank_account']}</code>\n"
        f"💳 Куда: <code>{data['recipient_account']}</code>\n"
        f"👤 Получатель: {data['recipient_name']}\n"
        f"💰 Сумма: ${amount}\n\n"
        f"Ты уверен?",
        reply_markup=bank_confirm_transfer_kb(
            data["recipient_account"],
            data["recipient_name"],
            amount,
        ),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("bank_confirm_"))
async def bank_confirm_transfer(callback: CallbackQuery):
    # Парсим callback: bank_confirm_573920_1000
    parts = callback.data.replace("bank_confirm_", "").split("_")
    if len(parts) != 2:
        await callback.answer("Ошибка")
        return

    account = parts[0]
    amount = int(parts[1])

    player = await get_player(callback.from_user.id)
    bank_balance = player.get("bank_balance", 0) or 0

    if bank_balance < amount:
        await callback.answer("💰 Недостаточно", show_alert=True)
        return

    # Ищем получателя
    import aiosqlite
    from config import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT telegram_id, bank_balance FROM players WHERE bank_account = ?",
            (account,)
        ) as cur:
            recipient = await cur.fetchone()

    if not recipient:
        await callback.answer("Счёт не найден", show_alert=True)
        return

    # Списываем у отправителя
    await update_player(
        callback.from_user.id,
        bank_balance=bank_balance - amount,
    )

    # Зачисляем получателю
    recipient_balance = (recipient["bank_balance"] or 0) + amount
    await update_player(
        recipient["telegram_id"],
        bank_balance=recipient_balance,
    )

    await callback.message.delete()
    await callback.message.answer(
        f"✅ <b>ПЕРЕВОД ВЫПОЛНЕН!</b>\n\n"
        f"💳 Куда: <code>{account}</code>\n"
        f"💰 Сумма: ${amount}",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Переведено!")


# ============================================
# ВКЛАД
# ============================================
@router.callback_query(F.data == "bank_deposit")
async def bank_deposit(callback: CallbackQuery, state: FSMContext):
    player = await get_player(callback.from_user.id)
    bank_balance = player.get("bank_balance", 0) or 0

    if bank_balance < DEPOSIT_MIN:
        await callback.answer(f"💰 Нужно минимум ${DEPOSIT_MIN} на счёте", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(
        f"📈 <b>ВКЛАД 5%/ДЕНЬ</b>\n\n"
        f"💰 На счёте: ${bank_balance}\n\n"
        f"Введи сумму вклада.\n\n"
        f"Минимум: ${DEPOSIT_MIN}\n\n"
        f"Пример: <code>5000</code>",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Bank.deposit)
    await callback.answer()


@router.message(Bank.deposit)
async def process_deposit(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except:
        await message.answer("❌ Введи число:")
        return

    if amount < DEPOSIT_MIN:
        await message.answer(f"❌ Минимум ${DEPOSIT_MIN}:")
        return

    player = await get_player(message.from_user.id)
    bank_balance = player.get("bank_balance", 0) or 0

    if bank_balance < amount:
        await message.answer(f"❌ Недостаточно (${bank_balance}). Попробуй меньше:")
        return

    new_bank = bank_balance - amount
    new_deposit = (player.get("bank_deposit", 0) or 0) + amount

    await update_player(
        message.from_user.id,
        bank_balance=new_bank,
        bank_deposit=new_deposit,
        bank_last_interest=datetime.now().isoformat(),
    )

    await state.clear()

    await message.answer(
        f"✅ <b>ВКЛАД ОФОРМЛЕН!</b>\n\n"
        f"💼 Вклад: ${new_deposit}\n"
        f"📈 Процент: 5%/день\n"
        f"⏱ Начисление через 24ч",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# СНЯТЬ ВКЛАД
# ============================================
@router.callback_query(F.data == "bank_withdraw_dep")
async def bank_withdraw_dep(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    deposit = player.get("bank_deposit", 0) or 0

    if deposit <= 0:
        await callback.answer("💼 Вклад пустой", show_alert=True)
        return

    await apply_interest(callback.from_user.id)
    player = await get_player(callback.from_user.id)
    deposit = player.get("bank_deposit", 0) or 0

    new_bank = (player.get("bank_balance", 0) or 0) + deposit

    await update_player(
        callback.from_user.id,
        bank_balance=new_bank,
        bank_deposit=0,
        bank_last_interest=None,
    )

    await callback.message.delete()
    await callback.message.answer(
        f"✅ <b>ВКЛАД СНЯТ!</b>\n\n"
        f"💰 +${deposit} на счёт\n"
        f"💰 На счёте: ${new_bank}",
        reply_markup=bank_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Снято!")
