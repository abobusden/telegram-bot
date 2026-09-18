from aiogram.fsm.state import State, StatesGroup


class Reg(StatesGroup):
    nickname = State()
    gender = State()
    faction = State()


class Bank(StatesGroup):
    topup = State()                # пополнение счёта
    withdraw = State()             # снятие со счёта
    transfer_account = State()     # ввод счёта получателя
    transfer_amount = State()      # ввод суммы перевода
    deposit = State()              # ввод суммы вклада
