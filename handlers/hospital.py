# ============================================
# БОЛЬНИЦА (лечение)
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import hospital_menu_kb, hospital_back_kb


router = Router()

HEAL_PRICE = 500


@router.message(F.text == "🏥 Больница")
async def hospital_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    if player["hp"] >= 100:
        await message.answer(
            f"🏥 <b>БОЛЬНИЦА</b>\n\n"
            f"❤️ Твоё HP: {player['hp']}/100\n\n"
            f"Ты здоров!\n"
            f"Лечение не нужно.",
            reply_markup=hospital_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    text = (
        f"🏥 <b>БОЛЬНИЦА</b>\n\n"
        f"❤️ Твоё HP: {player['hp']}/100\n\n"
        f"💰 Лечение: ${HEAL_PRICE}\n"
        f"❤️ Восстановит: 100/100\n"
    )

    if player["balance"] < HEAL_PRICE:
        text += f"\n❌ <b>Не хватает денег!</b>\n💰 У тебя: ${player['balance']}"

    await message.answer(
        text,
        reply_markup=hospital_menu_kb(player["balance"], player["hp"]),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "hospital_back")
async def hospital_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if player["hp"] >= 100:
        await callback.message.delete()
        await callback.message.answer(
            f"🏥 <b>БОЛЬНИЦА</b>\n\n"
            f"❤️ Твоё HP: {player['hp']}/100\n\n"
            f"Ты здоров!\n"
            f"Лечение не нужно.",
            reply_markup=hospital_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()
        return

    text = (
        f"🏥 <b>БОЛЬНИЦА</b>\n\n"
        f"❤️ Твоё HP: {player['hp']}/100\n\n"
        f"💰 Лечение: ${HEAL_PRICE}\n"
        f"❤️ Восстановит: 100/100\n"
    )

    if player["balance"] < HEAL_PRICE:
        text += f"\n❌ <b>Не хватает денег!</b>\n💰 У тебя: ${player['balance']}"

    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=hospital_menu_kb(player["balance"], player["hp"]),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "hospital_heal")
async def hospital_heal(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["hp"] >= 100:
        await callback.answer("Ты здоров!", show_alert=True)
        return

    if player["balance"] < HEAL_PRICE:
        await callback.answer("💰 Не хватает денег", show_alert=True)
        return

    new_balance = player["balance"] - HEAL_PRICE

    await update_player(
        callback.from_user.id,
        balance=new_balance,
        hp=100,
    )

    await callback.message.delete()
    await callback.message.answer(
        f"✅ <b>ПРОЛЕЧЕН!</b>\n\n"
        f"❤️ HP: 100/100\n"
        f"💰 -${HEAL_PRICE}\n\n"
        f"Ты снова в строю!",
        reply_markup=hospital_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Пролечен!")
