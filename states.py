from aiogram.fsm.state import State, StatesGroup


class Reg(StatesGroup):
    nickname = State()
    gender = State()
    faction = State()


class Bank(StatesGroup):
    topup = State()
    withdraw = State()
    transfer_account = State()
    transfer_amount = State()
    deposit = State()


class Casino(StatesGroup):
    dice_bet = State()
    slots_bet = State()


class Race(StatesGroup):
    bet = State()


class Admin(StatesGroup):
    find_user = State()
    give_money = State()
    set_level = State()
