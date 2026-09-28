from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    # Юзер
    waiting_for_bug = State()
    waiting_for_idea = State()

    # Ответ юзеру
    waiting_for_reply = State()

    # Блокировка
    waiting_for_block_reason = State()

    # Управление модерами
    waiting_for_add_mod = State()

    # Управление владельцами
    waiting_for_add_owner = State()

    # Блокировка от владельца
    waiting_for_owner_block_id = State()
    waiting_for_owner_block_reason = State()

    # Разблокировка
    waiting_for_unblock_id = State()

    # Рассылка
    waiting_for_broadcast = State()
