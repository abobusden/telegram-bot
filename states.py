from aiogram.fsm.state import State, StatesGroup


class Reg(StatesGroup):
    nickname = State()
    gender = State()
    faction = State()
