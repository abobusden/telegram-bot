import logging
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import (
    OWNER_ID, OWNER_IDS, SIGNATURE_MOD, SIGNATURE_OWNER,
    GREETING_OWNER, GREETING_MOD, GREETING_USER,
    TEXT_BUG_SENT, TEXT_IDEA_SENT, TEXT_BLOCKED
)
from keyboards import (
    user_menu, mod_menu, owner_menu, cancel_kb,
    ticket_actions, rating_kb,
    mod_block_time, owner_block_time,
    manage_mods_kb, del_mod_kb,
    manage_owners_kb, del_owner_kb,
    manage_blocks_kb, broadcast_confirm_kb,
    back_button
)
from states import Form
import database as db

router = Router()


# ================= ПОМОЩНИКИ =================

def role_of(user_id):
    if user_id in OWNER_IDS:
        return "owner"
    owners = [o["user_id"] for o in db.get_owners()]
    if user_id in owners:
        return "owner"
    if db.is_moderator(user_id):
        return "mod"
    return "user"


def is_blocked(user_id):
    return db.get_blocked(user_id) is not None


async def deny_if_blocked(message: Message):
    b = db.get_blocked(message.from_user.id)
    if not b:
        return False
    until = "навсегда" if b["until"] == "forever" else b["until"]
    who = "Владелец" if b["blocked_by_role"] == "owner" else "Модератор"
    await message.answer(TEXT_BLOCKED.format(
        reason=b["reason"], until=until, who=who
    ))
    return True


async def notify_mods_and_owner(bot: Bot, text: str, actions=None, photo_id=None):
    """Рассылка бага/идеи всем модерам + владельцам."""
    targets = set()
    for oid in OWNER_IDS:
        targets.add(oid)
    for m in db.get_moderators():
        targets.add(m["user_id"])
    for o in db.get_owners():
        targets.add(o["user_id"])

    for tid in targets:
        try:
            if photo_id:
                await bot.send_photo(tid, photo_id, caption=text, reply_markup=actions)
            else:
                await bot.send_message(tid, text, reply_markup=actions)
        except Exception as e:
            logging.warning(f"Не удалось отправить {tid}: {e}")


async def notify_owner(bot: Bot, text: str):
    for oid in OWNER_IDS:
        try:
            await bot.send_message(oid, text)
        except Exception as e:
            logging.warning(f"Не удалось уведомить владельца {oid}: {e}")


# ================= /start =================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    role = role_of(uid)

    if role == "owner":
        await message.answer(GREETING_OWNER + "\n\nВыбери действие:", reply_markup=owner_menu())
    elif role == "mod":
        await message.answer(
            GREETING_MOD.format(name=message.from_user.full_name) + "\n\nВыбери действие:",
            reply_markup=mod_menu()
        )
    else:
        await message.answer(
            GREETING_USER.format(name=message.from_user.full_name) + "\n\nВыбери действие:",
            reply_markup=user_menu()
        )


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"🆔 Твой ID: {message.from_user.id}")


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_start(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await cmd_start(callback.message, state)
    await callback.answer()


@router.message(F.text == "❌ Отмена")
async def cancel_message(message: Message, state: FSMContext):
    await state.clear()
    await cmd_start(message, state)


# ================= ОТПРАВКА БАГА =================

@router.callback_query(F.data == "bug")
async def ask_bug(callback: CallbackQuery, state: FSMContext):
    if await deny_if_blocked(callback.message):
        await callback.answer()
        return
    await callback.message.answer(
        "🐞 Опиши баг подробно:\n\n"
        "— Что ты делал?\n"
        "— Что ожидал?\n"
        "— Что произошло?\n\n"
        "📸 Можно приложить 1 скриншот.\n"
        "⚠️ Текст обязателен.\n\n"
        "Отправь текст и фото (если есть) одним сообщением.",
        reply_markup=cancel_kb()
    )
    await state.set_state(Form.waiting_for_bug)
    await callback.answer()


@router.message(Form.waiting_for_bug)
async def receive_bug(message: Message, state: FSMContext, bot: Bot):
    if not message.text and not message.caption:
        await message.answer("⚠️ Нужен текст описания. Отправь ещё раз.")
        return

    text = message.text or message.caption
    photo_id = message.photo[-1].file_id if message.photo else None

    ticket_id = db.create_ticket(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        "bug", text, photo_id
    )

    info = (
        f"🐞 <b>НОВЫЙ БАГ</b>\n\n"
        f"👤 От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"🎫 Тикет: #{ticket_id}\n\n"
        f"📝 {text}"
    )

    await notify_mods_and_owner(bot, info, ticket_actions(ticket_id), photo_id)
    await message.answer(TEXT_BUG_SENT)
    await state.clear()


# ================= ОТПРАВКА ИДЕИ =================

@router.callback_query(F.data == "idea")
async def ask_idea(callback: CallbackQuery, state: FSMContext):
    if await deny_if_blocked(callback.message):
        await callback.answer()
        return
    await callback.message.answer(
        "💡 Опиши свою идею для сервера Sky World.\n\n"
        "Чем подробнее — тем лучше!",
        reply_markup=cancel_kb()
    )
    await state.set_state(Form.waiting_for_idea)
    await callback.answer()


@router.message(Form.waiting_for_idea)
async def receive_idea(message: Message, state: FSMContext, bot: Bot):
    if message.photo:
        await message.answer("⚠️ К идее нельзя приложить фото. Опиши словами.")
        return
    if not message.text:
        await message.answer("⚠️ Отправь текст идеи.")
        return

    text = message.text
    ticket_id = db.create_ticket(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        "idea", text, None
    )

    info = (
        f"💡 <b>НОВАЯ ИДЕЯ</b>\n\n"
        f"👤 От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"🎫 Тикет: #{ticket_id}\n\n"
        f"📝 {text}"
    )

    await notify_mods_and_owner(bot, info, ticket_actions(ticket_id))
    await message.answer(TEXT_IDEA_SENT)
    await state.clear()
    # ================= ОТВЕТ ЮЗЕРУ =================

@router.callback_query(F.data.startswith("reply_"))
async def start_reply(callback: CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.split("_")[1])
    await state.update_data(ticket_id=ticket_id)
    await callback.message.answer(
        f"💬 Ответ на тикет #{ticket_id}\n\nНапиши текст ответа:",
        reply_markup=cancel_kb()
    )
    await state.set_state(Form.waiting_for_reply)
    await callback.answer()


@router.message(Form.waiting_for_reply)
async def send_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    ticket = db.get_ticket(ticket_id)

    if not ticket:
        await message.answer("⚠️ Тикет не найден.")
        await state.clear()
        return

    role = role_of(message.from_user.id)
    signature = SIGNATURE_OWNER if role == "owner" else SIGNATURE_MOD

    db.answer_ticket(ticket_id, message.text, message.from_user.id, role)

    user_text = (
        f"💬 <b>Ответ от поддержки:</b>\n\n"
        f"{message.text}\n\n"
        f"{signature}"
    )

    try:
        await bot.send_message(ticket["user_id"], user_text, reply_markup=rating_kb(ticket_id))
        await message.answer("✅ Ответ отправлен юзеру.")
    except Exception as e:
        logging.error(e)
        await message.answer("⚠️ Не удалось отправить ответ.")

    await state.clear()


# ================= ОЦЕНКА =================

@router.callback_query(F.data.startswith("rate_"))
async def rate_reply(callback: CallbackQuery):
    parts = callback.data.split("_")
    rating = "up" if parts[1] == "up" else "down"
    ticket_id = int(parts[2])
    ticket = db.get_ticket(ticket_id)

    if not ticket or not ticket["answered_by"]:
        await callback.answer("Уже оценено", show_alert=True)
        return

    db.add_rating(ticket_id, callback.from_user.id, ticket["answered_by"], rating)
    await callback.message.edit_reply_markup(reply_markup=None)

    if rating == "up":
        await callback.message.answer("✅ Спасибо за оценку!")
    else:
        await callback.message.answer("😔 Спасибо за честность. Мы станем лучше.")
        await notify_owner(
            callback.bot,
            f"👎 <b>НЕГАТИВНАЯ ОЦЕНКА</b>\n\n"
            f"🎫 Тикет: #{ticket_id}\n"
            f"👤 Юзер: {callback.from_user.full_name} (@{callback.from_user.username})"
        )
    await callback.answer()


# ================= МОИ ОБРАЩЕНИЯ =================

@router.callback_query(F.data == "my_tickets")
async def my_tickets(callback: CallbackQuery):
    rows = db.get_user_tickets(callback.from_user.id)
    if not rows:
        await callback.message.answer("📝 У тебя пока нет обращений.")
        await callback.answer()
        return

    lines = ["📝 <b>Мои обращения:</b>\n"]
    for r in rows[:10]:
        icon = "🐞" if r["type"] == "bug" else "💡"
        status = "✅ Отвечено" if r["status"] == "answered" else "⏳ На рассмотрении"
        text = (r["text"] or "")[:50]
        lines.append(f"{icon} #{r['id']} — {r['created_at']}\n«{text}...»\n{status}\n")

    await callback.message.answer("\n".join(lines))
    await callback.answer()


# ================= АКТИВНЫЕ ОБРАЩЕНИЯ (МОДЕР) =================

@router.callback_query(F.data == "active_tickets")
async def active_tickets(callback: CallbackQuery):
    rows = db.get_active_tickets()
    if not rows:
        await callback.message.answer("✅ Активных обращений нет.")
        await callback.answer()
        return

    lines = ["📋 <b>Активные обращения:</b>\n"]
    for r in rows:
        icon = "🐞" if r["type"] == "bug" else "💡"
        status = "⏳ Новое" if r["status"] == "new" else "👀 В работе"
        text = (r["text"] or "")[:40]
        uname = f"@{r['username']}" if r["username"] else r["user_id"]
        lines.append(f"{icon} #{r['id']} {uname} — {r['created_at']}\n«{text}»\n{status}\n")

    await callback.message.answer("\n".join(lines), reply_markup=back_button())
    await callback.answer()


# ================= БЛОКИРОВКА (МОДЕР) =================

@router.callback_query(F.data.startswith("block_"))
async def choose_block(callback: CallbackQuery):
    ticket_id = int(callback.data.split("_")[1])
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Тикет не найден", show_alert=True)
        return

    role = role_of(callback.from_user.id)
    if role == "mod":
        await callback.message.answer(
            f"🚫 Блокировка @{ticket['username']}\n\nНа сколько?",
            reply_markup=mod_block_time(ticket_id)
        )
    else:
        await callback.message.answer(
            f"🚫 Блокировка @{ticket['username']}\n\nНа сколько?",
            reply_markup=owner_block_time(ticket["user_id"])
        )
    await callback.answer()


@router.callback_query(F.data.startswith("modblock_"))
async def mod_block(callback: CallbackQuery, state: FSMContext):
    _, ticket_id, minutes = callback.data.split("_")
    ticket = db.get_ticket(int(ticket_id))
    if not ticket:
        await callback.answer("Тикет не найден", show_alert=True)
        return

    until = (datetime.now() + timedelta(minutes=int(minutes))).strftime("%d.%m.%Y %H:%M")
    await state.update_data(
        block_user_id=ticket["user_id"],
        block_until=until,
        block_minutes=int(minutes)
    )
    await callback.message.answer("📝 Напиши причину блокировки:", reply_markup=cancel_kb())
    await state.set_state(Form.waiting_for_block_reason)
    await callback.answer()


@router.callback_query(F.data.startswith("oblock_"))
async def owner_block_time_handler(callback: CallbackQuery, state: FSMContext):
    _, user_id, duration = callback.data.split("_")
    user_id = int(user_id)

    if duration == "forever":
        until = "forever"
    else:
        num = int(duration[:-1])
        unit = duration[-1]
        delta = {
            "m": timedelta(minutes=num),
            "h": timedelta(hours=num),
            "d": timedelta(days=num),
        }[unit]
        until = (datetime.now() + delta).strftime("%d.%m.%Y %H:%M")

    await state.update_data(block_user_id=user_id, block_until=until)
    await callback.message.answer("📝 Напиши причину блокировки:", reply_markup=cancel_kb())
    await state.set_state(Form.waiting_for_block_reason)
    await callback.answer()


@router.message(Form.waiting_for_block_reason)
async def do_block(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data["block_user_id"]
    until = data["block_until"]
    reason = message.text
    role = role_of(message.from_user.id)

    db.block_user(user_id, None, None, until, reason, message.from_user.id, role)

    try:
        who = "Владелец" if role == "owner" else "Модератор"
        until_str = "навсегда" if until == "forever" else until
        await bot.send_message(
            user_id,
            TEXT_BLOCKED.format(reason=reason, until=until_str, who=who)
        )
    except Exception:
        pass

    if role == "mod":
        await notify_owner(
            bot,
            f"🚫 <b>МОДЕР ЗАБЛОКИРОВАЛ ЮЗЕРА</b>\n\n"
            f"👮 Модер: @{message.from_user.username} — {message.from_user.id}\n"
            f"👤 Юзер ID: {user_id}\n"
            f"⏰ На: {'навсегда' if until == 'forever' else until}\n"
            f"📝 Причина: {reason}"
        )

    await message.answer(
        f"✅ Пользователь {user_id} заблокирован.\n"
        f"📝 Причина: {reason}"
    )
    await state.clear()


@router.callback_query(F.data == "owner_block")
async def owner_block_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🚫 Введи ID юзера для блокировки:", reply_markup=cancel_kb())
    await state.set_state(Form.waiting_for_owner_block_id)
    await callback.answer()


@router.message(Form.waiting_for_owner_block_id)
async def owner_block_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ ID должен быть числом.")
        return
    await state.update_data(block_user_id=uid)
    await message.answer(
        "На сколько заблокировать?",
        reply_markup=owner_block_time(uid)
    )
    await state.set_state(None)


# ================= РАЗБЛОКИРОВКА =================

@router.callback_query(F.data == "owner_unblock")
async def unblock_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🔓 Введи ID для разблокировки:", reply_markup=cancel_kb())
    await state.set_state(Form.waiting_for_unblock_id)
    await callback.answer()


@router.message(Command("unblock"))
@router.message(Form.waiting_for_unblock_id)
async def do_unblock(message: Message, state: FSMContext, bot: Bot):
    text = message.text
    if text.startswith("/unblock"):
        parts = text.split()
        if len(parts) < 2:
            await message.answer("⚠️ /unblock <ID>")
            return
        try:
            uid = int(parts[1])
        except ValueError:
            await message.answer("⚠️ ID должен быть числом.")
            return
    else:
        try:
            uid = int(text.strip())
        except ValueError:
            await message.answer("⚠️ ID должен быть числом.")
            return

    role = role_of(message.from_user.id)
    db.unblock_user(uid, message.from_user.id, role)

    try:
        await bot.send_message(uid, "✅ Вы разблокированы!")
    except Exception:
        pass

    if role == "mod":
        await notify_owner(
            bot,
            f"🔓 <b>МОДЕР РАЗБЛОКИРОВАЛ ЮЗЕРА</b>\n\n"
            f"👮 Модер: @{message.from_user.username} — {message.from_user.id}\n"
            f"👤 Юзер ID: {uid}"
        )

    await message.answer(f"✅ Пользователь {uid} разблокирован.")
    await state.clear()


# ================= МОЯ СТАТИСТИКА =================

@router.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    uid = callback.from_user.id
    s = db.get_mod_stats(uid)
    up, down = db.get_mod_ratings(uid)
    total_ratings = up + down
    percent = round(up / total_ratings * 100) if total_ratings else 0

    stars = "⭐" * min(5, max(1, percent // 20))
    label = "Отличный" if percent >= 90 else "Хороший" if percent >= 75 else "Средний"

    text = (
        f"📊 <b>МОЯ СТАТИСТИКА</b>\n\n"
        f"👤 {callback.from_user.full_name} (@{callback.from_user.username})\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📥 <b>ОБРАБОТАНО: {s['total']}</b>\n"
        f"🐞 Багов: {s['bugs']}\n"
        f"💡 Идей: {s['ideas']}\n\n"
        f"💬 Ответов: {s['total']}\n"
        f"👍 Полезных: {up} ({percent}%)\n"
        f"👎 Неполезных: {down}\n\n"
        f"🚫 Блокировок: {s['blocks']}\n"
        f"🔓 Разблокировок: {s['unblocks']}\n\n"
        f"📈 Рейтинг: {stars} {label}"
    )
    await callback.message.answer(text, reply_markup=back_button())
    await callback.answer()


@router.callback_query(F.data == "my_history")
async def my_history(callback: CallbackQuery):
    conn = db.get_conn()
    rows = conn.execute(
        "SELECT * FROM history WHERE by_id = ? ORDER BY id DESC LIMIT 20",
        (callback.from_user.id,)
    ).fetchall()
    conn.close()

    if not rows:
        await callback.message.answer("📜 История пуста.", reply_markup=back_button())
        await callback.answer()
        return

    lines = ["📜 <b>Моя история:</b>\n"]
    for r in rows:
        icon = "🚫" if r["action"] == "block" else "🔓"
        act = "заблокировал" if r["action"] == "block" else "разблокировал"
        lines.append(f"{icon} Я {act} юзера {r['user_id']}\n🕐 {r['created_at']}\n")

    await callback.message.answer("\n".join(lines), reply_markup=back_button())
    await callback.answer()
    # ================= УПРАВЛЕНИЕ МОДЕРАМИ =================

@router.callback_query(F.data == "manage_mods")
async def manage_mods(callback: CallbackQuery):
    mods = db.get_moderators()
    owners = db.get_owners()

    lines = ["🛡 <b>Управление модераторами</b>\n"]
    lines.append(f"👑 Владельцы ({len(OWNER_IDS) + len(owners)}):")
    for oid in OWNER_IDS:
        lines.append(f"• {oid}")
    for o in owners:
        uname = f"@{o['username']}" if o["username"] else ""
        lines.append(f"• {o['full_name']} {uname} — {o['user_id']}")

    lines.append(f"\n🛡 Модераторы ({len(mods)}):")
    if not mods:
        lines.append("• Пока нет")
    for m in mods:
        uname = f"@{m['username']}" if m["username"] else ""
        lines.append(f"• {m['full_name']} {uname} — {m['user_id']}")

    await callback.message.answer("\n".join(lines), reply_markup=manage_mods_kb())
    await callback.answer()


@router.callback_query(F.data == "add_mod")
async def add_mod_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "➕ <b>Добавление модера</b>\n\n"
        "Отправь ID пользователя.\n\n"
        "⚠️ Он должен уже нажать /start у бота.",
        reply_markup=cancel_kb()
    )
    await state.set_state(Form.waiting_for_add_mod)
    await callback.answer()


@router.message(Form.waiting_for_add_mod)
async def add_mod_save(message: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ ID должен быть числом.")
        return

    if db.is_moderator(uid):
        await message.answer("⚠️ Уже модер.")
        await state.clear()
        return

    username = None
    full_name = None
    try:
        chat = await bot.get_chat(uid)
        username = chat.username
        full_name = chat.full_name
    except Exception:
        pass

    db.add_moderator(uid, username, full_name, message.from_user.id)
    await message.answer(f"✅ Модератор {uid} добавлен.")

    try:
        await bot.send_message(uid, "🛡 Тебя назначили модератором Sky World!\n\nНапиши /start.")
    except Exception:
        pass

    await state.clear()
    await manage_mods(message)


@router.callback_query(F.data == "del_mod")
async def del_mod_list(callback: CallbackQuery):
    mods = db.get_moderators()
    if not mods:
        await callback.message.answer("Нет модеров.", reply_markup=manage_mods_kb())
    else:
        await callback.message.answer("Выбери, кого убрать:", reply_markup=del_mod_kb(mods))
    await callback.answer()


@router.callback_query(F.data.startswith("delmod_"))
async def del_mod_do(callback: CallbackQuery, bot: Bot):
    uid = int(callback.data.split("_")[1])
    db.remove_moderator(uid)
    await callback.message.answer(f"✅ Модератор {uid} удалён.")
    try:
        await bot.send_message(uid, "🛡 Тебя сняли с должности модератора.")
    except Exception:
        pass
    await callback.answer()


# ================= УПРАВЛЕНИЕ ВЛАДЕЛЬЦАМИ =================

@router.callback_query(F.data == "manage_owners")
async def manage_owners(callback: CallbackQuery):
    owners = db.get_owners()
    lines = ["👑 <b>Управление владельцами</b>\n"]
    lines.append(f"👑 Владельцы ({len(OWNER_IDS) + len(owners)}):")
    for oid in OWNER_IDS:
        lines.append(f"• {oid}")
    for o in owners:
        uname = f"@{o['username']}" if o["username"] else ""
        lines.append(f"• {o['full_name']} {uname} — {o['user_id']}")

    await callback.message.answer("\n".join(lines), reply_markup=manage_owners_kb())
    await callback.answer()


@router.callback_query(F.data == "add_owner")
async def add_owner_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "➕ <b>Добавление совладельца</b>\n\n"
        "Отправь ID пользователя.\n\n"
        "⚠️ Он получит ВСЕ права владельца.",
        reply_markup=cancel_kb()
    )
    await state.set_state(Form.waiting_for_add_owner)
    await callback.answer()


@router.message(Form.waiting_for_add_owner)
async def add_owner_save(message: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ ID должен быть числом.")
        return

    username = None
    full_name = None
    try:
        chat = await bot.get_chat(uid)
        username = chat.username
        full_name = chat.full_name
    except Exception:
        pass

    db.add_owner(uid, username, full_name, message.from_user.id)
    await message.answer(f"✅ Совладелец {uid} добавлен.")

    try:
        await bot.send_message(uid, "👑 Тебя назначили совладельцем Sky World!\n\nНапиши /start.")
    except Exception:
        pass

    await state.clear()
    await manage_owners(message)


@router.callback_query(F.data == "del_owner")
async def del_owner_list(callback: CallbackQuery):
    owners = db.get_owners()
    if not owners:
        await callback.message.answer("Нет совладельцев.", reply_markup=manage_owners_kb())
    else:
        await callback.message.answer(
            "Выбери, кого убрать:",
            reply_markup=del_owner_kb(owners, callback.from_user.id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("delowner_"))
async def del_owner_do(callback: CallbackQuery, bot: Bot):
    uid = int(callback.data.split("_")[1])
    if uid in OWNER_IDS:
        await callback.answer("❌ Нельзя удалить главного владельца.", show_alert=True)
        return
    db.remove_owner(uid)
    await callback.message.answer(f"✅ Совладелец {uid} удалён.")
    try:
        await bot.send_message(uid, "👑 Тебя сняли с должности совладельца.")
    except Exception:
        pass
    await callback.answer()


# ================= УПРАВЛЕНИЕ БЛОКИРОВКАМИ =================

@router.callback_query(F.data == "manage_blocks")
async def manage_blocks(callback: CallbackQuery):
    rows = db.get_all_blocked()
    lines = ["🚫 <b>Управление блокировками</b>\n"]

    if not rows:
        lines.append("Активных блокировок нет.")
    else:
        lines.append(f"Активные блокировки ({len(rows)}):")
        for r in rows[:15]:
            until = "навсегда" if r["until"] == "forever" else r["until"]
            uname = f"@{r['username']}" if r["username"] else str(r["user_id"])
            lines.append(f"• {uname} — до {until} ({r['reason']})")

    await callback.message.answer("\n".join(lines), reply_markup=manage_blocks_kb())
    await callback.answer()


# ================= ИСТОРИЯ (ВСЯ) =================

@router.callback_query(F.data == "all_history")
async def all_history(callback: CallbackQuery):
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()

    if not rows:
        await callback.message.answer("📜 История пуста.", reply_markup=back_button())
        await callback.answer()
        return

    lines = ["📜 <b>История наказаний:</b>\n"]
    for r in rows:
        icon = "🚫" if r["action"] == "block" else "🔓"
        act = "заблокировал" if r["action"] == "block" else "разблокировал"
        role = "👑 Владелец" if r["by_role"] == "owner" else "🛡 Модер"
        extra = f" | ⏰ {r['duration']}" if r["action"] == "block" else ""
        reason = f" | 📝 {r['reason']}" if r["reason"] else ""
        lines.append(
            f"{icon} {role} {act} юзера {r['user_id']}\n"
            f"🕐 {r['created_at']}{extra}{reason}\n"
        )

    await callback.message.answer("\n".join(lines), reply_markup=back_button())
    await callback.answer()


# ================= ОЦЕНКИ МОДЕРОВ =================

@router.callback_query(F.data == "mod_ratings")
async def mod_ratings(callback: CallbackQuery):
    mods = db.get_moderators()
    if not mods:
        await callback.message.answer("Модеров нет.", reply_markup=back_button())
        await callback.answer()
        return

    lines = ["📊 <b>Оценки модеров:</b>\n"]
    for m in mods:
        up, down = db.get_mod_ratings(m["user_id"])
        total = up + down
        pct = round(up / total * 100) if total else 0
        uname = f"@{m['username']}" if m["username"] else m["user_id"]
        lines.append(f"🛡 {uname}:\n👍 {up} / 👎 {down} ({pct}%)\n")

    await callback.message.answer("\n".join(lines), reply_markup=back_button())
    await callback.answer()


# ================= СТАТИСТИКА БОТА =================

@router.callback_query(F.data == "bot_stats")
async def bot_stats(callback: CallbackQuery):
    s = db.get_bot_stats()
    mods_count = len(db.get_moderators())
    owners_count = len(OWNER_IDS) + len(db.get_owners())

    text = (
        f"📊 <b>СТАТИСТИКА SKY WORLD</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Юзеров: {s['users']}\n"
        f"🛡 Модеров: {mods_count}\n"
        f"👑 Владельцев: {owners_count}\n\n"
        f"📥 Обращений: {s['bugs'] + s['ideas']}\n"
        f"🐞 Багов: {s['bugs']}\n"
        f"💡 Идей: {s['ideas']}\n"
        f"✅ Закрыто: {s['closed']}\n"
        f"⏳ В работе: {s['active']}\n\n"
        f"🚫 Блокировок: {s['blocks']}"
    )
    await callback.message.answer(text, reply_markup=back_button())
    await callback.answer()


# ================= РАССЫЛКА =================

@router.callback_query(F.data == "broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📢 <b>Рассылка</b>\n\n"
        "Отправь текст, который разошлём всем юзерам.\n"
        "⚠️ Можно с фото (1 шт).",
        reply_markup=cancel_kb()
    )
    await state.set_state(Form.waiting_for_broadcast)
    await callback.answer()


@router.message(Form.waiting_for_broadcast)
async def broadcast_preview(message: Message, state: FSMContext):
    text = message.text or message.caption
    photo_id = message.photo[-1].file_id if message.photo else None

    if not text:
        await message.answer("⚠️ Нужен текст.")
        return

    await state.update_data(bc_text=text, bc_photo=photo_id)

    preview = f"📢 <b>Проверь сообщение:</b>\n\n{text}\n\nРазослать всем?"
    await message.answer(preview, reply_markup=broadcast_confirm_kb())
    await state.set_state(None)


@router.callback_query(F.data == "broadcast_send")
async def broadcast_do(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    text = data.get("bc_text")
    photo = data.get("bc_photo")

    conn = db.get_conn()
    users = conn.execute("SELECT DISTINCT user_id FROM tickets").fetchall()
    conn.close()

    sent = 0
    errors = 0
    for u in users:
        try:
            if photo:
                await bot.send_photo(u["user_id"], photo, caption=text)
            else:
                await bot.send_message(u["user_id"], text)
            sent += 1
        except Exception:
            errors += 1

    await callback.message.answer(f"✅ Рассылка завершена.\n✅ Доставлено: {sent}\n❌ Ошибок: {errors}")
    await state.clear()
    await callback.answer()
