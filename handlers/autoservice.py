# ============================================
# АВТОСЕРВИС (улучшение машины)
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player
from keyboards import autoservice_menu_kb, autoservice_back_kb


router = Router()

AUTOSERVICE_PHOTO = "https://i.ibb.co/ns0ZMzHf/Screenshot-20260918-175758.jpg"

ENGINE_PRICES = {1: 3000, 2: 8000, 3: 15000}
NITRO_PRICE = 10000


@router.message(F.text == "🔧 Автосервис")
async def autoservice_menu(message: Message):
    player = await get_player(message.from_user.id)
    if not player:
        await message.answer("Сначала зарегистрируйся: /start")
        return

    if not player.get("car"):
        await message.answer(
            f"🔧 <b>АВТОСЕРВИС</b>\n\n"
            f"❌ У тебя нет машины!\n\n"
            f"Сначала купи машину в автосалоне,\n"
            f"потом возвращайся.",
            reply_markup=autoservice_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    engine = player.get("engine_level", 0)
    nitro = player.get("nitro", 0)

    nitro_text = "да" if nitro else "нет"

    await message.answer_photo(
        photo=AUTOSERVICE_PHOTO,
        caption=(
            f"🔧 <b>АВТОСЕРВИС</b>\n\n"
            f"🚗 Машина: {player['car']}\n"
            f"🔧 Двигатель: ур.{engine}\n"
            f"💨 Нитро: {nitro_text}\n\n"
            f"💰 Баланс: ${player['balance']}"
        ),
        reply_markup=autoservice_menu_kb(engine, nitro),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "autoservice_back")
async def autoservice_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if not player.get("car"):
        await callback.message.delete()
        await callback.message.answer(
            f"🔧 <b>АВТОСЕРВИС</b>\n\n"
            f"❌ У тебя нет машины!\n\n"
            f"Сначала купи машину в автосалоне.",
            reply_markup=autoservice_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()
        return

    engine = player.get("engine_level", 0)
    nitro = player.get("nitro", 0)

    nitro_text = "да" if nitro else "нет"

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=AUTOSERVICE_PHOTO,
        caption=(
            f"🔧 <b>АВТОСЕРВИС</b>\n\n"
            f"🚗 Машина: {player['car']}\n"
            f"🔧 Двигатель: ур.{engine}\n"
            f"💨 Нитро: {nitro_text}\n\n"
            f"💰 Баланс: ${player['balance']}"
        ),
        reply_markup=autoservice_menu_kb(engine, nitro),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "autoservice_engine")
async def autoservice_engine(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if not player.get("car"):
        await callback.answer("У тебя нет машины", show_alert=True)
        return

    engine = player.get("engine_level", 0)

    if engine >= 3:
        await callback.answer("🔧 Двигатель уже на максимуме!", show_alert=True)
        return

    next_level = engine + 1
    price = ENGINE_PRICES[next_level]

    if player["balance"] < price:
        await callback.answer(f"💰 Нужно ${price}", show_alert=True)
        return

    await update_player(
        callback.from_user.id,
        balance=player["balance"] - price,
        engine_level=next_level,
    )

    mult = {1: 0.9, 2: 0.8, 3: 0.7}[next_level]

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=AUTOSERVICE_PHOTO,
        caption=(
            f"✅ <b>ДВИГАТЕЛЬ УР.{next_level} КУПЛЕН!</b>\n\n"
            f"⚡ Множитель скорости: ×{mult}\n"
            f"💰 -${price}\n\n"
            f"Теперь ты ездишь быстрее!"
        ),
        reply_markup=autoservice_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Улучшено!")


@router.callback_query(F.data == "autoservice_nitro")
async def autoservice_nitro(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)

    if not player.get("car"):
        await callback.answer("У тебя нет машины", show_alert=True)
        return

    if player.get("nitro", 0):
        await callback.answer("💨 Нитро уже установлено!", show_alert=True)
        return

    if player["balance"] < NITRO_PRICE:
        await callback.answer(f"💰 Нужно ${NITRO_PRICE}", show_alert=True)
        return

    await update_player(
        callback.from_user.id,
        balance=player["balance"] - NITRO_PRICE,
        nitro=1,
    )

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=AUTOSERVICE_PHOTO,
        caption=(
            f"✅ <b>НИТРО УСТАНОВЛЕНО!</b>\n\n"
            f"💨 Множитель скорости: ×0.7\n"
            f"💰 -${NITRO_PRICE}\n\n"
            f"Теперь ты ездишь ещё быстрее!"
        ),
        reply_markup=autoservice_back_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Установлено!")
