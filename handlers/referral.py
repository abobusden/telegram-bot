# ============================================
# РЕФЕРАЛКА
# ============================================

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import get_player, update_player, get_referrals
from keyboards import referral_menu_kb, back_to_referral_kb


router = Router()

REFERRAL_BONUS_ME = 500
REFERRAL_BONUS_FRIEND = 500

BOT_USERNAME = "GTA_CrimeBot"


@router.callback_query(F.data == "referral_menu")
async def referral_menu(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    link = f"https://t.me/{BOT_USERNAME}?start=ref_{callback.from_user.id}"
    count = player.get("referral_count", 0) or 0
    earned = count * REFERRAL_BONUS_ME

    await callback.message.edit_text(
        f"🎁 <b>РЕФЕРАЛЫ</b>\n\n"
        f"Приглашай друзей и получай деньги!\n\n"
        f"💰 Тебе: <b>${REFERRAL_BONUS_ME}</b>\n"
        f"🎁 Другу: <b>${REFERRAL_BONUS_FRIEND}</b>\n\n"
        f"🔗 Твоя ссылка:\n"
        f"<code>{link}</code>\n\n"
        f"👥 Приглашено: <b>{count}</b>\n"
        f"💵 Заработано: <b>${earned:,}</b>",
        reply_markup=referral_menu_kb(link),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "referral_list")
async def referral_list(callback: CallbackQuery):
    referrals = await get_referrals(callback.from_user.id)

    text = "👥 <b>ТВОИ РЕФЕРАЛЫ</b>\n\n"

    if not referrals:
        text += "Пока никого нет.\n"
    else:
        for i, p in enumerate(referrals, 1):
            text += f"{i}. {p['nickname']} — Ур.{p['level']}\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_referral_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "referral_back")
async def referral_back(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{callback.from_user.id}"
    count = player.get("referral_count", 0) or 0
    earned = count * REFERRAL_BONUS_ME

    await callback.message.edit_text(
        f"🎁 <b>РЕФЕРАЛЫ</b>\n\n"
        f"Приглашай друзей и получай деньги!\n\n"
        f"💰 Тебе: <b>${REFERRAL_BONUS_ME}</b>\n"
        f"🎁 Другу: <b>${REFERRAL_BONUS_FRIEND}</b>\n\n"
        f"🔗 Твоя ссылка:\n"
        f"<code>{link}</code>\n\n"
        f"👥 Приглашено: <b>{count}</b>\n"
        f"💵 Заработано: <b>${earned:,}</b>",
        reply_markup=referral_menu_kb(link),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
