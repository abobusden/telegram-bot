@router.callback_query(F.data == "death_heal")
async def death_heal(callback: CallbackQuery):
    player = await get_player(callback.from_user.id)
    if not player:
        await callback.answer("Сначала зарегистрируйся")
        return

    if player["hp"] > 0:
        await callback.answer("Ты ещё жив!", show_alert=True)
        return

    if player["balance"] < 500:
        await callback.answer("💰 Нужно $500", show_alert=True)
        return

    await update_player(
        callback.from_user.id,
        balance=player["balance"] - 500,
        hp=100,
    )

    death_waiting.pop(callback.from_user.id, None)

    await callback.message.delete()
    await callback.message.answer(
        f"🏥 <b>ПРОЛЕЧЕН!</b>\n\n"
        f"❤️ HP: 100/100\n"
        f"💰 -$500\n\n"
        f"Ты снова в строю!",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Пролечен!")
