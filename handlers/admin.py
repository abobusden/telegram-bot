# ============================================
# АДМИН-ПАНЕЛЬ
# ============================================

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import SUPPORT_ID
from database import (
    get_player, update_player, get_player_by_nickname,
)
from keyboards import (
    admin_menu_kb, admin_user_kb, admin_back_kb,
    admin_cancel_kb, admin_weapons_kb,
    admin_cars_kb, admin_homes_kb,
)
from states import Admin


router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == SUPPORT_ID


# ============================================
# /admin
# ============================================
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        f"🛠 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"Выбери действие:",
        reply_markup=admin_menu_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    await state.clear()

    await callback.message.edit_text(
        f"🛠 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"Выбери действие:",
        reply_markup=admin_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ПОИСК ИГРОКА
# ============================================
@router.callback_query(F.data == "admin_players")
async def admin_players(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        f"👥 <b>ИГРОКИ</b>\n\n"
        f"Введи ник или ID игрока:\n\n"
        f"Пример: <code>BigSmoke_88</code>",
        reply_markup=admin_cancel_kb(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(Admin.find_user)
    await callback.answer()


@router.message(Admin.find_user)
async def find_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    query = message.text.strip()
    player = None

    if query.isdigit():
        player = await get_player(int(query))
    else:
        player = await get_player_by_nickname(query)

    if not player:
        await message.answer(
            f"❌ Игрок <b>{query}</b> не найден.\n\nПопробуй ещё:",
            parse_mode=ParseMode.HTML,
        )
        return

    await state.clear()
    await show_user_profile(player, message)


# ============================================
# ПРОФИЛЬ
# ============================================
async def show_user_profile(player: dict, message: Message):
    gender = "👨" if player["gender"] == "male" else "👩"
    faction = player.get("faction") or "нет"
    home = player.get("home") or "нет"
    weapon = player.get("weapon") or "нет"
    car = player.get("car") or "нет"
    engine = player.get("engine_level", 0)
    nitro = "да" if player.get("nitro", 0) else "нет"
    bank_acc = player.get("bank_account") or "нет"
    bank_bal = player.get("bank_balance", 0) or 0
    deposit = player.get("bank_deposit", 0) or 0
    wanted = "⭐" * player["wanted"] if player["wanted"] > 0 else "чисто"
    status = "🚫 Забанен" if player.get("is_banned") else "✅ Активен"

    text = (
        f"👤 <b>ПРОФИЛЬ ИГРОКА</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{player['telegram_id']}</code>\n"
        f"👤 Ник: <b>{player['nickname']}</b>\n"
        f"⚧ Пол: {gender}\n"
        f"🚩 Банда: {faction}\n"
        f"📍 Район: {player['district']}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>СТАТЫ:</b>\n"
        f"❤️ HP: {player['hp']}/100\n"
        f"💰 Баланс: ${player['balance']:,}\n"
        f"⭐ Уровень: {player['level']}\n"
        f"📊 Опыт: {player['exp']}/{player['level'] * 100}\n"
        f"🚨 Розыск: {wanted}\n"
        f"🎯 Ур.криминала: {player.get('crime_level', 1)}/5\n"
        f"📈 Дел до ур.: {player.get('crime_deals', 0)}/5\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎒 <b>ИМУЩЕСТВО:</b>\n"
        f"🏠 Жильё: {home}\n"
        f"🚗 Машина: {car}\n"
        f"🔧 Двигатель: ур.{engine}\n"
        f"💨 Нитро: {nitro}\n"
        f"🔫 Оружие: {weapon}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>БАНК:</b>\n"
        f"💳 Счёт: {bank_acc}\n"
        f"💰 На счёте: ${bank_bal:,}\n"
        f"💼 Вклад: ${deposit:,}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>СТАТИСТИКА:</b>\n"
        f"💼 Работ: {player.get('crime_deals', 0)}\n"
        f"⚔️ Побед PvP: {player.get('pvp_wins', 0)}\n"
        f"❌ Поражений PvP: {player.get('pvp_losses', 0)}\n"
        f"🏁 Побед в гонках: {player.get('race_wins', 0)}\n"
        f"👥 Приглашено: {player.get('referral_count', 0)}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🚫 Статус: {status}\n"
    )

    await message.answer(
        text,
        reply_markup=admin_user_kb(player["telegram_id"], player.get("is_banned", 0)),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# ВЫДАТЬ ДЕНЬГИ
# ============================================
@router.callback_query(F.data.startswith("admin_give_"))
async def admin_give(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    target_id = int(callback.data.replace("admin_give_", ""))
    await state.update_data(target_id=target_id)
    await state.set_state(Admin.give_money)

    await callback.message.edit_text(
        f"💰 <b>ВЫДАТЬ ДЕНЬГИ</b>\n\n"
        f"Введи сумму:\n"
        f"Пример: <code>100000</code>",
        reply_markup=admin_cancel_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message(Admin.give_money)
async def process_give(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        amount = int(message.text.strip())
    except:
        await message.answer("❌ Введи число:")
        return

    data = await state.get_data()
    target_id = data["target_id"]

    player = await get_player(target_id)
    if not player:
        await message.answer("❌ Игрок не найден")
        await state.clear()
        return

    await update_player(target_id, balance=player["balance"] + amount)
    await state.clear()

    await message.answer(
        f"✅ <b>ВЫДАНО!</b>\n\n"
        f"👤 {player['nickname']}\n"
        f"💰 +${amount:,}\n"
        f"💵 Новый баланс: ${player['balance'] + amount:,}",
        reply_markup=admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# УСТАНОВИТЬ УРОВЕНЬ
# ============================================
@router.callback_query(F.data.startswith("admin_level_"))
async def admin_level(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    target_id = int(callback.data.replace("admin_level_", ""))
    await state.update_data(target_id=target_id)
    await state.set_state(Admin.set_level)

    await callback.message.edit_text(
        f"⭐ <b>УСТАНОВИТЬ УРОВЕНЬ</b>\n\n"
        f"Введи новый уровень:\n"
        f"Пример: <code>10</code>",
        reply_markup=admin_cancel_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message(Admin.set_level)
async def process_level(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        level = int(message.text.strip())
    except:
        await message.answer("❌ Введи число:")
        return

    data = await state.get_data()
    target_id = data["target_id"]

    player = await get_player(target_id)
    if not player:
        await message.answer("❌ Игрок не найден")
        await state.clear()
        return

    await update_player(target_id, level=level, exp=0)
    await state.clear()

    await message.answer(
        f"✅ <b>УРОВЕНЬ УСТАНОВЛЕН!</b>\n\n"
        f"👤 {player['nickname']}\n"
        f"⭐ Ур.{player['level']} → Ур.{level}",
        reply_markup=admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ============================================
# ВЫДАТЬ ОРУЖИЕ
# ============================================
@router.callback_query(F.data.startswith("admin_weapon_"))
async def admin_weapon(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    target_id = int(callback.data.replace("admin_weapon_", ""))

    await callback.message.edit_text(
        f"🎁 <b>ВЫДАТЬ ОРУЖИЕ</b>\n\n"
        f"Выбери:",
        reply_markup=admin_weapons_kb(target_id),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_setweapon_"))
async def admin_setweapon(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    parts = callback.data.replace("admin_setweapon_", "").split("_")
    target_id = int(parts[0])
    weapon = parts[1]

    await update_player(target_id, weapon=weapon)

    player = await get_player(target_id)
    await callback.message.edit_text(
        f"✅ <b>ОРУЖИЕ ВЫДАНО!</b>\n\n"
        f"👤 {player['nickname']}\n"
        f"🔫 {weapon}",
        reply_markup=admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ВЫДАТЬ МАШИНУ
# ============================================
@router.callback_query(F.data.startswith("admin_car_"))
async def admin_car(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    target_id = int(callback.data.replace("admin_car_", ""))

    await callback.message.edit_text(
        f"🚗 <b>ВЫДАТЬ МАШИНУ</b>\n\n"
        f"Выбери:",
        reply_markup=admin_cars_kb(target_id),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_setcar_"))
async def admin_setcar(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    parts = callback.data.replace("admin_setcar_", "").split("_")
    target_id = int(parts[0])
    car = parts[1]

    await update_player(target_id, car=car)

    player = await get_player(target_id)
    await callback.message.edit_text(
        f"✅ <b>МАШИНА ВЫДАНА!</b>\n\n"
        f"👤 {player['nickname']}\n"
        f"🚗 {car}",
        reply_markup=admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ВЫДАТЬ ДОМ
# ============================================
@router.callback_query(F.data.startswith("admin_home_"))
async def admin_home(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    target_id = int(callback.data.replace("admin_home_", ""))

    await callback.message.edit_text(
        f"🏠 <b>ВЫДАТЬ ДОМ</b>\n\n"
        f"Выбери:",
        reply_markup=admin_homes_kb(target_id),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_sethome_"))
async def admin_sethome(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    parts = callback.data.replace("admin_sethome_", "").split("_")
    target_id = int(parts[0])
    home = parts[1]

    await update_player(target_id, home=home)

    player = await get_player(target_id)
    await callback.message.edit_text(
        f"✅ <b>ДОМ ВЫДАН!</b>\n\n"
        f"👤 {player['nickname']}\n"
        f"🏠 {home}",
        reply_markup=admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# ЗАБАНИТЬ / РАЗБАНИТЬ
# ============================================
@router.callback_query(F.data.startswith("admin_ban_"))
async def admin_ban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    target_id = int(callback.data.replace("admin_ban_", ""))
    await update_player(target_id, is_banned=1)

    player = await get_player(target_id)
    await callback.message.edit_text(
        f"🚫 <b>ИГРОК ЗАБАНЕН</b>\n\n"
        f"👤 {player['nickname']}",
        reply_markup=admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_unban_"))
async def admin_unban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    target_id = int(callback.data.replace("admin_unban_", ""))
    await update_player(target_id, is_banned=0)

    player = await get_player(target_id)
    await callback.message.edit_text(
        f"✅ <b>ИГРОК РАЗБАНЕН</b>\n\n"
        f"👤 {player['nickname']}",
        reply_markup=admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ============================================
# СТАТИСТИКА
# ============================================
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    import aiosqlite
    from config import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) as c FROM players") as cur:
            total = (await cur.fetchone())["c"]

        async with db.execute("SELECT SUM(balance) as s FROM players") as cur:
            money = (await cur.fetchone())["s"] or 0

        async with db.execute("SELECT COUNT(*) as c FROM players WHERE is_banned = 1") as cur:
            banned = (await cur.fetchone())["c"]

    await callback.message.edit_text(
        f"📊 <b>СТАТИСТИКА</b>\n\n"
        f"👥 Всего игроков: {total}\n"
        f"🚫 Забанено: {banned}\n"
        f"💰 Денег в игре: ${money:,}",
        reply_markup=admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
