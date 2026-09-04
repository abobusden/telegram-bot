import os
import json
import time
import random
from threading import Thread
from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8609399059:AAH1VPl7e9LLPb3zIQ4g7sCtD8yZPtK12-c"
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "players.json"
CLANS_FILE = "clans.json"
MOVE_TIMEOUT = 30
ADMIN_ID = 6236795210

players = {}
clans = {}
queue = []
raid_queue = []          
active_raid = None       
raid_cooldowns = {}      
battle_timers = {}
casino_messages = {}

RANKS = {
    1: "Новичок",
    2: "Ученик",
    3: "Боец",
    4: "Ветеран",
    5: "Мастер",
    6: "Герой",
    7: "Легенда",
    8: "Истребитель",
    9: "Дракон",
    10: "Абсолют"
}

MAX_UPGRADE_LEVEL = 10

DAILY_QUESTS_POOL = {
    'pvp_play': {'name': 'Сыграть в PvP', 'target': 1, 'coins': 20, 'xp': 15},
    'pvp_win': {'name': 'Выиграть в PvP', 'target': 1, 'coins': 30, 'xp': 20},
    'raid_play': {'name': 'Сыграть в режим рейд', 'target': 1, 'coins': 25, 'xp': 20},
    'potion_use': {'name': 'Использовать зелье здоровья', 'target': 1, 'coins': 15, 'xp': 10},
    'raid_top': {'name': 'Войти в топ 1-2 в рейде', 'target': 1, 'coins': 40, 'xp': 30}
}

WEEKLY_QUESTS = {
    'wk_dmg_500': {'name': 'Нанести суммарно 500 урона Тирану', 'target': 500, 'coins': 150, 'xp': 100},
    'wk_raid_3': {'name': 'Поучаствовать в 3 рейдах', 'target': 3, 'coins': 100, 'xp': 80},
    'wk_dmg_1000': {'name': 'Нанести суммарно 1000 урона Тирану', 'target': 1000, 'coins': 300, 'xp': 200},
    'wk_raid_5': {'name': 'Поучаствовать в 5 рейдах', 'target': 5, 'coins': 180, 'xp': 120},
    'wk_raid_10': {'name': 'Поучаствовать в 10 рейдах', 'target': 10, 'coins': 400, 'xp': 300}
}

TOWER_ENEMIES = {
    1: {'name': 'Слизневик', 'hp': 60, 'dmg': (10, 15), 'coins': 15, 'xp': 10},
    2: {'name': 'Гоблин-воин', 'hp': 90, 'dmg': (15, 20), 'coins': 25, 'xp': 15},
    3: {'name': 'Орк-берсерк', 'hp': 130, 'dmg': (20, 25), 'coins': 40, 'xp': 25},
    4: {'name': 'Скелет-рыцарь', 'hp': 180, 'dmg': (25, 30), 'coins': 60, 'xp': 35},
    5: {'name': 'Тролль', 'hp': 250, 'dmg': (30, 40), 'coins': 80, 'xp': 50},
    6: {'name': 'Темный маг', 'hp': 300, 'dmg': (40, 50), 'coins': 100, 'xp': 60},
    7: {'name': 'Вампир', 'hp': 400, 'dmg': (45, 55), 'coins': 130, 'xp': 75},
    8: {'name': 'Голем', 'hp': 550, 'dmg': (50, 65), 'coins': 160, 'xp': 90},
    9: {'name': 'Демон', 'hp': 750, 'dmg': (60, 75), 'coins': 200, 'xp': 120},
    10: {'name': 'Владыка Бездны', 'hp': 1000, 'dmg': (70, 90), 'coins': 300, 'xp': 200}
}

def save_players_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(players, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_players_data():
    global players
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                players = {int(k): v for k, v in raw_data.items()}
                for uid in players:
                    players[uid]['opponent'] = None
                    players[uid]['in_tower'] = False
                    players[uid]['is_defending'] = False
                    players[uid]['is_turn'] = False
        except Exception:
            players = {}

def save_clans_data():
    try:
        with open(CLANS_FILE, "w", encoding="utf-8") as f:
            json.dump(clans, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_clans_data():
    global clans
    if os.path.exists(CLANS_FILE):
        try:
            with open(CLANS_FILE, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                clans = {k: v for k, v in raw_data.items()}
        except Exception:
            clans = {}

load_players_data()
load_clans_data()

def reset_inactivity_timer(user_id):
    battle_timers[user_id] = time.time()

def check_inactivity_loop():
    while True:
        time.sleep(5)
        current_time = time.time()
        for uid in list(players.keys()):
            p = players.get(uid)
            if p and p.get('opponent') is not None and p.get('is_turn'):
                last_move = battle_timers.get(uid, current_time)
                if current_time - last_move > MOVE_TIMEOUT:
                    opponent_id = p['opponent']
                    bot.send_message(uid, "⏱️ Вы слишком долго думали и пропустили время хода! Засчитано поражение по таймауту.", reply_markup=get_main_menu(uid))
                    bot.send_message(opponent_id, "⏱️ Противник превысил лимит времени на ход! Вам присуждена победа!", reply_markup=get_main_menu(opponent_id))
                    end_battle(winner_id=opponent_id, loser_id=uid)

t_inactivity = Thread(target=check_inactivity_loop, daemon=True)
t_inactivity.start()

def check_and_reset_quests(user_id):
    if user_id not in players or 'quests' not in players[user_id]:
        return
    q_data = players[user_id]['quests']
    current_time = time.time()
    changed = False
    if current_time >= q_data['daily_reset']:
        q_data['daily_reset'] = current_time + 86400
        q_data['daily_active'] = random.sample(list(DAILY_QUESTS_POOL.keys()), 3)
        q_data['daily_progress'] = {q: 0 for q in q_data['daily_active']}
        q_data['daily_claimed'] = {q: False for q in q_data['daily_active']}
        changed = True
    if current_time >= q_data['weekly_reset']:
        q_data['weekly_reset'] = current_time + 604800
        q_data['weekly_progress'] = {q: 0 for q in WEEKLY_QUESTS.keys()}
        q_data['weekly_claimed'] = {q: False for q in WEEKLY_QUESTS.keys()}
        changed = True
    if changed:
        save_players_data()

def progress_quest(user_id, q_type, amount=1):
    if user_id not in players or 'quests' not in players[user_id]:
        return
    check_and_reset_quests(user_id)
    q_data = players[user_id]['quests']
    changed = False
    if q_type in q_data['daily_active']:
        current = q_data['daily_progress'][q_type]
        target = DAILY_QUESTS_POOL[q_type]['target']
        if current < target:
            q_data['daily_progress'][q_type] = min(target, current + amount)
            changed = True
    if q_type in WEEKLY_QUESTS:
        current = q_data['weekly_progress'].get(q_type, 0)
        target = WEEKLY_QUESTS[q_type]['target']
        if current < target:
            q_data['weekly_progress'][q_type] = min(target, current + amount)
            changed = True
    if changed:
        save_players_data()

def init_user(user_id, name, username=None):
    if user_id not in players:
        players[user_id] = {
            'name': name,
            'username': username or name,
            'hp': 100,
            'max_hp': 100,
            'opponent': None,
            'is_defending': False,
            'is_turn': False,
            'inventory': ['Зелье лечения', 'Зелье лечения'],
            'level': 1,
            'xp': 0,
            'coins': 100,
            'wins': 0,
            'losses': 0,
            'up_dmg': 0,    
            'up_hp': 0,
            'tower_floor': 1,
            'in_tower': False,
            'tower_enemy_hp': 0,
            'clan': None,
            'muted_until': 0,
            'banned': False
        }
    else:
        players[user_id]['name'] = name
        if username:
            players[user_id]['username'] = username
        for key, default in [('level', 1), ('xp', 0), ('coins', 0), ('wins', 0), ('losses', 0), ('up_dmg', 0), ('up_hp', 0), ('tower_floor', 1), ('in_tower', False), ('tower_enemy_hp', 0), ('clan', None), ('muted_until', 0), ('banned', False)]:
            if key not in players[user_id]:
                players[user_id][key] = default

    if 'quests' not in players[user_id]:
        players[user_id]['quests'] = {
            'daily_reset': time.time() + 86400,
            'weekly_reset': time.time() + 604800,
            'daily_active': random.sample(list(DAILY_QUESTS_POOL.keys()), 3),
            'daily_progress': {},
            'daily_claimed': {},
            'weekly_progress': {},
            'weekly_claimed': {}
        }
        for q in players[user_id]['quests']['daily_active']:
            players[user_id]['quests']['daily_progress'][q] = 0
            players[user_id]['quests']['daily_claimed'][q] = False
        for q in WEEKLY_QUESTS.keys():
            players[user_id]['quests']['weekly_progress'][q] = 0
            players[user_id]['quests']['weekly_claimed'][q] = False
            
    check_and_reset_quests(user_id)
    save_players_data()

def add_xp_and_coins(user_id, xp_gain, coins_gain):
    p = players[user_id]
    p['coins'] += coins_gain
    if p['level'] >= 10:
        p['xp'] = 100
        save_players_data()
        return False
    p['xp'] += xp_gain
    leveled_up = False
    while p['xp'] >= 100 and p['level'] < 10:
        p['xp'] -= 100
        p['level'] += 1
        p['max_hp'] += 10 + (p['up_hp'] * 5)
        p['hp'] = p['max_hp']
        leveled_up = True
    if p['level'] == 10 and p['xp'] > 100:
        p['xp'] = 100
    save_players_data()
    return leveled_up

def get_progress_bar(xp):
    percent = min(100, max(0, xp))
    filled = percent // 10
    empty = 10 - filled
    return "█" * filled + "░" * empty + f" {percent}%"

def get_main_menu(user_id=None):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("В бой!"),
        KeyboardButton("🦖 Рейд на Тирана"),
        KeyboardButton("🗼 Башня"),
        KeyboardButton("⚡ Прокачка"),
        KeyboardButton("📜 Квесты"),
        KeyboardButton("➡️ Вперед")
    )
    if user_id and user_id == ADMIN_ID:
        markup.add(KeyboardButton("👑 Админ-панель"))
    return markup

def get_second_menu(user_id=None):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("Инвентарь"),
        KeyboardButton("🎲 Казино"),
        KeyboardButton("🛡️ Клан"),
        KeyboardButton("👤 Профиль"),
        KeyboardButton("🏆 Топ"),
        KeyboardButton("⬅️ Назад")
    )
    if user_id and user_id == ADMIN_ID:
        markup.add(KeyboardButton("👑 Админ-панель"))
    return markup

def get_battle_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("Атака"),
        KeyboardButton("Защита"),
        KeyboardButton("Инвентарь"),
        KeyboardButton("🏳️ Сдаться")
    )
    return markup

def get_raid_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("⚔️ Ударить Тирана"),
        KeyboardButton("Инвентарь")
    )
    return markup

def get_inventory_menu(inventory):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for item in set(inventory):
        count = inventory.count(item)
        markup.add(KeyboardButton(f"Использовать: {item} ({count})"))
    markup.add(KeyboardButton("Назад"))
    return markup

def generate_quests_ui(user_id):
    check_and_reset_quests(user_id)
    q_data = players[user_id]['quests']
    daily_tl = max(0, int(q_data['daily_reset'] - time.time()))
    weekly_tl = max(0, int(q_data['weekly_reset'] - time.time()))
    d_h, d_m = divmod(daily_tl // 60, 60)
    w_d, w_h = divmod(weekly_tl // 3600, 24)
    text = f"📜 <b>КВЕСТЫ</b>\n\n"
    text += f"🌞 <b>Ежедневные</b> (Сброс через {d_h} ч. {d_m} мин.)\n"
    markup = InlineKeyboardMarkup(row_width=1)
    for idx, q_key in enumerate(q_data['daily_active'], 1):
        q_info = DAILY_QUESTS_POOL[q_key]
        prog = q_data['daily_progress'].get(q_key, 0)
        claimed = q_data['daily_claimed'].get(q_key, False)
        status = "✅ Выполнено" if claimed else f"⏳ {prog}/{q_info['target']}"
        text += f"{idx}. {q_info['name']}\n   Награда: {q_info['coins']} 💰 | {q_info['xp']} XP\n   Прогресс: {status}\n\n"
        if prog >= q_info['target'] and not claimed:
            markup.add(InlineKeyboardButton(f"🎁 Награда: {q_info['name']}", callback_data=f"quest:daily:{q_key}"))
    text += f"🗓️ <b>Еженедельные</b> (Сброс через {w_d} дн. {w_h} ч.)\n"
    for idx, q_key in enumerate(WEEKLY_QUESTS.keys(), 1):
        q_info = WEEKLY_QUESTS[q_key]
        prog = q_data['weekly_progress'].get(q_key, 0)
        claimed = q_data['weekly_claimed'].get(q_key, False)
        status = "✅ Выполнено" if claimed else f"⏳ {prog}/{q_info['target']}"
        text += f"{idx}. {q_info['name']}\n   Награда: {q_info['coins']} 💰 | {q_info['xp']} XP\n   Прогресс: {status}\n\n"
        if prog >= q_info['target'] and not claimed:
            short_name = q_info['name'][:20] + "..." if len(q_info['name']) > 20 else q_info['name']
            markup.add(InlineKeyboardButton(f"🎁 Награда: {short_name}", callback_data=f"quest:weekly:{q_key}"))
    markup.add(InlineKeyboardButton("🔄 Обновить задания", callback_data="quest_refresh"))
    return text, markup

def generate_leaderboard(lb_type='rank', page=1):
    all_players = list(players.values())
    if lb_type == 'rank':
        sorted_p = sorted(all_players, key=lambda x: (x['level'], x['xp'], x['wins']), reverse=True)
        title = "🏆 Таблица лидеров по рангу\n\n"
    else:
        sorted_p = sorted(all_players, key=lambda x: (x['wins'], x['level']), reverse=True)
        title = "⚔️ Таблица лидеров по победам\n\n"
    per_page = 5
    total_players = len(sorted_p)
    total_pages = max(1, (total_players + per_page - 1) // per_page)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_players = sorted_p[start_idx:end_idx]
    text = title
    if not sorted_p:
        text += "Игроков пока нет."
    else:
        medals = ["🥇", "🥈", "🥉"]
        for idx, p in enumerate(page_players, start=start_idx + 1):
            icon = medals[idx - 1] if idx <= 3 else f"{idx}."
            rank_name = RANKS.get(p['level'], "Абсолют")
            uname = f"@{p['username']}" if p.get('username') else p['name']
            if lb_type == 'rank':
                text += f"{icon} {uname} — 🔥 {rank_name} ({p['level']} ур., {p['xp']} XP)\n"
            else:
                text += f"{icon} {uname} — 🏆 {p['wins']} побед ({p['level']} ур.)\n"
    markup = InlineKeyboardMarkup()
    btn_rank = InlineKeyboardButton("🔥 По рангу" if lb_type != 'rank' else "▶️ По рангу ◀️", callback_data="top:rank:1")
    btn_wins = InlineKeyboardButton("🏆 По победам" if lb_type != 'wins' else "▶️ По победам ◀️", callback_data="top:wins:1")
    markup.row(btn_rank, btn_wins)
    prev_page = page - 1 if page > 1 else total_pages
    next_page = page + 1 if page < total_pages else 1
    btn_prev = InlineKeyboardButton("⬅️ Назад", callback_data=f"top:{lb_type}:{prev_page}")
    btn_page = InlineKeyboardButton(f"Стр. {page}/{total_pages}", callback_data="ignore")
    btn_next = InlineKeyboardButton("Вперед ➡️", callback_data=f"top:{lb_type}:{next_page}")
    markup.row(btn_prev, btn_page, btn_next)
    return text, markup

def end_battle(winner_id, loser_id):
    players[winner_id]['wins'] += 1
    players[loser_id]['losses'] += 1
    progress_quest(winner_id, 'pvp_play', 1)
    progress_quest(winner_id, 'pvp_win', 1)
    progress_quest(loser_id, 'pvp_play', 1)
    leveled_up = add_xp_and_coins(winner_id, 10, 20)
    for uid in (winner_id, loser_id):
        players[uid]['opponent'] = None
        players[uid]['hp'] = players[uid]['max_hp']
        players[uid]['is_defending'] = False
        players[uid]['is_turn'] = False
        battle_timers.pop(uid, None)
    save_players_data()
    win_msg = "🏆 Вы победили!\nНаграда: +10 XP, +20 монет 💰\nЗдоровье восстановлено."
    if leveled_up:
        new_lvl = players[winner_id]['level']
        new_rank = RANKS.get(new_lvl, "Абсолют")
        win_msg += f"\n\n🎉 ПОЗДРАВЛЯЕМ! Вы повысили уровень до {new_lvl} ({new_rank})!"
    bot.send_message(winner_id, win_msg, reply_markup=get_main_menu(winner_id))
    bot.send_message(loser_id, "☠️ Вы проиграли!\nЗдоровье восстановлено.", reply_markup=get_main_menu(loser_id))

@bot.message_handler(commands=['start'])
def start_game(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'):
        bot.send_message(user_id, "❌ Ваш аккаунт заблокирован администратором.")
        return
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! Готов к сражениям?",
        reply_markup=get_main_menu(user_id)
    )

@bot.message_handler(func=lambda message: message.text == "➡️ Вперед")
def go_forward(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    bot.send_message(user_id, "Дополнительное меню:", reply_markup=get_second_menu(user_id))

@bot.message_handler(func=lambda message: message.text == "⬅️ Назад")
def go_back(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    bot.send_message(user_id, "Главное меню:", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.text == "🎲 Казино")
def casino_menu(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'):
        return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎲 Кости", callback_data="casino:dice_menu"),
        InlineKeyboardButton("💣 Мины 4x3", callback_data="casino:mines_menu")
    )
    bot.send_message(user_id, f"🎲 <b>КАЗИНО</b>\n\nУ вас монет: 💰 {players[user_id]['coins']}\nВыберите игру:", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("casino:"))
def casino_callback(call):
    user_id = call.from_user.id
    init_user(user_id, call.from_user.first_name, call.from_user.username)
    parts = call.data.split(":")
    action = parts[1]

    if action == "dice_menu":
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("10 💰", callback_data="casino:dice_bet:10"),
            InlineKeyboardButton("50 💰", callback_data="casino:dice_bet:50"),
            InlineKeyboardButton("100 💰", callback_data="casino:dice_bet:100"),
            InlineKeyboardButton("500 💰", callback_data="casino:dice_bet:500"),
            InlineKeyboardButton("1000 💰", callback_data="casino:dice_bet:1000"),
            InlineKeyboardButton("🔙 Назад", callback_data="casino:main")
        )
        try:
            bot.edit_message_text("🎲 <b>КОСТИ</b>\n\nСделайте ставку. Если ваша сумма броска кубиков будет больше или равна сумме бота, вы выиграете x2!", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif action == "dice_bet":
        bet = int(parts[2])
        if players[user_id]['coins'] < bet:
            bot.answer_callback_query(call.id, "Не хватает монет для ставки!", show_alert=True)
            return
        players[user_id]['coins'] -= bet
        user_roll = random.randint(1, 6) + random.randint(1, 6)
        bot_roll = random.randint(1, 6) + random.randint(1, 6)
        
        text = f"🎲 <b>КОСТИ</b> (Ставка: {bet} 💰)\n\nВаш бросок: {user_roll}\nБросок бота: {bot_roll}\n\n"
        if user_roll >= bot_roll:
            win_amount = bet * 2
            players[user_id]['coins'] += win_amount
            text += f"🎉 Вы победили и выиграли {win_amount} 💰!"
        else:
            text += f"😢 Вы проиграли ставку."
        
        save_players_data()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎲 Снова", callback_data="casino:dice_menu"), InlineKeyboardButton("🔙 В казино", callback_data="casino:main"))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif action == "mines_menu":
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("10 💰", callback_data="casino:mines_bet:10"),
            InlineKeyboardButton("50 💰", callback_data="casino:mines_bet:50"),
            InlineKeyboardButton("100 💰", callback_data="casino:mines_bet:100"),
            InlineKeyboardButton("🔙 Назад", callback_data="casino:main")
        )
        try:
            bot.edit_message_text("💣 <b>МИНЫ (4x3)</b>\n\nНа поле 12 клеток (4 ряда по 3), запрятаны 3 мины. Открывайте безопасные клетки, увеличивая коэффициент победы!", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif action == "mines_bet":
        bet = int(parts[2])
        if players[user_id]['coins'] < bet:
            bot.answer_callback_query(call.id, "Не хватает монет для ставки!", show_alert=True)
            return
        players[user_id]['coins'] -= bet
        save_players_data()
        
        mines = random.sample(range(12), 3)
        casino_messages[user_id] = {
            'game': 'mines',
            'bet': bet,
            'mines': mines,
            'revealed': [],
            'mult': 1.0
        }
        text, markup = get_mines_board_ui(user_id)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif action == "mines_step":
        cell_idx = int(parts[2])
        game_data = casino_messages.get(user_id)
        if not game_data or game_data['game'] != 'mines':
            bot.answer_callback_query(call.id, "Игра не найдена.", show_alert=True)
            return
        if cell_idx in game_data['revealed']:
            bot.answer_callback_query(call.id, "Клетка уже открыта!")
            return
            
        if cell_idx in game_data['mines']:
            text = f"💣 Вы подорвались на мине!\nСтавка {game_data['bet']} 💰 сгорела."
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("💣 Снова", callback_data=f"casino:mines_bet:{game_data['bet']}"), InlineKeyboardButton("🔙 В казино", callback_data="casino:main"))
            casino_messages.pop(user_id, None)
            try:
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
            except Exception:
                pass
            bot.answer_callback_query(call.id, "Вы проиграли!", show_alert=True)
        else:
            game_data['revealed'].append(cell_idx)
            game_data['mult'] += 0.3
            if len(game_data['revealed']) >= (12 - 3):
                win_val = int(game_data['bet'] * game_data['mult'])
                players[user_id]['coins'] += win_val
                save_players_data()
                text = f"🏆 Поздравляем! Вы открыли все безопасные клетки и выиграли {win_val} 💰 (Коэф: x{round(game_data['mult'], 1)})!"
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("💣 Снова", callback_data=f"casino:mines_bet:{game_data['bet']}"), InlineKeyboardButton("🔙 В казино", callback_data="casino:main"))
                casino_messages.pop(user_id, None)
                try:
                    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
                except Exception:
                    pass
                bot.answer_callback_query(call.id, "Победа!", show_alert=True)
            else:
                text, markup = get_mines_board_ui(user_id)
                try:
                    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
                except Exception:
                    pass
                bot.answer_callback_query(call.id)

    elif action == "mines_cashout":
        game_data = casino_messages.get(user_id)
        if not game_data or game_data['game'] != 'mines':
            bot.answer_callback_query(call.id, "Игра не найдена.", show_alert=True)
            return
        win_val = int(game_data['bet'] * game_data['mult'])
        players[user_id]['coins'] += win_val
        save_players_data()
        text = f"💰 Вы успешно забрали выигрыш: {win_val} 💰 (Коэф: x{round(game_data['mult'], 1)})!"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💣 Снова", callback_data=f"casino:mines_bet:{game_data['bet']}"), InlineKeyboardButton("🔙 В казино", callback_data="casino:main"))
        casino_messages.pop(user_id, None)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif action == "main":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🎲 Кости", callback_data="casino:dice_menu"),
            InlineKeyboardButton("💣 Мины 4x3", callback_data="casino:mines_menu")
        )
        try:
            bot.edit_message_text(f"🎲 <b>КАЗИНО</b>\n\nУ вас монет: 💰 {players[user_id]['coins']}\nВыберите игру:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

def get_mines_board_ui(user_id):
    game_data = casino_messages[user_id]
    text = f"💣 <b>МИНЫ (4x3)</b>\nСтавка: {game_data['bet']} 💰 | Текущий коэф: x{round(game_data['mult'], 1)}\nВыберите клетку:"
    markup = InlineKeyboardMarkup(row_width=3)
    row_buttons = []
    for i in range(12):
        if i in game_data['revealed']:
            btn = InlineKeyboardButton("✅", callback_data="ignore")
        else:
            btn = InlineKeyboardButton(f"❓ {i+1}", callback_data=f"casino:mines_step:{i}")
        row_buttons.append(btn)
        if len(row_buttons) == 3:
            markup.row(*row_buttons)
            row_buttons = []
    markup.add(InlineKeyboardButton(f"💰 Забрать ({int(game_data['bet'] * game_data['mult'])} 💰)", callback_data="casino:mines_cashout"))
    return text, markup

@bot.message_handler(func=lambda message: message.text in ["🛡️ Клан", "Клан"])
def clan_menu(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'):
        return
    p = players[user_id]
    
    if p['clan']:
        clan_name = p['clan']
        c_data = clans.get(clan_name, {})
        members = c_data.get('members', [])
        is_leader = (c_data.get('leader') == user_id)
        
        text = f"🛡️ <b>КЛАН: {clan_name}</b>\nУчастников: {len(members)}\nВаша роль: {'👑 Глава' + (' | Команда /clan_delete для роспуска' if is_leader else '')}\n\nСписок участников:\n"
        for m_id in members:
            m_p = players.get(m_id)
            m_name = f"@{m_p['username']}" if m_p and m_p.get('username') else str(m_id)
            text += f"- {m_name}\n"
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚪 Выйти из клана", callback_data="clan:leave"))
        if is_leader:
            markup.add(InlineKeyboardButton("❌ Распустить клан", callback_data="clan:delete"))
        bot.send_message(user_id, text, reply_markup=markup, parse_mode="HTML")
    else:
        if p['level'] < 5:
            bot.send_message(user_id, "🛡️ Для управления или вступления в клан требуется минимум 5-й уровень!")
        else:
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("🏗️ Создать клан (150 💰)", callback_data="clan:create_menu"),
                InlineKeyboardButton("📜 Список кланов", callback_data="clan:list:1")
            )
            bot.send_message(user_id, "🛡️ <b>КЛАНОВАЯ СИСТЕМА</b>\n\nВы не состоите в клане.", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("clan:"))
def clan_callback(call):
    user_id = call.from_user.id
    init_user(user_id, call.from_user.first_name, call.from_user.username)
    parts = call.data.split(":")
    action = parts[1]

    if action == "create_menu":
        if players[user_id]['level'] < 5:
            bot.answer_callback_query(call.id, "Нужен 5-й уровень!", show_alert=True)
            return
        if players[user_id]['coins'] < 150:
            bot.answer_callback_query(call.id, "Не хватает монет для создания клана (150 💰)!", show_alert=True)
            return
        bot.send_message(user_id, "Введите название для вашего клана следующим сообщением (одним словом или через пробел):")
        bot.answer_callback_query(call.id)
        players[user_id]['awaiting_clan_name'] = True

    elif action == "list":
        page = int(parts[2]) if len(parts) > 2 else 1
        all_clans = list(clans.keys())
        per_page = 5
        total_pages = max(1, (len(all_clans) + per_page - 1) // per_page)
        if page < 1: page = 1
        if page > total_pages: page = total_pages
        
        text = f"🛡️ <b>СПИСОК КЛАНОВ</b> (Стр. {page}/{total_pages})\n\n"
        markup = InlineKeyboardMarkup()
        page_clans = all_clans[(page-1)*per_page : page*per_page]
        for c_name in page_clans:
            c_members = len(clans[c_name]['members'])
            text += f"- <b>{c_name}</b> ({c_members} уч.)\n"
            markup.add(InlineKeyboardButton(f"📥 Вступить в {c_name}", callback_data=f"clan:join:{c_name}"))
            
        btn_prev = InlineKeyboardButton("⬅️ Назад", callback_data=f"clan:list:{page-1}")
        btn_next = InlineKeyboardButton("Вперед ➡️", callback_data=f"clan:list:{page+1}")
        markup.row(btn_prev, btn_next)
        markup.add(InlineKeyboardButton("🔙 В меню кланов", callback_data="clan:main"))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif action == "join":
        c_name = parts[2]
        if players[user_id]['level'] < 5:
            bot.answer_callback_query(call.id, "Нужен 5-й уровень!", show_alert=True)
            return
        if players[user_id]['clan']:
            bot.answer_callback_query(call.id, "Вы уже состоите в клане!", show_alert=True)
            return
        if c_name not in clans:
            bot.answer_callback_query(call.id, "Клан не найден.", show_alert=True)
            return
        clans[c_name]['members'].append(user_id)
        players[user_id]['clan'] = c_name
        save_clans_data()
        save_players_data()
        bot.answer_callback_query(call.id, f"Вы успешно вступили в клан {c_name}!", show_alert=True)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

    elif action == "leave":
        c_name = players[user_id]['clan']
        if not c_name or c_name not in clans:
            bot.answer_callback_query(call.id, "Вы не в клане.", show_alert=True)
            return
        if clans[c_name]['leader'] == user_id:
            bot.answer_callback_query(call.id, "Лидер не может выйти, распустите клан.", show_alert=True)
            return
        clans[c_name]['members'].remove(user_id)
        players[user_id]['clan'] = None
        save_clans_data()
        save_players_data()
        bot.answer_callback_query(call.id, "Вы вышли из клана.", show_alert=True)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

    elif action == "delete":
        c_name = players[user_id]['clan']
        if not c_name or c_name not in clans or clans[c_name]['leader'] != user_id:
            bot.answer_callback_query(call.id, "Вы не лидер клана.", show_alert=True)
            return
        for m_id in clans[c_name]['members']:
            if m_id in players:
                players[m_id]['clan'] = None
        del clans[c_name]
        save_clans_data()
        save_players_data()
        bot.answer_callback_query(call.id, "Клан распущен.", show_alert=True)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

    elif action == "main":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🏗️ Создать клан (150 💰)", callback_data="clan:create_menu"),
            InlineKeyboardButton("📜 Список кланов", callback_data="clan:list:1")
        )
        try:
            bot.edit_message_text("🛡️ <b>КЛАНОВАЯ СИСТЕМА</b>\n\nВы не состоите в клане.", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: players.get(message.chat.id, {}).get('awaiting_clan_name'))
def create_clan_process(message):
    user_id = message.chat.id
    players[user_id]['awaiting_clan_name'] = False
    c_name = message.text.strip()
    if len(c_name) < 3 or len(c_name) > 20:
        bot.send_message(user_id, "Название клана должно быть от 3 до 20 символов.")
        return
    if c_name in clans:
        bot.send_message(user_id, "Клан с таким названием уже существует.")
        return
    if players[user_id]['coins'] < 150:
        bot.send_message(user_id, "Не хватает монет.")
        return
    players[user_id]['coins'] -= 150
    players[user_id]['clan'] = c_name
    clans[c_name] = {
        'leader': user_id,
        'members': [user_id]
    }
    save_clans_data()
    save_players_data()
    bot.send_message(user_id, f"🛡️ Клан <b>{c_name}</b> успешно создан!", parse_mode="HTML", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.text in ["👑 Админ-панель", "Админ-панель"])
def admin_panel_menu(message):
    user_id = message.chat.id
    if user_id != ADMIN_ID:
        return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin:stats"),
        InlineKeyboardButton("📢 Рассылка", callback_data="admin:broadcast"),
        InlineKeyboardButton("🔍 Найти игрока", callback_data="admin:search")
    )
    bot.send_message(user_id, "👑 <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\nВыберите действие или используйте /ahelp для справки.", reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=['ahelp'])
def admin_help_command(message):
    user_id = message.chat.id
    if user_id != ADMIN_ID:
        return
    help_text = (
        "👑 <b>СПРАВКА ПО АДМИН-КОМАНДАМ</b>\n\n"
        "• <b>/setcoins [username/id] [кол-во]</b> — установить монеты\n"
        "• <b>/addcoins [username/id] [кол-во]</b> — выдать монеты\n"
        "• <b>/setxp [username/id] [кол-во]</b> — установить опыт\n"
        "• <b>/setlvl [username/id] [уровень]</b> — установить уровень\n"
        "• <b>/giveitem [username/id] [предмет]</b> — выдать предмет\n"
        "• <b>/reset [username/id]</b> — сбросить прогресс\n"
        "• <b>/ban [username/id]</b> — забанить игрока\n"
        "• <b>/unban [username/id]</b> — разбанить игрока\n"
        "• <b>/mute [username/id] [минуты]</b> — выдать мут\n"
        "• <b>/unmute [username/id]</b> — снять мут\n"
        "• <b>/stats</b> — общая статистика бота\n"
        "• <b>/broadcast [текст]</b> — глобальная рассылка\n"
    )
    bot.send_message(user_id, help_text, parse_mode="HTML")

def resolve_user_target(target_str):
    target_str = str(target_str).strip()
    if target_str.isdigit():
        uid = int(target_str)
        if uid in players:
            return uid
    if target_str.startswith('@'):
        target_str = target_str[1:]
    for uid, p in players.items():
        if p.get('username', '').lower() == target_str.lower() or p.get('name', '').lower() == target_str.lower():
            return uid
    return None

@bot.message_handler(commands=['setcoins'])
def cmd_setcoins(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    players[uid]['coins'] = int(args[2])
    save_players_data()
    bot.send_message(message.chat.id, f"Успешно! Монеты игрока обновлены.")

@bot.message_handler(commands=['addcoins'])
def cmd_addcoins(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    players[uid]['coins'] += int(args[2])
    save_players_data()
    bot.send_message(message.chat.id, f"Успешно! Монеты добавлены.")

@bot.message_handler(commands=['setxp'])
def cmd_setxp(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    players[uid]['xp'] = int(args[2])
    save_players_data()
    bot.send_message(message.chat.id, f"Успешно! Опыт обновлен.")

@bot.message_handler(commands=['setlvl'])
def cmd_setlvl(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    lvl = int(args[2])
    players[uid]['level'] = lvl
    players[uid]['max_hp'] = 100 + (lvl - 1) * 15 + (players[uid]['up_hp'] * 5)
    players[uid]['hp'] = players[uid]['max_hp']
    save_players_data()
    bot.send_message(message.chat.id, f"Успешно! Уровень установлен.")

@bot.message_handler(commands=['giveitem'])
def cmd_giveitem(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    item_name = args[2]
    players[uid]['inventory'].append(item_name)
    save_players_data()
    bot.send_message(message.chat.id, f"Предмет выдал.")

@bot.message_handler(commands=['reset'])
def cmd_reset(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    name = players[uid]['name']
    username = players[uid]['username']
    players[uid] = {
        'name': name,
        'username': username,
        'hp': 100,
        'max_hp': 100,
        'opponent': None,
        'is_defending': False,
        'is_turn': False,
        'inventory': ['Зелье лечения', 'Зелье лечения'],
        'level': 1,
        'xp': 0,
        'coins': 100,
        'wins': 0,
        'losses': 0,
        'up_dmg': 0,
        'up_hp': 0,
        'tower_floor': 1,
        'in_tower': False,
        'tower_enemy_hp': 0,
        'clan': None,
        'muted_until': 0,
        'banned': False
    }
    save_players_data()
    bot.send_message(message.chat.id, f"Прогресс аккаунта сброшен.")

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    players[uid]['banned'] = True
    save_players_data()
    bot.send_message(message.chat.id, f"Игрок заблокирован.")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    players[uid]['banned'] = False
    save_players_data()
    bot.send_message(message.chat.id, f"Игрок разблокирован.")

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    mins = int(args[2])
    players[uid]['muted_until'] = time.time() + (mins * 60)
    save_players_data()
    bot.send_message(message.chat.id, f"Мут выдан на {mins} минут.")

@bot.message_handler(commands=['unmute'])
def cmd_unmute(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    uid = resolve_user_target(args[1])
    if not uid:
        bot.send_message(message.chat.id, "Игрок не найден.")
        return
    players[uid]['muted_until'] = 0
    save_players_data()
    bot.send_message(message.chat.id, f"Мут снят.")

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if message.from_user.id != ADMIN_ID: return
    total_users = len(players)
    total_clans = len(clans)
    total_coins = sum(p.get('coins', 0) for p in players.values())
    text = f"📊 <b>СТАТИСТИКА БОТА</b>\n\nИгроков в базе: {total_users}\nКланов в базе: {total_clans}\nВсего монет на руках: {total_coins}"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.send_message(message.chat.id, "Введите текст рассылки.")
        return
    count = 0
    for uid in list(players.keys()):
        try:
            bot.send_message(uid, f"📢 <b>ОБЪЯВЛЕНИЕ АДМИНИСТРАЦИИ</b>\n\n{text}", parse_mode="HTML")
            count += 1
        except Exception:
            pass
    bot.send_message(message.chat.id, f"Рассылка завершена. Успешно отправлено: {count} пользователям.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin:"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    action = call.data.split(":")[1]
    if action == "stats":
        total_users = len(players)
        total_clans = len(clans)
        total_coins = sum(p.get('coins', 0) for p in players.values())
        text = f"📊 <b>СТАТИСТИКА БОТА</b>\n\nИгроков в базе: {total_users}\nКланов в базе: {total_clans}\nВсего монет на руках: {total_coins}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")
    elif action == "broadcast":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Используйте команду /broadcast [текст сообщения] для рассылки.")
    elif action == "search":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Введите username или ID игрока следующим сообщением, а затем используйте команды управления через /ahelp.")

@bot.message_handler(func=lambda message: message.text in ["📜 Квесты", "Квесты"])
def show_quests_menu(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    text, markup = generate_quests_ui(user_id)
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("quest:"))
def handle_quest_claim(call):
    user_id = call.from_user.id
    parts = call.data.split(":")
    if len(parts) == 3:
        q_cat = parts[1]
        q_key = parts[2]
        check_and_reset_quests(user_id)
        q_data = players[user_id]['quests']
        if q_cat == 'daily' and q_key in q_data['daily_active']:
            if q_data['daily_progress'].get(q_key, 0) >= DAILY_QUESTS_POOL[q_key]['target'] and not q_data['daily_claimed'].get(q_key, False):
                q_data['daily_claimed'][q_key] = True
                add_xp_and_coins(user_id, DAILY_QUESTS_POOL[q_key]['xp'], DAILY_QUESTS_POOL[q_key]['coins'])
                bot.answer_callback_query(call.id, f"Награда получена! +{DAILY_QUESTS_POOL[q_key]['coins']} 💰, +{DAILY_QUESTS_POOL[q_key]['xp']} XP", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "Квест еще не выполнен или уже собран!")
        elif q_cat == 'weekly' and q_key in WEEKLY_QUESTS:
            if q_data['weekly_progress'].get(q_key, 0) >= WEEKLY_QUESTS[q_key]['target'] and not q_data['weekly_claimed'].get(q_key, False):
                q_data['weekly_claimed'][q_key] = True
                add_xp_and_coins(user_id, WEEKLY_QUESTS[q_key]['xp'], WEEKLY_QUESTS[q_key]['coins'])
                bot.answer_callback_query(call.id, f"Награда получена! +{WEEKLY_QUESTS[q_key]['coins']} 💰, +{WEEKLY_QUESTS[q_key]['xp']} XP", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "Квест еще не выполнен или уже собран!")
    text, markup = generate_quests_ui(user_id)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "quest_refresh")
def handle_quest_refresh(call):
    user_id = call.from_user.id
    text, markup = generate_quests_ui(user_id)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        bot.answer_callback_query(call.id, "Квесты обновлены!")
    except Exception:
        bot.answer_callback_query(call.id, "Нет новых изменений.")

@bot.message_handler(func=lambda message: message.text in ["👤 Профиль", "Профиль"])
def show_profile(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    p = players[user_id]
    rank_name = RANKS.get(p['level'], "Абсолют")
    username_str = f"@{p['username']}" if p.get('username') else p['name']
    if p['level'] >= 10:
        xp_str = "MAX"
        progress_str = "██████████ 100%"
        left_str = "Достигнут максимальный ранг!"
    else:
        xp_str = f"{p['xp']} / 100"
        progress_str = get_progress_bar(p['xp'])
        left_str = f"осталось {100 - p['xp']} XP"
    profile_text = (
        f"Игрок: {username_str}\n"
        f"Ранг: 🔥 {rank_name} ({p['level']} уровень)\n"
        f"Клан: {p['clan'] if p['clan'] else 'Отсутствует'}\n"
        f"Макс. HP: {p['max_hp']} (Улучшений: {p['up_hp']}/{MAX_UPGRADE_LEVEL})\n"
        f"Сила атаки бонус: +{p['up_dmg'] * 3} (Улучшений: {p['up_dmg']}/{MAX_UPGRADE_LEVEL})\n"
        f"Монеты: 💰 {p['coins']}\n"
        f"Победы: {p['wins']} | Поражения: {p['losses']}\n"
        f"Текущий этаж Башни: 🗼 {p['tower_floor']}\n"
        f"Опыт: {xp_str}\n"
        f"Прогресс: {progress_str}\n"
        f"До следующего ранга: {left_str}"
    )
    bot.send_message(user_id, profile_text, reply_markup=get_second_menu(user_id))

@bot.message_handler(func=lambda message: message.text and "Прокачка" in message.text)
def show_upgrades(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    p = players[user_id]
    text = f"⚡ Меню прокачки характеристик\nУ вас монет: 💰 {p['coins']}\n\n"
    if p['up_dmg'] >= MAX_UPGRADE_LEVEL:
        text += f"1. 💪 Сила удара (Уровень: {p['up_dmg']}/{MAX_UPGRADE_LEVEL} - MAX)\n"
        text += "   Увеличивает урон в боях и рейдах.\n\n"
    else:
        cost_dmg = (p['up_dmg'] + 1) * 25
        text += f"1. 💪 Сила удара (Уровень: {p['up_dmg']}/{MAX_UPGRADE_LEVEL})\n"
        text += "   Увеличивает урон в боях и рейдах.\n"
        text += f"   Цена апгрейда: {cost_dmg} монет\n\n"
    if p['up_hp'] >= MAX_UPGRADE_LEVEL:
        text += f"2. 🛡️ Закалка здоровья (Уровень: {p['up_hp']}/{MAX_UPGRADE_LEVEL} - MAX)\n"
        text += "   Увеличивает максимальное HP (+15 за уровень).\n"
    else:
        cost_hp = (p['up_hp'] + 1) * 20
        text += f"2. 🛡️ Закалка здоровья (Уровень: {p['up_hp']}/{MAX_UPGRADE_LEVEL})\n"
        text += "   Увеличивает максимальное HP (+15 за уровень).\n"
        text += f"   Цена апгрейда: {cost_hp} монет\n"
    markup = InlineKeyboardMarkup(row_width=1)
    if p['up_dmg'] < MAX_UPGRADE_LEVEL:
        markup.add(InlineKeyboardButton(f"💪 Улучшить урон ({(p['up_dmg'] + 1) * 25} 💰)", callback_data="up:dmg"))
    if p['up_hp'] < MAX_UPGRADE_LEVEL:
        markup.add(InlineKeyboardButton(f"🛡️ Улучшить HP ({(p['up_hp'] + 1) * 20} 💰)", callback_data="up:hp"))
    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("up:"))
def handle_upgrade_callback(call):
    user_id = call.from_user.id
    init_user(user_id, call.from_user.first_name, call.from_user.username)
    p = players[user_id]
    action = call.data.split(":")[1]
    if action == "dmg":
        if p['up_dmg'] >= MAX_UPGRADE_LEVEL:
            bot.answer_callback_query(call.id, "Достигнут максимальный уровень!", show_alert=True)
        else:
            cost = (p['up_dmg'] + 1) * 25
            if p['coins'] >= cost:
                p['coins'] -= cost
                p['up_dmg'] += 1
                save_players_data()
                bot.answer_callback_query(call.id, f"Успешно! Сила удара повышена (Ур. {p['up_dmg']})")
            else:
                bot.answer_callback_query(call.id, "Не хватает монет!", show_alert=True)
                return
    elif action == "hp":
        if p['up_hp'] >= MAX_UPGRADE_LEVEL:
            bot.answer_callback_query(call.id, "Достигнут максимальный уровень!", show_alert=True)
        else:
            cost = (p['up_hp'] + 1) * 20
            if p['coins'] >= cost:
                p['coins'] -= cost
                p['up_hp'] += 1
                p['max_hp'] += 15
                p['hp'] = min(p['max_hp'], p['hp'] + 15)
                save_players_data()
                bot.answer_callback_query(call.id, f"Успешно! Здоровье повышено (Ур. {p['up_hp']})")
            else:
                bot.answer_callback_query(call.id, "Не хватает монет!", show_alert=True)
                return
    text = f"⚡ Меню прокачки характеристик\nУ вас монет: 💰 {p['coins']}\n\n"
    if p['up_dmg'] >= MAX_UPGRADE_LEVEL:
        text += f"1. 💪 Сила удара (Уровень: {p['up_dmg']}/{MAX_UPGRADE_LEVEL} - MAX)\n"
        text += "   Увеличивает урон в боях и рейдах.\n\n"
    else:
        cost_dmg = (p['up_dmg'] + 1) * 25
        text += f"1. 💪 Сила удара (Уровень: {p['up_dmg']}/{MAX_UPGRADE_LEVEL})\n"
        text += "   Увеличивает урон в боях и рейдах.\n"
        text += f"   Цена апгрейда: {cost_dmg} монет\n\n"
    if p['up_hp'] >= MAX_UPGRADE_LEVEL:
        text += f"2. 🛡️ Закалка здоровья (Уровень: {p['up_hp']}/{MAX_UPGRADE_LEVEL} - MAX)\n"
        text += "   Увеличивает максимальное HP (+15 за уровень).\n"
    else:
        cost_hp = (p['up_hp'] + 1) * 20
        text += f"2. 🛡️ Закалка здоровья (Уровень: {p['up_hp']}/{MAX_UPGRADE_LEVEL})\n"
        text += "   Увеличивает максимальное HP (+15 за уровень).\n"
        text += f"   Цена апгрейда: {cost_hp} монет\n"
    markup = InlineKeyboardMarkup(row_width=1)
    if p['up_dmg'] < MAX_UPGRADE_LEVEL:
        markup.add(InlineKeyboardButton(f"💪 Улучшить урон ({(p['up_dmg'] + 1) * 25} 💰)", callback_data="up:dmg"))
    if p['up_hp'] < MAX_UPGRADE_LEVEL:
        markup.add(InlineKeyboardButton(f"🛡️ Улучшить HP ({(p['up_hp'] + 1) * 20} 💰)", callback_data="up:hp"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

@bot.message_handler(func=lambda message: message.text in ["🏆 Топ", "Топ"])
def show_top(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    text, markup = generate_leaderboard('rank', 1)
    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("top:"))
def handle_top_callback(call):
    parts = call.data.split(":")
    lb_type = parts[1]
    page = int(parts[2])
    text, markup = generate_leaderboard(lb_type, page)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ignore")
def handle_ignore_callback(call):
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text in ["🗼 Башня", "Башня"])
def enter_tower(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    floor = players[user_id]['tower_floor']
    if floor > len(TOWER_ENEMIES):
        bot.send_message(user_id, "🏆 Вы прошли все этажи Башни испытаний! Поздравляем!", reply_markup=get_main_menu(user_id))
        return
    enemy = TOWER_ENEMIES[floor]
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("⚔️ Штурмовать этаж"),
        KeyboardButton("Назад")
    )
    text = (
        f"🗼 <b>БАШНЯ ИСПЫТАНИЙ</b>\n\n"
        f"Текущий этаж: {floor} из {len(TOWER_ENEMIES)}\n"
        f"Противник: <b>{enemy['name']}</b>\n"
        f"❤️ Здоровье: {enemy['hp']}\n"
        f"⚔️ Урон: {enemy['dmg'][0]}-{enemy['dmg'][1]}\n\n"
        f"Награда за победу: {enemy['coins']} 💰 | {enemy['xp']} XP"
    )
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "⚔️ Штурмовать этаж")
def start_tower_battle(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    if players[user_id]['opponent'] is not None or user_id in raid_queue:
        bot.send_message(user_id, "Вы не можете начать этаж, пока ищете другой бой или в очереди на рейд.")
        return
    floor = players[user_id]['tower_floor']
    if floor > len(TOWER_ENEMIES):
        bot.send_message(user_id, "🏆 Вы прошли всю Башню!", reply_markup=get_main_menu(user_id))
        return
    enemy = TOWER_ENEMIES[floor]
    players[user_id]['in_tower'] = True
    players[user_id]['tower_enemy_hp'] = enemy['hp']
    bot.send_message(user_id, f"Вы вошли на {floor} этаж!\nПеред вами {enemy['name']}. Ваш ход!", reply_markup=get_battle_menu())

@bot.message_handler(func=lambda message: message.text == "В бой!")
def search_opponent(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    if players[user_id].get('in_tower'):
        bot.send_message(user_id, "Сначала завершите бой в Башне!", reply_markup=get_battle_menu())
        return
    if players[user_id]['opponent'] is not None:
        bot.send_message(user_id, "Вы уже находитесь в бою!", reply_markup=get_battle_menu())
        return
    if user_id in queue:
        bot.send_message(user_id, "Вы уже ищете противника. Ожидайте...")
        return
    if queue:
        opponent_id = queue.pop(0)
        players[user_id]['opponent'] = opponent_id
        players[opponent_id]['opponent'] = user_id
        first_turn = random.choice([user_id, opponent_id])
        second_turn = opponent_id if first_turn == user_id else user_id
        players[first_turn]['is_turn'] = True
        players[second_turn]['is_turn'] = False
        reset_inactivity_timer(first_turn)
        for uid in (user_id, opponent_id):
            enemy_name = players[players[uid]['opponent']]['name']
            msg = f"Противник найден: {enemy_name}!\n"
            msg += f"Ваш ход! (Лимит времени: {MOVE_TIMEOUT} сек.)" if players[uid]['is_turn'] else "Ход противника, ожидайте..."
            bot.send_message(uid, msg, reply_markup=get_battle_menu())
    else:
        queue.append(user_id)
        bot.send_message(user_id, "Поиск противника... Ожидайте.")

@bot.message_handler(func=lambda message: message.text == "🦖 Рейд на Тирана")
def start_raid_queue(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    if players[user_id].get('in_tower'):
        bot.send_message(user_id, "Сначала завершите бой в Башне!", reply_markup=get_battle_menu())
        return
    if user_id in raid_cooldowns:
        timeLeft = raid_cooldowns[user_id] - time.time()
        if timeLeft > 0:
            mins = int(timeLeft // 60)
            secs = int(timeLeft % 60)
            bot.send_message(user_id, f"⏳ Вы на кулдауне после прошлого рейда! Подождите еще {mins} мин. {secs} сек.", reply_markup=get_main_menu(user_id))
            return
        else:
            del raid_cooldowns[user_id]
    global active_raid
    if active_raid is not None:
        if user_id in active_raid['participants']:
            bot.send_message(user_id, "Вы уже участвуете в текущем рейде на Тирана!", reply_markup=get_raid_menu())
            return
        if len(active_raid['participants']) < 5:
            active_raid['participants'].append(user_id)
            active_raid['damage'][user_id] = 0
            queue_text = f"🦖 Вы присоединились к текущему рейду на Тирана! Участников: {len(active_raid['participants'])}/5.\nЗдоровье Тирана: {active_raid['boss_hp']}/{active_raid['max_hp']} HP"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔄 Обновить", callback_data="raid_refresh"))
            bot.send_message(user_id, queue_text, reply_markup=markup)
            for uid in active_raid['participants']:
                if uid != user_id:
                    try:
                        bot.send_message(uid, f"👤 К текущему рейду присоединился новый участник! Всего игроков: {len(active_raid['participants'])}/5")
                    except Exception:
                        pass
            return
        else:
            bot.send_message(user_id, "Текущий рейд уже заполнен (максимум 5 участников). Ожидайте окончания боя.", reply_markup=get_main_menu(user_id))
            return
    if user_id in raid_queue:
        bot.send_message(user_id, "Вы уже в очереди на рейд. Ожидайте набора участников...")
        return
    raid_queue.append(user_id)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Обновить", callback_data="queue_refresh"))
    reply_markup_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    reply_markup_kb.add(KeyboardButton("❌ Прекратить поиск"))
    bot.send_message(user_id, f"🦖 Вы встали в очередь на рейд против Тирана!\nУчастников в очереди: {len(raid_queue)} из 3 (мин. для старта)", reply_markup=reply_markup_kb)
    bot.send_message(user_id, "Нажмите кнопку ниже, чтобы проверить количество участников:", reply_markup=markup)
    if len(raid_queue) >= 3:
        participants = raid_queue[:5] 
        del raid_queue[:len(participants)]
        active_raid = {
            'boss_hp': 1000,
            'max_hp': 1000,
            'participants': participants,
            'damage': {uid: 0 for uid in participants},
            'turn_index': 0
        }
        for uid in participants:
            raid_markup = InlineKeyboardMarkup()
            raid_markup.add(InlineKeyboardButton("🔄 Обновить", callback_data="raid_refresh"))
            bot.send_message(
                uid,
                f"🚨 РЕЙД НАЧАЛСЯ!\nБосс: Тиран (1000 HP)\nУчастников в группе: {len(participants)}\nВаш черед атаковать!",
                reply_markup=raid_markup
            )

@bot.callback_query_handler(func=lambda call: call.data == "queue_refresh")
def handle_queue_refresh(call):
    user_id = call.from_user.id
    if user_id in raid_queue:
        count = len(raid_queue)
        new_text = f"🦖 Вы в очереди на рейд против Тирана!\nУчастников в очереди: {count} из 3 (мин. для старта)"
        try:
            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup)
        except Exception:
            pass
        bot.answer_callback_query(call.id, f"Обновлено! В очереди: {count} из 3")
    else:
        bot.answer_callback_query(call.id, "Вы не находитесь в очереди.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "raid_refresh")
def handle_raid_refresh(call):
    global active_raid
    user_id = call.from_user.id
    if active_raid is not None and user_id in active_raid['participants']:
        current_turn_user = active_raid['participants'][active_raid['turn_index']]
        is_my_turn = (current_turn_user == user_id)
        turn_text = "Ваш черед атаковать!" if is_my_turn else "Ожидайте ход других участников."
        new_text = (
            f"🚨 АКТИВНЫЙ РЕЙД НА ТИРАНА\n"
            f"Здоровье Тирана: {active_raid['boss_hp']}/{active_raid['max_hp']} HP\n"
            f"Участников в группе: {len(active_raid['participants'])}/5\n"
            f"{turn_text}"
        )
        try:
            bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup)
        except Exception:
            pass
        bot.answer_callback_query(call.id, "Статус рейда обновлен!")
    else:
        bot.answer_callback_query(call.id, "Активный рейд не найден.", show_alert=True)

@bot.message_handler(func=lambda message: message.text == "❌ Прекратить поиск")
def cancel_raid_queue(message):
    user_id = message.chat.id
    if user_id in raid_queue:
        raid_queue.remove(user_id)
        bot.send_message(user_id, "❌ Вы вышли из очереди поиска рейда.", reply_markup=get_main_menu(user_id))
    else:
        bot.send_message(user_id, "Вы не находитесь в очереди на рейд.", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.text == "⚔️ Ударить Тирана")
def attack_tyrant(message):
    global active_raid
    user_id = message.chat.id
    if active_raid is None or user_id not in active_raid['participants']:
        bot.send_message(user_id, "Вы сейчас не участвуете в активном рейде.", reply_markup=get_main_menu(user_id))
        return
    current_participants = active_raid['participants']
    if current_participants[active_raid['turn_index']] != user_id:
        bot.send_message(user_id, "⏳ Сейчас не ваша очередь бить Тирана! Ожидайте ход других участников.")
        return
    base_dmg = random.randint(30, 60)
    damage = base_dmg + (players[user_id]['up_dmg'] * 3)
    active_raid['boss_hp'] -= damage
    active_raid['damage'][user_id] += damage
    bot.send_message(user_id, f"💥 Вы нанесли Тирану {damage} урона!")
    for uid in current_participants:
        if uid != user_id:
            try:
                bot.send_message(uid, f"⚔️ Участник нанес Тирану {damage} урона!")
            except Exception:
                pass
    if active_raid['boss_hp'] <= 0:
        sorted_dmg = sorted(active_raid['damage'].items(), key=lambda x: x[1], reverse=True)
        rewards = [
            (100, 100), 
            (50, 50),   
            (30, 30),   
            (10, 10),   
            (10, 10)    
        ]
        current_time = time.time()
        for idx, (uid, dmg) in enumerate(sorted_dmg):
            progress_quest(uid, 'raid_play', 1)
            progress_quest(uid, 'wk_raid_3', 1)
            progress_quest(uid, 'wk_raid_5', 1)
            progress_quest(uid, 'wk_raid_10', 1)
            progress_quest(uid, 'wk_dmg_500', dmg)
            progress_quest(uid, 'wk_dmg_1000', dmg)
            if idx < 2:
                progress_quest(uid, 'raid_top', 1)
            coins, xp = rewards[idx] if idx < len(rewards) else (5, 5)
            leveled_up = add_xp_and_coins(uid, xp, coins)
            raid_cooldowns[uid] = current_time + 600
            place_str = f"{idx + 1} место"
            msg = f"🎉 ТИРАН ПОВЕРЖЕН!\nВы заняли {place_str} по урону ({dmg} урона).\nНаграда: +{coins} монет 💰, +{xp} XP!"
            if leveled_up:
                new_lvl = players[uid]['level']
                new_rank = RANKS.get(new_lvl, "Абсолют")
                msg += f"\n🎉 ПОЗДРАВЛЯЕМ! Повышен уровень до {new_lvl} ({new_rank})!"
            try:
                bot.send_message(uid, msg, reply_markup=get_main_menu(uid))
            except Exception:
                pass
        active_raid = None
        return
    active_raid['turn_index'] = (active_raid['turn_index'] + 1) % len(current_participants)
    next_user_id = current_participants[active_raid['turn_index']]
    raid_markup = InlineKeyboardMarkup()
    raid_markup.add(InlineKeyboardButton("🔄 Обновить", callback_data="raid_refresh"))
    bot.send_message(user_id, f"Здоровье Тирана: {active_raid['boss_hp']}/{active_raid['max_hp']} HP. Ожидайте следующий ход.")
    try:
        bot.send_message(next_user_id, f"🚨 Ваш ход атаковать Тирана! (Здоровье босса: {active_raid['boss_hp']}/{active_raid['max_hp']} HP)", reply_markup=raid_markup)
    except Exception:
        pass

@bot.message_handler(func=lambda message: message.text == "Атака")
def attack(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('in_tower'):
        floor = players[user_id]['tower_floor']
        if floor > len(TOWER_ENEMIES):
            bot.send_message(user_id, "Вы прошли всю Башню!", reply_markup=get_main_menu(user_id))
            players[user_id]['in_tower'] = False
            return
        enemy = TOWER_ENEMIES[floor]
        base_dmg = random.randint(15, 25)
        damage = base_dmg + (players[user_id]['up_dmg'] * 2)
        players[user_id]['tower_enemy_hp'] -= damage
        msg = f"⚔️ Вы нанесли {damage} урона монстру {enemy['name']}!"
        if players[user_id]['tower_enemy_hp'] <= 0:
            players[user_id]['in_tower'] = False
            players[user_id]['hp'] = players[user_id]['max_hp']
            players[user_id]['tower_floor'] += 1
            coins_gain = enemy['coins']
            xp_gain = enemy['xp']
            leveled_up = add_xp_and_coins(user_id, xp_gain, coins_gain)
            win_msg = f"🏆 Вы одолели монстра {enemy['name']} и прошли этаж {floor}!\nНаграда: +{xp_gain} XP, +{coins_gain} монет 💰\nЗдоровье восстановлено."
            if leveled_up:
                new_lvl = players[user_id]['level']
                new_rank = RANKS.get(new_lvl, "Абсолют")
                win_msg += f"\n\n🎉 ПОЗДРАВЛЯЕМ! Вы повысили уровень до {new_lvl} ({new_rank})!"
            bot.send_message(user_id, win_msg, reply_markup=get_main_menu(user_id))
            save_players_data()
            return
        e_dmg = random.randint(enemy['dmg'][0], enemy['dmg'][1])
        players[user_id]['hp'] -= e_dmg
        msg += f"\n🩸 {enemy['name']} атакует в ответ и наносит {e_dmg} урона!\nВаше здоровье: {max(0, players[user_id]['hp'])} HP\nЗдоровье монстра: {max(0, players[user_id]['tower_enemy_hp'])} HP"
        if players[user_id]['hp'] <= 0:
            players[user_id]['in_tower'] = False
            players[user_id]['hp'] = players[user_id]['max_hp']
            msg += "\n\n☠️ Вы проиграли! Здоровье восстановлено. Возвращайтесь, когда станете сильнее."
            bot.send_message(user_id, msg, reply_markup=get_main_menu(user_id))
        else:
            bot.send_message(user_id, msg, reply_markup=get_battle_menu())
        save_players_data()
        return

    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu(user_id))
        return

    if not players[user_id]['is_turn']:
        bot.send_message(user_id, "Сейчас не ваш ход!")
        return

    opponent_id = players[user_id]['opponent']
    base_dmg = random.randint(15, 25)
    damage = base_dmg + (players[user_id]['up_dmg'] * 2)
    if players[opponent_id]['is_defending']:
        damage = damage // 2
        players[opponent_id]['is_defending'] = False
        def_msg = " Противник защищался, урон снижен!"
    else:
        def_msg = ""
    players[opponent_id]['hp'] -= damage
    bot.send_message(user_id, f"Вы нанесли {damage} урона!{def_msg}")
    bot.send_message(opponent_id, f"Противник нанес вам {damage} урона!{def_msg}\nВаше здоровье: {max(0, players[opponent_id]['hp'])} HP")
    if players[opponent_id]['hp'] <= 0:
        end_battle(winner_id=user_id, loser_id=opponent_id)
    else:
        players[user_id]['is_turn'] = False
        players[opponent_id]['is_turn'] = True
        reset_inactivity_timer(opponent_id)
        bot.send_message(opponent_id, f"Ваш ход! (Лимит времени: {MOVE_TIMEOUT} сек.) Выберите действие.")
    save_players_data()

@bot.message_handler(func=lambda message: message.text == "Защита")
def defend(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('in_tower'):
        floor = players[user_id]['tower_floor']
        enemy = TOWER_ENEMIES[floor]
        e_dmg = random.randint(enemy['dmg'][0], enemy['dmg'][1]) // 2
        players[user_id]['hp'] -= e_dmg
        msg = f"🛡️ Вы ушли в защиту!\n🩸 {enemy['name']} атакует, но урон снижен: {e_dmg} урона!\nВаше здоровье: {max(0, players[user_id]['hp'])} HP\nЗдоровье монстра: {max(0, players[user_id]['tower_enemy_hp'])} HP"
        if players[user_id]['hp'] <= 0:
            players[user_id]['in_tower'] = False
            players[user_id]['hp'] = players[user_id]['max_hp']
            msg += "\n\n☠️ Вы проиграли! Здоровье восстановлено. Возвращайтесь, когда станете сильнее."
            bot.send_message(user_id, msg, reply_markup=get_main_menu(user_id))
        else:
            bot.send_message(user_id, msg, reply_markup=get_battle_menu())
        save_players_data()
        return

    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu(user_id))
        return

    if not players[user_id]['is_turn']:
        bot.send_message(user_id, "Сейчас не ваш ход!")
        return

    opponent_id = players[user_id]['opponent']
    players[user_id]['is_defending'] = True
    bot.send_message(user_id, "Вы приготовились к защите. Следующий урон будет снижен!")
    bot.send_message(opponent_id, f"Противник ушел в глухую оборону.\nВаш ход! (Лимит времени: {MOVE_TIMEOUT} сек.)")
    players[user_id]['is_turn'] = False
    players[opponent_id]['is_turn'] = True
    reset_inactivity_timer(opponent_id)
    save_players_data()

@bot.message_handler(func=lambda message: message.text in ["🏳️ Сдаться", "Сдаться"])
def surrender(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('in_tower'):
        players[user_id]['in_tower'] = False
        players[user_id]['hp'] = players[user_id]['max_hp']
        bot.send_message(user_id, "🏳️ Вы сбежали из Башни! Здоровье восстановлено.", reply_markup=get_main_menu(user_id))
        save_players_data()
        return

    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu(user_id))
        return

    opponent_id = players[user_id]['opponent']
    players[opponent_id]['wins'] += 1
    players[user_id]['losses'] += 1
    progress_quest(opponent_id, 'pvp_play', 1)
    progress_quest(opponent_id, 'pvp_win', 1)
    progress_quest(user_id, 'pvp_play', 1)
    leveled_up = add_xp_and_coins(opponent_id, 10, 20)
    for uid in (user_id, opponent_id):
        players[uid]['opponent'] = None
        players[uid]['hp'] = players[uid]['max_hp']
        players[uid]['is_defending'] = False
        players[uid]['is_turn'] = False
        battle_timers.pop(uid, None)
    save_players_data()
    win_msg = "🏆 Противник сдался! Вы победили!\nНаграда: +10 XP, +20 монет 💰\nЗдоровье восстановлено."
    if leveled_up:
        new_lvl = players[opponent_id]['level']
        new_rank = RANKS.get(new_lvl, "Абсолют")
        win_msg += f"\n\n🎉 ПОЗДРАВЛЯЕМ! Вы повысили уровень до {new_lvl} ({new_rank})!"
    bot.send_message(opponent_id, win_msg, reply_markup=get_main_menu(opponent_id))
    bot.send_message(user_id, "🏳️ Вы сдались! Засчитано поражение.\nЗдоровье восстановлено.", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.text == "Инвентарь")
def inventory(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('banned'): return
    hp = players[user_id]['hp']
    max_hp = players[user_id]['max_hp']
    items = players[user_id]['inventory']
    if not items:
        bot.send_message(user_id, f"Ваш Инвентарь:\nЗдоровье: {hp}/{max_hp}\nПредметы: Пусто", reply_markup=get_inventory_menu([]))
        return
    bot.send_message(
        user_id,
        f"Ваш Инвентарь:\nЗдоровье: {hp}/{max_hp}\nВыберите предмет для использования:",
        reply_markup=get_inventory_menu(items)
    )

@bot.message_handler(func=lambda message: message.text in ["Назад", "⬅️ Назад"])
def back_to_menu(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if players[user_id].get('in_tower'):
        bot.send_message(user_id, "Вы вернулись в меню боя Башни:", reply_markup=get_battle_menu())
    elif players[user_id]['opponent'] is not None:
        bot.send_message(user_id, "Вы вернулись в меню боя:", reply_markup=get_battle_menu())
    elif active_raid is not None and user_id in active_raid['participants']:
        bot.send_message(user_id, "Вы в активном рейде:", reply_markup=get_raid_menu())
    else:
        bot.send_message(user_id, "Главное меню:", reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.text.startswith("Использовать: "))
def use_item(message):
    user_id = message.chat.id
    if user_id not in players: return
    if players[user_id].get('banned'): return
    item_name = message.text.replace("Использовать: ", "").split(" (")[0]
    items = players[user_id]['inventory']
    if item_name in items:
        if item_name == "Зелье лечения":
            if players[user_id]['hp'] >= players[user_id]['max_hp']:
                bot.send_message(user_id, "Ваше здоровье уже максимальное!")
                return
            items.remove(item_name)
            heal_amount = 40
            players[user_id]['hp'] = min(players[user_id]['max_hp'], players[user_id]['hp'] + heal_amount)
            progress_quest(user_id, 'potion_use', 1)
            save_players_data()
            bot.send_message(user_id, f"Вы использовали Зелье лечения и восстановили {heal_amount} HP!\nТекущее здоровье: {players[user_id]['hp']}/{players[user_id]['max_hp']}")
            if players[user_id]['opponent'] is not None and players[user_id]['is_turn']:
                opponent_id = players[user_id]['opponent']
                players[user_id]['is_turn'] = False
                players[opponent_id]['is_turn'] = True
                reset_inactivity_timer(opponent_id)
                bot.send_message(opponent_id, f"Противник потратил ход на зелье.\nВаш ход! (Лимит времени: {MOVE_TIMEOUT} сек.)")
            elif players[user_id].get('in_tower'):
                floor = players[user_id]['tower_floor']
                enemy = TOWER_ENEMIES[floor]
                e_dmg = random.randint(enemy['dmg'][0], enemy['dmg'][1])
                players[user_id]['hp'] -= e_dmg
                msg_append = f"🩸 {enemy['name']} атакует вас, пока вы пили зелье, и наносит {e_dmg} урона!\nВаше здоровье: {max(0, players[user_id]['hp'])} HP"
                if players[user_id]['hp'] <= 0:
                    players[user_id]['in_tower'] = False
                    players[user_id]['hp'] = players[user_id]['max_hp']
                    msg_append += "\n\n☠️ Вы проиграли! Здоровье восстановлено."
                    bot.send_message(user_id, msg_append, reply_markup=get_main_menu(user_id))
                else:
                    bot.send_message(user_id, msg_append, reply_markup=get_battle_menu())
                save_players_data()
        else:
            bot.send_message(user_id, "Этот предмет нельзя использовать.")
    else:
        bot.send_message(user_id, "У вас больше нет этого предмета!")

@bot.message_handler(content_types=['text'])
def global_chat(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    if message.text.startswith('/'): return
    p = players[user_id]
    if p.get('banned'): return
    if p.get('muted_until', 0) > time.time():
        bot.send_message(user_id, "❌ У вас действует мут. Вы не можете писать в глобальный чат.")
        return
    sender_name = f"@{p['username']}" if p.get('username') else p['name']
    chat_msg = f"{sender_name}: {message.text}"
    for uid in players:
        if uid != user_id:
            try:
                bot.send_message(uid, chat_msg)
            except Exception:
                pass

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            time.sleep(5)
