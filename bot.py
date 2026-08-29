import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import random
import time
from threading import Thread
from flask import Flask

TOKEN = "8609399059:AAH1VPl7e9LLPb3zIQ4g7sCtD8yZPtK12-c"
bot = telebot.TeleBot(TOKEN)

players = {}
queue = []

raid_queue = []          
active_raid = None       
raid_cooldowns = {}      

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
            'coins': 0,
            'wins': 0,
            'losses': 0,
            'up_dmg': 0,    
            'up_hp': 0      
        }
    else:
        players[user_id]['name'] = name
        if username:
            players[user_id]['username'] = username
        for key, default in [('level', 1), ('xp', 0), ('coins', 0), ('wins', 0), ('losses', 0), ('up_dmg', 0), ('up_hp', 0)]:
            if key not in players[user_id]:
                players[user_id][key] = default

def add_xp_and_coins(user_id, xp_gain, coins_gain):
    p = players[user_id]
    p['coins'] += coins_gain

    if p['level'] >= 10:
        p['xp'] = 100
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

    return leveled_up

def get_progress_bar(xp):
    percent = min(100, max(0, xp))
    filled = percent // 10
    empty = 10 - filled
    return "█" * filled + "░" * empty + f" {percent}%"

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("В бой!"),
        KeyboardButton("🦖 Рейд на Тирана"),
        KeyboardButton("⚡ Прокачка"),
        KeyboardButton("Инвентарь"),
        KeyboardButton("👤 Профиль"),
        KeyboardButton("🏆 Топ")
    )
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

    leveled_up = add_xp_and_coins(winner_id, 10, 20)

    for uid in (winner_id, loser_id):
        players[uid]['opponent'] = None
        players[uid]['hp'] = players[uid]['max_hp']
        players[uid]['is_defending'] = False
        players[uid]['is_turn'] = False

    win_msg = "🏆 Вы победили!\nНаграда: +10 XP, +20 монет 💰\nЗдоровье восстановлено."
    if leveled_up:
        new_lvl = players[winner_id]['level']
        new_rank = RANKS.get(new_lvl, "Абсолют")
        win_msg += f"\n\n🎉 ПОЗДРАВЛЯЕМ! Вы повысили уровень до {new_lvl} ({new_rank})!"

    bot.send_message(winner_id, win_msg, reply_markup=get_main_menu())
    bot.send_message(loser_id, "☠️ Вы проиграли!\nЗдоровье восстановлено.", reply_markup=get_main_menu())

@bot.message_handler(commands=['start'])
def start_game(message):
    init_user(message.chat.id, message.from_user.first_name, message.from_user.username)
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! Готов к сражениям?",
        reply_markup=get_main_menu()
    )

@bot.message_handler(func=lambda message: message.text in ["👤 Профиль", "Профиль"])
def show_profile(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
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
        f"Макс. HP: {p['max_hp']} (Улучшений: {p['up_hp']}/{MAX_UPGRADE_LEVEL})\n"
        f"Сила атаки бонус: +{p['up_dmg'] * 3} (Улучшений: {p['up_dmg']}/{MAX_UPGRADE_LEVEL})\n"
        f"Монеты: 💰 {p['coins']}\n"
        f"Победы: {p['wins']} | Поражения: {p['losses']}\n"
        f"Опыт: {xp_str}\n"
        f"Прогресс: {progress_str}\n"
        f"До следующего ранга: {left_str}"
    )

    bot.send_message(user_id, profile_text, reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text and "Прокачка" in message.text)
def show_upgrades(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
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

@bot.message_handler(func=lambda message: message.text == "В бой!")
def search_opponent(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)

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

        for uid in (user_id, opponent_id):
            enemy_name = players[players[uid]['opponent']]['name']
            msg = f"Противник найден: {enemy_name}!\n"
            msg += "Ваш ход!" if players[uid]['is_turn'] else "Ход противника, ожидайте..."
            bot.send_message(uid, msg, reply_markup=get_battle_menu())
    else:
        queue.append(user_id)
        bot.send_message(user_id, "Поиск противника... Ожидайте.")

@bot.message_handler(func=lambda message: message.text == "🦖 Рейд на Тирана")
def start_raid_queue(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)

    if user_id in raid_cooldowns:
        timeLeft = raid_cooldowns[user_id] - time.time()
        if timeLeft > 0:
            mins = int(timeLeft // 60)
            secs = int(timeLeft % 60)
            bot.send_message(user_id, f"⏳ Вы на кулдауне после прошлого рейда! Подождите еще {mins} мин. {secs} сек.", reply_markup=get_main_menu())
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
            bot.send_message(user_id, f"🦖 Вы присоединились к текущему рейду на Тирана! Участников: {len(active_raid['participants'])}/5.\nЗдоровье Тирана: {active_raid['boss_hp']}/{active_raid['max_hp']} HP", reply_markup=get_raid_menu())
            for uid in active_raid['participants']:
                if uid != user_id:
                    bot.send_message(uid, f"👤 К текущему рейду присоединился новый участник! Всего игроков: {len(active_raid['participants'])}")
            return
        else:
            bot.send_message(user_id, "Текущий рейд уже заполнен (максимум 5 участников). Ожидайте окончания боя.", reply_markup=get_main_menu())
            return

    if user_id in raid_queue:
        bot.send_message(user_id, "Вы уже в очереди на рейд. Ожидайте набора участников...")
        return

    raid_queue.append(user_id)
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("❌ Прекратить поиск"))

    bot.send_message(user_id, f"🦖 Вы встали в очередь на рейд против Тирана!\nУчастников в очереди: {len(raid_queue)}/3 (мин. для старта)", reply_markup=markup)

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
            bot.send_message(
                uid,
                f"🚨 РЕЙД НАЧАЛСЯ!\nБосс: Тиран (1000 HP)\nУчастников в группе: {len(participants)}\nВаш черед атаковать!",
                reply_markup=get_raid_menu()
            )

@bot.message_handler(func=lambda message: message.text == "❌ Прекратить поиск")
def cancel_raid_queue(message):
    user_id = message.chat.id
    if user_id in raid_queue:
        raid_queue.remove(user_id)
        bot.send_message(user_id, "❌ Вы вышли из очереди поиска рейда.", reply_markup=get_main_menu())
    else:
        bot.send_message(user_id, "Вы не находитесь в очереди на рейд.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text == "⚔️ Ударить Тирана")
def attack_tyrant(message):
    global active_raid
    user_id = message.chat.id

    if active_raid is None or user_id not in active_raid['participants']:
        bot.send_message(user_id, "Вы сейчас не участвуете в активном рейде.", reply_markup=get_main_menu())
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
            bot.send_message(uid, f"⚔️ Участник нанес Тирану {damage} урона!")

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
            coins, xp = rewards[idx] if idx < len(rewards) else (5, 5)
            leveled_up = add_xp_and_coins(uid, xp, coins)
            
            raid_cooldowns[uid] = current_time + 600

            place_str = f"{idx + 1} место"
            msg = f"🎉 ТИРАН ПОВЕРЖЕН!\nВы заняли {place_str} по урону ({dmg} урона).\nНаграда: +{coins} монет 💰, +{xp} XP!"
            if leveled_up:
                new_lvl = players[uid]['level']
                new_rank = RANKS.get(new_lvl, "Абсолют")
                msg += f"\n🎉 ПОЗДРАВЛЯЕМ! Повышен уровень до {new_lvl} ({new_rank})!"
            
            bot.send_message(uid, msg, reply_markup=get_main_menu())

        active_raid = None
        return

    active_raid['turn_index'] = (active_raid['turn_index'] + 1) % len(current_participants)
    next_user_id = current_participants[active_raid['turn_index']]

    bot.send_message(user_id, f"Здоровье Тирана: {active_raid['boss_hp']}/{active_raid['max_hp']} HP. Ожидайте следующий ход.")
    bot.send_message(next_user_id, f"🚨 Ваш ход атаковать Тирана! (Здоровье босса: {active_raid['boss_hp']}/{active_raid['max_hp']} HP)")

@bot.message_handler(func=lambda message: message.text == "Атака")
def attack(message):
    user_id = message.chat.id
    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu())
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
        bot.send_message(opponent_id, "Ваш ход! Выберите действие.")

@bot.message_handler(func=lambda message: message.text == "Защита")
def defend(message):
    user_id = message.chat.id
    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu())
        return

    if not players[user_id]['is_turn']:
        bot.send_message(user_id, "Сейчас не ваш ход!")
        return

    opponent_id = players[user_id]['opponent']
    players[user_id]['is_defending'] = True

    bot.send_message(user_id, "Вы приготовились к защите. Следующий урон будет снижен!")
    bot.send_message(opponent_id, "Противник ушел в глухую оборону.\nВаш ход!")

    players[user_id]['is_turn'] = False
    players[opponent_id]['is_turn'] = True

@bot.message_handler(func=lambda message: message.text in ["🏳️ Сдаться", "Сдаться"])
def surrender(message):
    user_id = message.chat.id
    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu())
        return

    opponent_id = players[user_id]['opponent']

    players[opponent_id]['wins'] += 1
    players[user_id]['losses'] += 1

    leveled_up = add_xp_and_coins(opponent_id, 10, 20)

    for uid in (user_id, opponent_id):
        players[uid]['opponent'] = None
        players[uid]['hp'] = players[uid]['max_hp']
        players[uid]['is_defending'] = False
        players[uid]['is_turn'] = False

    win_msg = "🏆 Противник сдался! Вы победили!\nНаграда: +10 XP, +20 монет 💰\nЗдоровье восстановлено."
    if leveled_up:
        new_lvl = players[opponent_id]['level']
        new_rank = RANKS.get(new_lvl, "Абсолют")
        win_msg += f"\n\n🎉 ПОЗДРАВЛЯЕМ! Вы повысили уровень до {new_lvl} ({new_rank})!"

    bot.send_message(opponent_id, win_msg, reply_markup=get_main_menu())
    bot.send_message(user_id, "🏳️ Вы сдались! Засчитано поражение.\nЗдоровье восстановлено.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text == "Инвентарь")
def inventory(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)

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
    if players[user_id]['opponent'] is not None:
        bot.send_message(user_id, "Вы вернулись в меню боя:", reply_markup=get_battle_menu())
    elif active_raid is not None and user_id in active_raid['participants']:
        bot.send_message(user_id, "Вы в активном рейде:", reply_markup=get_raid_menu())
    else:
        bot.send_message(user_id, "Главное меню:", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text.startswith("Использовать: "))
def use_item(message):
    user_id = message.chat.id
    if user_id not in players:
        return

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

            bot.send_message(user_id, f"Вы использовали Зелье лечения и восстановили {heal_amount} HP!\nТекущее здоровье: {players[user_id]['hp']}/{players[user_id]['max_hp']}")

            if players[user_id]['opponent'] is not None and players[user_id]['is_turn']:
                opponent_id = players[user_id]['opponent']
                players[user_id]['is_turn'] = False
                players[opponent_id]['is_turn'] = True
                bot.send_message(opponent_id, "Противник потратил ход на зелье.\nВаш ход!")
        else:
            bot.send_message(user_id, "Этот предмет нельзя использовать.")
    else:
        bot.send_message(user_id, "У вас больше нет этого предмета!")

@bot.message_handler(content_types=['text'])
def global_chat(message):
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    
    if message.text.startswith('/'):
        return

    p = players[user_id]
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
