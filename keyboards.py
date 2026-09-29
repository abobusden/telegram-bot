from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)


# ================= ГЛАВНЫЕ МЕНЮ =================

def user_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐞 Сообщить о баге", callback_data="bug")],
        [InlineKeyboardButton(text="💡 Предложить идею", callback_data="idea")],
        [InlineKeyboardButton(text="📝 Мои обращения", callback_data="my_tickets")],
    ])


def mod_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐞 Сообщить о баге", callback_data="bug")],
        [InlineKeyboardButton(text="💡 Предложить идею", callback_data="idea")],
        [InlineKeyboardButton(text="📋 Активные обращения", callback_data="active_tickets")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📜 Моя история", callback_data="my_history")],
    ])


def owner_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐞 Сообщить о баге", callback_data="bug")],
        [InlineKeyboardButton(text="💡 Предложить идею", callback_data="idea")],
        [InlineKeyboardButton(text="📋 Активные обращения", callback_data="active_tickets")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📜 Моя история", callback_data="my_history")],
        [InlineKeyboardButton(text="🛡 Управление модерами", callback_data="manage_mods")],
        [InlineKeyboardButton(text="👑 Управление владельцами", callback_data="manage_owners")],
        [InlineKeyboardButton(text="🚫 Управление блокировками", callback_data="manage_blocks")],
        [InlineKeyboardButton(text="📜 История наказаний", callback_data="all_history")],
        [InlineKeyboardButton(text="📊 Оценки модеров", callback_data="mod_ratings")],
        [InlineKeyboardButton(text="📊 Статистика бота", callback_data="bot_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")],
    ])


# ================= ПОДПИСКА НА КАНАЛЫ =================

def subscribe_kb():
    from config import CHANNELS
    buttons = []
    for ch in CHANNELS:
        buttons.append([InlineKeyboardButton(text=f"📢 {ch['name']}", url=ch["link"])])
    buttons.append([InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ================= ОТМЕНА =================

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


# ================= ОБРАЩЕНИЕ =================

def ticket_actions(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{ticket_id}")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_{ticket_id}")],
    ])


def rating_kb(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Да", callback_data=f"rate_up_{ticket_id}"),
            InlineKeyboardButton(text="👎 Нет", callback_data=f"rate_down_{ticket_id}"),
        ]
    ])


# ================= БЛОКИРОВКА (МОДЕР) =================

def mod_block_time(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 минут", callback_data=f"modblock_{ticket_id}_10")],
        [InlineKeyboardButton(text="30 минут", callback_data=f"modblock_{ticket_id}_30")],
        [InlineKeyboardButton(text="1 час", callback_data=f"modblock_{ticket_id}_60")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")],
    ])


# ================= БЛОКИРОВКА (ВЛАДЕЛЕЦ) =================

def owner_block_time(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 минут", callback_data=f"oblock_{user_id}_10m")],
        [InlineKeyboardButton(text="30 минут", callback_data=f"oblock_{user_id}_30m")],
        [InlineKeyboardButton(text="1 час", callback_data=f"oblock_{user_id}_1h")],
        [InlineKeyboardButton(text="6 часов", callback_data=f"oblock_{user_id}_6h")],
        [InlineKeyboardButton(text="1 день", callback_data=f"oblock_{user_id}_1d")],
        [InlineKeyboardButton(text="7 дней", callback_data=f"oblock_{user_id}_7d")],
        [InlineKeyboardButton(text="30 дней", callback_data=f"oblock_{user_id}_30d")],
        [InlineKeyboardButton(text="♾ Навсегда", callback_data=f"oblock_{user_id}_forever")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")],
    ])


# ================= УПРАВЛЕНИЕ МОДЕРАМИ =================

def manage_mods_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить модера", callback_data="add_mod")],
        [InlineKeyboardButton(text="➖ Удалить модера", callback_data="del_mod")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="manage_mods")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])


def del_mod_kb(mods):
    buttons = []
    for m in mods:
        name = m["full_name"] or "Без имени"
        uname = f"@{m['username']}" if m["username"] else ""
        text = f"🗑 {name} {uname} — {m['user_id']}".strip()
        buttons.append([InlineKeyboardButton(text=text[:60], callback_data=f"delmod_{m['user_id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="manage_mods")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ================= УПРАВЛЕНИЕ ВЛАДЕЛЬЦАМИ =================

def manage_owners_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить владельца", callback_data="add_owner")],
        [InlineKeyboardButton(text="➖ Убрать владельца", callback_data="del_owner")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])


def del_owner_kb(owners, self_id):
    buttons = []
    for o in owners:
        if o["user_id"] == self_id:
            continue
        name = o["full_name"] or "Без имени"
        uname = f"@{o['username']}" if o["username"] else ""
        text = f"🗑 {name} {uname} — {o['user_id']}".strip()
        buttons.append([InlineKeyboardButton(text=text[:60], callback_data=f"delowner_{o['user_id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="manage_owners")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ================= УПРАВЛЕНИЕ БЛОКИРОВКАМИ =================

def manage_blocks_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Заблокировать юзера", callback_data="owner_block")],
        [InlineKeyboardButton(text="🔓 Разблокировать юзера", callback_data="owner_unblock")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])


# ================= РАССЫЛКА =================

def broadcast_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_send")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")],
    ])


# ================= УНИВЕРСАЛЬНОЕ =================

def back_button(callback="back_to_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback)]
    ])
