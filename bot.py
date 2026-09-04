import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import random
import time
from threading import Thread
from flask import Flask
import sqlite3

TOKEN = "8609399059:AAH1VPl7e9LLPb3zIQ4g7sCtD8yZPtK12-c"
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 6236795210

players = {}
queue = []
user_states = {}

REQUIRED_CREATE_LEVEL = 5
INITIAL_MAX_MEMBERS = 10
BONUS_MEMBERS_PER_LEVEL = 2

tyrant_boss = {
    'hp': 50000,
    'max_hp': 50000,
    'level': 1,
    'is_alive': True
}

conn = sqlite3.connect("game_database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    coins INTEGER DEFAULT 0,
    clan_id INTEGER DEFAULT NULL,
    clan_role TEXT DEFAULT NULL,
    is_muted INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    muted_until INTEGER DEFAULT 0,
    banned_until INTEGER DEFAULT 0,
    tower_floor INTEGER DEFAULT 1,
    quest_battles INTEGER DEFAULT 0,
    quest_casino INTEGER DEFAULT 0,
    quest_claimed INTEGER DEFAULT 0,
    last_quest_reset INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS clans (
    clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    tag TEXT UNIQUE,
    leader_id INTEGER,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    type TEXT DEFAULT 'open',
    max_members INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS clan_applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(clan_id, user_id)
)
""")

conn.commit()

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

def parse_duration(str_val):
    if not str_val:
        return 0
    unit = str_val[-1].lower()
    val_str = str_val[:-1]
    if not val_str.isdigit():
        if str_val.isdigit():
            return int(str_val) * 60
        return 0
    val = int(val_str)
    if unit == 's':
        return val
    elif unit == 'm':
        return val * 60
    elif unit == 'h':
        return val * 3600
    elif unit == 'd':
        return val * 86400
    return 0

def format_time_remaining(seconds):
    if seconds <= 0:
        return "0с"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    parts = []
    if d > 0:
        parts.append(f"{d}д")
    if h > 0:
        parts.append(f"{h}ч")
    if m > 0:
        parts.append(f"{m}м")
    if s > 0 or not parts:
        parts.append(f"{s}с")
    return " ".join(parts)

def is_user_banned(user_id):
    cursor.execute("SELECT is_banned, banned_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] == 1:
        banned_until = row[1]
        now = int(time.time())
        if banned_until > 0 and now >= banned_until:
            cursor.execute("UPDATE users SET is_banned = 0, banned_until = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            return False
        return True
    return False

def get_ban_remaining(user_id):
    cursor.execute("SELECT banned_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] > 0:
        rem = row[0] - int(time.time())
        return max(0, rem)
    return 0

def is_user_muted(user_id):
    cursor.execute("SELECT is_muted, muted_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] == 1:
        muted_until = row[1]
        now = int(time.time())
        if muted_until > 0 and now >= muted_until:
            cursor.execute("UPDATE users SET is_muted = 0, muted_until = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            return False
        return True
    return False

def get_mute_remaining(user_id):
    cursor.execute("SELECT muted_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] > 0:
        rem = row[0] - int(time.time())
        return max(0, rem)
    return 0

def find_target_user(identifier):
    identifier = identifier.strip()
    if identifier.startswith("@"):
        clean_username = identifier[1:]
        cursor.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (clean_username,))
        row = cursor.fetchone()
        if row:
            return row[0]
        for uid, pdata in players.items():
            if pdata.get("username") and pdata["username"].lower() == clean_username.lower():
                return uid
    elif identifier.isdigit():
        return int(identifier)
    return None

def sync_user_db(user_id, username):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    conn.commit()

def get_db_user(user_id):
    cursor.execute("""
        SELECT user_id, username, level, xp, coins, clan_id, clan_role, is_muted, is_banned, muted_until, banned_until,
               tower_floor, quest_battles, quest_casino, quest_claimed, last_quest_reset
        FROM users WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            "user_id": row[0],
            "username": row[1],
            "level": row[2],
            "xp": row[3],
            "coins": row[4],
            "clan_id": row[5],
            "clan_role": row[6],
            "is_muted": row[7],
            "is_banned": row[8],
            "muted_until": row[9],
            "banned_until": row[10],
            "tower_floor": row[11],
            "quest_battles": row[12],
            "quest_casino": row[13],
            "quest_claimed": row[14],
            "last_quest_reset": row[15]
        }
    return None

def check_quest_reset(user_id):
    db_user = get_db_user(user_id)
    if not db_user:
        return
    now = int(time.time())
    if now - db_user['last_quest_reset'] >= 86400:
        cursor.execute("""
            UPDATE users SET quest_battles = 0, quest_casino = 0, quest_claimed = 0, last_quest_reset = ?
            WHERE user_id = ?
        """, (now, user_id))
        conn.commit()

def get_clan_by_id(clan_id):
    cursor.execute("SELECT clan_id, name, tag, leader_id, level, xp, type, max_members FROM clans WHERE clan_id = ?", (clan_id,))
    row = cursor.fetchone()
    if row:
        return {
            "clan_id": row[0],
            "name": row[1],
            "tag": row[2],
            "leader_id": row[3],
            "level": row[4],
            "xp": row[5],
            "type": row[6],
            "max_members": row[7]
        }
    return None

def get_clan_by_name_or_tag(identifier):
    cursor.execute("SELECT clan_id, name, tag, leader_id, level, xp, type, max_members FROM clans WHERE name = ? OR tag = ?", (identifier, identifier.upper()))
    row = cursor.fetchone()
    if row:
        return {
            "clan_id": row[0],
            "name": row[1],
            "tag": row[2],
            "leader_id": row[3],
            "level": row[4],
            "xp": row[5],
            "type": row[6],
            "max_members": row[7]
        }
    return None

def get_clan_members_count(clan_id):
    cursor.execute("SELECT COUNT(*) FROM users WHERE clan_id = ?", (clan_id,))
    return cursor.fetchone()[0]

def get_clan_members(clan_id):
    cursor.execute("SELECT user_id, username, level, clan_role FROM users WHERE clan_id = ?", (clan_id,))
    rows = cursor.fetchall()
    members = []
    for row in rows:
        members.append({
            "user_id": row[0],
            "username": row[1],
            "level": row[2],
            "clan_role": row[3]
        })
    return members

def get_all_clans():
    cursor.execute("SELECT clan_id, name, tag, level, type, max_members FROM clans")
    rows = cursor.fetchall()
    clans = []
    for row in rows:
        clans.append({
            "clan_id": row[0],
            "name": row[1],
            "tag": row[2],
            "level": row[3],
            "type": row[4],
            "max_members": row[5]
        })
    return clans

def add_clan_xp(clan_id, xp_amount):
    clan = get_clan_by_id(clan_id)
    if not clan:
        return
    
    new_xp = clan["xp"] + xp_amount
    current_level = clan["level"]
    required_xp = current_level * 1000
    
    if new_xp >= required_xp:
        new_level = current_level + 1
        rem_xp = new_xp - required_xp
        new_max_members = INITIAL_MAX_MEMBERS + (new_level - 1) * BONUS_MEMBERS_PER_LEVEL
        cursor.execute(
            "UPDATE clans SET level = ?, xp = ?, max_members = ? WHERE clan_id = ?",
            (new_level, rem_xp, new_max_members, clan_id)
        )
    else:
        cursor.execute("UPDATE clans SET xp = ? WHERE clan_id = ?", (new_xp, clan_id))
    conn.commit()

def create_clan(user_id, clan_name, clan_tag):
    user = get_db_user(user_id)
    if not user:
        return "❌ Ошибка: Пользователь не найден!"
    if user["clan_id"] is not None:
        return "❌ Вы уже состоите в клане!"
    if user["level"] < REQUIRED_CREATE_LEVEL:
        return f"🔒 Создание клана доступно с {REQUIRED_CREATE_LEVEL} уровня! Ваш уровень: {user['level']}."
    
    clan_name = clan_name.strip()
    clan_tag = clan_tag.strip().upper()
    
    if len(clan_name) < 3 or len(clan_name) > 16:
        return "❌ Название клана должно содержать от 3 до 16 символов!"
    if len(clan_tag) < 3 or len(clan_tag) > 4:
        return "❌ Тэг клана должен содержать от 3 до 4 символов!"
    
    cursor.execute("SELECT clan_id FROM clans WHERE name = ? OR tag = ?", (clan_name, clan_tag))
    if cursor.fetchone():
        return "❌ Клан с таким названием или тэгом уже существует!"
    
    cursor.execute(
        "INSERT INTO clans (name, tag, leader_id, max_members) VALUES (?, ?, ?, ?)",
        (clan_name, clan_tag, user_id, INITIAL_MAX_MEMBERS)
    )
    clan_id = cursor.lastrowid
    
    cursor.execute(
        "UPDATE users SET clan_id = ?, clan_role = 'leader' WHERE user_id = ?",
        (clan_id, user_id)
    )
    conn.commit()
    return f"🎉 Клан [{clan_tag}] {clan_name} успешно создан!"

def join_clan(user_id, clan_identifier):
    user = get_db_user(user_id)
    if not user:
        return "❌ Ошибка: Пользователь не найден!"
    if user["clan_id"] is not None:
        return "❌ Вы уже состоите в клане!"
    
    clan = get_clan_by_name_or_tag(clan_identifier)
    if not clan:
        if str(clan_identifier).isdigit():
            clan = get_clan_by_id(int(clan_identifier))
    
    if not clan:
        return "❌ Клан не найден!"
    
    clan_id = clan["clan_id"]
    current_members = get_clan_members_count(clan_id)
    if current_members >= clan["max_members"]:
        return "❌ В клане нет свободных мест!"
    
    if clan["type"] == "closed":
        cursor.execute("INSERT OR IGNORE INTO clan_applications (clan_id, user_id) VALUES (?, ?)", (clan_id, user_id))
        conn.commit()
        return f"📩 Клан [{clan['tag']}] {clan['name']} закрытого типа. Ваша заявка отправлена лидеру и заместителям!"
    
    cursor.execute(
        "UPDATE users SET clan_id = ?, clan_role = 'member' WHERE user_id = ?",
        (clan_id, user_id)
    )
    cursor.execute("DELETE FROM clan_applications WHERE user_id = ?", (user_id,))
    conn.commit()
    return f"🎉 Вы успешно вступили в клан [{clan['tag']}] {clan['name']}!"

def leave_clan(user_id):
    user = get_db_user(user_id)
    if not user or user["clan_id"] is None:
        return "❌ Вы не состоите в клане!"
    
    if user["clan_role"] == "leader":
        return "❌ Лидер не может покинуть клан! Передайте лидерство или расформируйте клан."
    
    cursor.execute(
        "UPDATE users SET clan_id = NULL, clan_role = NULL WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    return "🚪 Вы успешно покинули клан."

def kick_member(actor_id, target_id):
    actor = get_db_user(actor_id)
    target = get_db_user(target_id)
    
    if not actor or actor["clan_id"] is None:
        return "❌ Вы не состоите в клане!"
    if not target or target["clan_id"] != actor["clan_id"]:
        return "❌ Этот игрок не состоит в вашем клане!"
    
    if actor["clan_role"] not in ["leader", "deputy"]:
        return "❌ У вас нет прав для исключения участников!"
    
    if target["clan_role"] == "leader":
        return "❌ Нельзя исключить лидера клана!"
    if actor["clan_role"] == "deputy" and target["clan_role"] == "deputy":
        return "❌ Заместитель не может исключить другого заместителя!"
    
    cursor.execute(
        "UPDATE users SET clan_id = NULL, clan_role = NULL WHERE user_id = ?",
        (target_id,)
    )
    conn.commit()
    return f"👢 Игрок {target['username']} исключен из клана."

def promote_member(actor_id, target_id):
    actor = get_db_user(actor_id)
    target = get_db_user(target_id)
    
    if not actor or actor["clan_role"] != "leader":
        return "❌ Только лидер клана может назначать заместителей!"
    if not target or target["clan_id"] != actor["clan_id"]:
        return "❌ Этот игрок не состоит в вашем клане!"
    if target["clan_role"] == "deputy":
        return "❌ Игрок уже является заместителем!"
    if target["clan_role"] == "leader":
        return "❌ Нельзя изменить роль лидера!"
    
    cursor.execute("UPDATE users SET clan_role = 'deputy' WHERE user_id = ?", (target_id,))
    conn.commit()
    return f"⭐ Игрок {target['username']} назначен заместителем клана!"

def demote_member(actor_id, target_id):
    actor = get_db_user(actor_id)
    target = get_db_user(target_id)
    
    if not actor or actor["clan_role"] != "leader":
        return "❌ Только лидер клана может разжаловать заместителей!"
    if not target or target["clan_id"] != actor["clan_id"]:
        return "❌ Этот игрок не состоит в вашем клане!"
    if target["clan_role"] != "deputy":
        return "❌ Игрок не является заместителем!"
    
    cursor.execute("UPDATE users SET clan_role = 'member' WHERE user_id = ?", (target_id,))
    conn.commit()
    return f"🔻 Игрок {target['username']} понижен до обычного участника."

def transfer_leadership(actor_id, target_id):
    actor = get_db_user(actor_id)
    target = get_db_user(target_id)
    
    if not actor or actor["clan_role"] != "leader":
        return "❌ Только лидер клана может передать лидерство!"
    if not target or target["clan_id"] != actor["clan_id"]:
        return "❌ Этот игрок не состоит в вашем клане!"
    if actor_id == target_id:
        return "❌ Вы уже являетесь лидером!"
    
    clan_id = actor["clan_id"]
    cursor.execute("UPDATE users SET clan_role = 'member' WHERE user_id = ?", (actor_id,))
    cursor.execute("UPDATE users SET clan_role = 'leader' WHERE user_id = ?", (target_id,))
    cursor.execute("UPDATE clans SET leader_id = ? WHERE clan_id = ?", (target_id, clan_id))
    conn.commit()
    return f"👑 Лидерство клана успешно передано игроку {target['username']}!"

def set_clan_type(actor_id, new_type):
    actor = get_db_user(actor_id)
    if not actor or actor["clan_role"] not in ["leader", "deputy"]:
        return "❌ У вас нет прав на изменение настроек клана!"
    if new_type not in ["open", "closed"]:
        return "❌ Неверный тип клана! Используйте 'open' или 'closed'."
    
    cursor.execute("UPDATE clans SET type = ? WHERE clan_id = ?", (new_type, actor["clan_id"]))
    conn.commit()
    return f"⚙️ Тип клана успешно изменен на: {'Открытый' if new_type == 'open' else 'Закрытый'}."

def get_clan_applications(actor_id):
    actor = get_db_user(actor_id)
    if not actor or actor["clan_role"] not in ["leader", "deputy"]:
        return "❌ У вас нет прав для просмотра заявок!"
    
    clan_id = actor["clan_id"]
    cursor.execute("""
        SELECT ca.application_id, u.user_id, u.username, u.level 
        FROM clan_applications ca 
        JOIN users u ON ca.user_id = u.user_id 
        WHERE ca.clan_id = ?
    """, (clan_id,))
    rows = cursor.fetchall()
    
    if not rows:
        return "📩 Список заявок пуст."
    
    text = "📩 **Заявки на вступление:**\n"
    for row in rows:
        text += f"ID заявки: {row[0]} | Игрок: {row[2]} (Ур. {row[3]}) | User ID: {row[1]}\n"
    return text

def process_application(actor_id, application_id, action):
    actor = get_db_user(actor_id)
    if not actor or actor["clan_role"] not in ["leader", "deputy"]:
        return "❌ У вас нет прав для обработки заявок!"
    
    cursor.execute("SELECT clan_id, user_id FROM clan_applications WHERE application_id = ?", (application_id,))
    app = cursor.fetchone()
    if not app:
        return "❌ Заявка не найдена!"
    
    clan_id, applicant_id = app[0], app[1]
    if clan_id != actor["clan_id"]:
        return "❌ Это заявка из другого клана!"
    
    if action == "accept":
        clan = get_clan_by_id(clan_id)
        current_members = get_clan_members_count(clan_id)
        if current_members >= clan["max_members"]:
            return "❌ В клане нет свободных мест для принятия заявки!"
        
        cursor.execute("UPDATE users SET clan_id = ?, clan_role = 'member' WHERE user_id = ?", (clan_id, applicant_id))
        cursor.execute("DELETE FROM clan_applications WHERE user_id = ?", (applicant_id,))
        conn.commit()
        return "✅ Заявка принята! Игрок зачислен в клан."
    elif action == "reject":
        cursor.execute("DELETE FROM clan_applications WHERE application_id = ?", (application_id,))
        conn.commit()
        return "❌ Заявка отклонена."
    else:
        return "❌ Неизвестное действие!"

def disband_clan(actor_id):
    actor = get_db_user(actor_id)
    if not actor or actor["clan_role"] != "leader":
        return "❌ Только лидер может расформировать клан!"
    
    clan_id = actor["clan_id"]
    cursor.execute("UPDATE users SET clan_id = NULL, clan_role = NULL WHERE clan_id = ?", (clan_id,))
    cursor.execute("DELETE FROM clan_applications WHERE clan_id = ?", (clan_id,))
    cursor.execute("DELETE FROM clans WHERE clan_id = ?", (clan_id,))
    conn.commit()
    return "💥 Клан был успешно расформирован."

def get_clan_info(clan_id):
    clan = get_clan_by_id(clan_id)
    if not clan:
        return "❌ Клан не найден!"
    
    members = get_clan_members(clan_id)
    leader = get_db_user(clan["leader_id"])
    leader_name = leader["username"] if leader else "Неизвестно"
    
    info = f"🛡️ **Клан [{clan['tag']}] {clan['name']}**\n"
    info += f"👑 Лидер: {leader_name}\n"
    info += f"📊 Уровень: {clan['level']} (XP: {clan['xp']}/{clan['level'] * 1000})\n"
    info += f"👥 Участники: {len(members)}/{clan['max_members']}\n"
    info += f"🔒 Тип: {'Открытый' if clan['type'] == 'open' else 'Закрытый'}\n\n"
    info += "📜 Список участников:\n"
    
    for member in members:
        role_symbol = "👑" if member["clan_role"] == "leader" else ("⭐" if member["clan_role"] == "deputy" else "🔹")
        info += f"{role_symbol} {member['username']} (Ур. {member['level']})\n"
        
    return info

def get_my_clan_info(user_id):
    user = get_db_user(user_id)
    if not user or user["clan_id"] is None:
        return "❌ Вы не состоите в клане!"
    return get_clan_info(user["clan_id"])

def list_clans_text():
    clans = get_all_clans()
    if not clans:
        return "🛡️ В игре пока нет ни одного клана."
    
    text = "📜 **Список кланов в игре:**\n\n"
    for clan in clans:
        count = get_clan_members_count(clan["clan_id"])
        type_str = "Открытый" if clan["type"] == "open" else "Закрытый"
        text += f"▪️ ID: {clan['clan_id']} | [{clan['tag']}] **{clan['name']}** | Ур. {clan['level']} | Мест: {count}/{clan['max_members']} | Тип: {type_str}\n"
    return text

def get_clan_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🛡️ Мой клан"),
        KeyboardButton("📜 Список кланов"),
        KeyboardButton("➕ Создать клан"),
        KeyboardButton("🚪 Покинуть клан"),
        KeyboardButton("Назад")
    )
    return markup

def update_activity(user_id):
    if user_id in players:
        players[user_id]['last_activity'] = time.time()

def init_user(user_id, name, username=None):
    uname = username or name
    sync_user_db(user_id, uname)
    check_quest_reset(user_id)
    db_user = get_db_user(user_id)
    
    if user_id not in players:
        players[user_id] = {
            'name': name,
            'username': uname,
            'hp': 100,
            'max_hp': 100 + (db_user['level'] - 1) * 10,
            'opponent': None,
            'is_defending': False,
            'is_turn': False,
            'inventory': ['Зелье лечения', 'Зелье лечения'],
            'level': db_user['level'],
            'xp': db_user['xp'],
            'coins': db_user['coins'],
            'wins': 0,
            'losses': 0,
            'menu_page': 1,
            'mines_game': None,
            'last_activity': time.time(),
            'tower_floor': db_user['tower_floor']
        }
    else:
        players[user_id]['name'] = name
        players[user_id]['username'] = uname
        players[user_id]['level'] = db_user['level']
        players[user_id]['xp'] = db_user['xp']
        players[user_id]['coins'] = db_user['coins']
        players[user_id]['tower_floor'] = db_user['tower_floor']
        players[user_id]['last_activity'] = time.time()
        if 'menu_page' not in players[user_id]:
            players[user_id]['menu_page'] = 1
        if 'mines_game' not in players[user_id]:
            players[user_id]['mines_game'] = None

def add_xp_and_coins(user_id, xp_gain, coins_gain):
    p = players[user_id]
    p['coins'] += coins_gain
    
    leveled_up = False
    if p['level'] < 10:
        p['xp'] += xp_gain
        while p['xp'] >= 100 and p['level'] < 10:
            p['xp'] -= 100
            p['level'] += 1
            p['max_hp'] += 10
            leveled_up = True
            
        if p['level'] == 10 and p['xp'] > 100:
            p['xp'] = 100
    else:
        p['xp'] = 100

    cursor.execute("UPDATE users SET level = ?, xp = ?, coins = ? WHERE user_id = ?", (p['level'], p['xp'], p['coins'], user_id))
    conn.commit()
    
    db_user = get_db_user(user_id)
    if db_user and db_user["clan_id"] is not None:
        add_clan_xp(db_user["clan_id"], xp_gain)

    return leveled_up

def increment_quest_battle(user_id):
    check_quest_reset(user_id)
    cursor.execute("UPDATE users SET quest_battles = quest_battles + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def increment_quest_casino(user_id):
    check_quest_reset(user_id)
    cursor.execute("UPDATE users SET quest_casino = quest_casino + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def get_progress_bar(xp):
    percent = min(100, max(0, xp))
    filled = percent // 10
    empty = 10 - filled
    return "█" * filled + "░" * empty + f" {percent}%"

def get_main_menu(page=1):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if page == 1:
        markup.add(
            KeyboardButton("В бой!"),
            KeyboardButton("🏰 Башня"),
            KeyboardButton("🎰 Казино"),
            KeyboardButton("Инвентарь"),
            KeyboardButton("👤 Профиль"),
            KeyboardButton("➡️ Вперед")
        )
    else:
        markup.add(
            KeyboardButton("📜 Квесты"),
            KeyboardButton("👹 Рейд на Тирана"),
            KeyboardButton("🏆 Топ"),
            KeyboardButton("🛡️ Кланы"),
            KeyboardButton("⬅️ Назад")
        )
    return markup

def get_casino_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🎲 Кости"),
        KeyboardButton("💣 Мины 4х3"),
        KeyboardButton("Назад")
    )
    return markup

def get_battle_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("Атака"),
        KeyboardButton("Защита"),
        KeyboardButton("Инвентарь"),
        KeyboardButton("🚪 Покинуть рейд"),
        KeyboardButton("🏳️ Сдаться")
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
        title = "🏆 **Таблица лидеров по рангу**\n\n"
    else:
        sorted_p = sorted(all_players, key=lambda x: (x['wins'], x['level']), reverse=True)
        title = "⚔️ **Таблица лидеров по победам**\n\n"

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

    increment_quest_battle(winner_id)
    increment_quest_battle(loser_id)

    leveled_up = add_xp_and_coins(winner_id, 10, 20)

    for uid in (winner_id, loser_id):
        players[uid]['opponent'] = None
        players[uid]['hp'] = players[uid]['max_hp']
        players[uid]['is_defending'] = False
        players[uid]['is_turn'] = False

    win_msg = "🏆 **Вы победили!**\nНаграда: +10 XP, +20 монет 💰\nЗдоровье восстановлено."
    if leveled_up:
        new_lvl = players[winner_id]['level']
        new_rank = RANKS.get(new_lvl, "Абсолют")
        win_msg += f"\n\n🎉 **ПОЗДРАВЛЯЕМ!** Вы повысили уровень до {new_lvl} ({new_rank})!"

    bot.send_message(winner_id, win_msg, reply_markup=get_main_menu(players[winner_id]['menu_page']), parse_mode="Markdown")
    bot.send_message(loser_id, "☠️ **Вы проиграли!**\nЗдоровье восстановлено.", reply_markup=get_main_menu(players[loser_id]['menu_page']), parse_mode="Markdown")

def auto_kick_afk_loop():
    while True:
        try:
            now = time.time()
            for user_id, pdata in list(players.items()):
                if pdata.get('opponent') is not None:
                    last_act = pdata.get('last_activity', now)
                    if now - last_act >= 60:
                        opponent_id = pdata['opponent']
                        players[user_id]['losses'] += 1
                        players[opponent_id]['wins'] += 1
                        
                        leveled_up = add_xp_and_coins(opponent_id, 10, 20)
                        
                        for uid in (user_id, opponent_id):
                            players[uid]['opponent'] = None
                            players[uid]['hp'] = players[uid]['max_hp']
                            players[uid]['is_defending'] = False
                            players[uid]['is_turn'] = False
                            
                        bot.send_message(user_id, "⏱️ **Вы были исключены из боя за АФК (не было действий 60 сек)!**\nВам засчитано поражение.", reply_markup=get_main_menu(players[user_id]['menu_page']), parse_mode="Markdown")
                        
                        win_msg = "🏆 **Противник был исключен за АФК! Вы победили!**\nНаграда: +10 XP, +20 монет 💰\nЗдоровье восстановлено."
                        if leveled_up:
                            new_lvl = players[opponent_id]['level']
                            new_rank = RANKS.get(new_lvl, "Абсолют")
                            win_msg += f"\n\n🎉 **ПОЗДРАВЛЯЕМ!** Вы повысили уровень до {new_lvl} ({new_rank})!"
                        bot.send_message(opponent_id, win_msg, reply_markup=get_main_menu(players[opponent_id]['menu_page']), parse_mode="Markdown")
        except Exception:
            pass
        time.sleep(5)

@bot.message_handler(commands=['ahelp'])
def admin_help(message):
    if message.chat.id != ADMIN_ID:
        return
    help_text = (
        "👑 **Панель Администратора**\n\n"
        "`/addxp @user/ID <кол-во>` — Выдать опыт игроку\n"
        "`/addcoins @user/ID <кол-во>` — Выдать монеты игроку\n"
        "`/mute [время] @user/ID` — Заблокировать чат (Пример: `/mute 30m @user`)\n"
        "`/unmute @user/ID` — Снять блокировку чата\n"
        "`/ban [время] @user/ID` — Заблокировать игрока (Пример: `/ban 30m @user`)\n"
        "`/unban @user/ID` — Разблокировать игрока\n"
        "`/setlevel @user/ID <уровень>` — Установить уровень (1-10)\n"
        "`/stats` — Статистика пользователей базы данных"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['addxp'])
def admin_add_xp(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 2 or not args[1].isdigit():
        bot.send_message(message.chat.id, "❌ Использование: `/addxp @user/ID <кол-во>`", parse_mode="Markdown")
        return
    
    target_id = find_target_user(args[0])
    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден!")
        return
    
    amount = int(args[1])
    init_user(target_id, "Игрок")
    leveled_up = add_xp_and_coins(target_id, amount, 0)
    
    msg = f"✅ Выдали {amount} XP игроку {args[0]}."
    if leveled_up:
        msg += f" Игрок повысил уровень до {players[target_id]['level']}!"
    bot.send_message(message.chat.id, msg)
    try:
        bot.send_message(target_id, f"🎁 Администратор выдал вам {amount} XP!")
    except Exception:
        pass

@bot.message_handler(commands=['addcoins'])
def admin_add_coins(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 2 or not args[1].isdigit():
        bot.send_message(message.chat.id, "❌ Использование: `/addcoins @user/ID <кол-во>`", parse_mode="Markdown")
        return
    
    target_id = find_target_user(args[0])
    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден!")
        return
    
    amount = int(args[1])
    init_user(target_id, "Игрок")
    add_xp_and_coins(target_id, 0, amount)
    
    bot.send_message(message.chat.id, f"✅ Выдали {amount} монет игроку {args[0]}.")
    try:
        bot.send_message(target_id, f"💰 Администратор выдал вам {amount} монет!")
    except Exception:
        pass

@bot.message_handler(commands=['mute'])
def admin_mute(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 1:
        bot.send_message(message.chat.id, "❌ Использование: `/mute [время] @user/ID` (Пример: `/mute 30m @user`)", parse_mode="Markdown")
        return
    
    duration_seconds = 0
    target_str = ""
    
    if len(args) >= 2:
        parsed = parse_duration(args[0])
        if parsed > 0:
            duration_seconds = parsed
            target_str = args[1]
        else:
            target_str = args[0]
            duration_seconds = parse_duration(args[1])
    else:
        target_str = args[0]
        
    target_id = find_target_user(target_str)
    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден!")
        return
    
    muted_until = int(time.time()) + duration_seconds if duration_seconds > 0 else 0
    cursor.execute("UPDATE users SET is_muted = 1, muted_until = ? WHERE user_id = ?", (muted_until, target_id))
    conn.commit()
    
    time_str = f" на {format_time_remaining(duration_seconds)}" if duration_seconds > 0 else " навсегда"
    bot.send_message(message.chat.id, f"🔇 Игрок {target_str} заблокирован в чате{time_str}.")
    try:
        bot.send_message(target_id, f"🔇 Вы получили мутв чате{time_str}.")
    except Exception:
        pass

@bot.message_handler(commands=['unmute'])
def admin_unmute(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 1:
        bot.send_message(message.chat.id, "❌ Использование: `/unmute @user/ID`", parse_mode="Markdown")
        return
    
    target_id = find_target_user(args[0])
    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден!")
        return
    
    cursor.execute("UPDATE users SET is_muted = 0, muted_until = 0 WHERE user_id = ?", (target_id,))
    conn.commit()
    bot.send_message(message.chat.id, f"🔊 Мут снят с игрока {args[0]}.")
    try:
        bot.send_message(target_id, "🔊 Администратор снял с вас мут в чате.")
    except Exception:
        pass

@bot.message_handler(commands=['ban'])
def admin_ban(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 1:
        bot.send_message(message.chat.id, "❌ Использование: `/ban [время] @user/ID` (Пример: `/ban 30m @user`)", parse_mode="Markdown")
        return
    
    duration_seconds = 0
    target_str = ""
    
    if len(args) >= 2:
        parsed = parse_duration(args[0])
        if parsed > 0:
            duration_seconds = parsed
            target_str = args[1]
        else:
            target_str = args[0]
            duration_seconds = parse_duration(args[1])
    else:
        target_str = args[0]
        
    target_id = find_target_user(target_str)
    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден!")
        return
    
    banned_until = int(time.time()) + duration_seconds if duration_seconds > 0 else 0
    cursor.execute("UPDATE users SET is_banned = 1, banned_until = ? WHERE user_id = ?", (banned_until, target_id))
    conn.commit()
    
    time_str = f" на {format_time_remaining(duration_seconds)}" if duration_seconds > 0 else " навсегда"
    bot.send_message(message.chat.id, f"⛔ Игрок {target_str} заблокирован в боте{time_str}.")
    try:
        bot.send_message(target_id, f"⛔ Вы были заблокированы администратором{time_str}.")
    except Exception:
        pass

@bot.message_handler(commands=['unban'])
def admin_unban(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 1:
        bot.send_message(message.chat.id, "❌ Использование: `/unban @user/ID`", parse_mode="Markdown")
        return
    
    target_id = find_target_user(args[0])
    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден!")
        return
    
    cursor.execute("UPDATE users SET is_banned = 0, banned_until = 0 WHERE user_id = ?", (target_id,))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ Разблокирован игрок {args[0]}.")
    try:
        bot.send_message(target_id, "✅ Ваш аккаунт в боте разблокирован.")
    except Exception:
        pass

@bot.message_handler(commands=['setlevel'])
def admin_setlevel(message):
    if message.chat.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 2 or not args[1].isdigit():
        bot.send_message(message.chat.id, "❌ Использование: `/setlevel @user/ID <уровень>`", parse_mode="Markdown")
        return
    
    target_id = find_target_user(args[0])
    if not target_id:
        bot.send_message(message.chat.id, "❌ Игрок не найден!")
        return
    
    new_lvl = max(1, min(10, int(args[1])))
    init_user(target_id, "Игрок")
    players[target_id]['level'] = new_lvl
    players[target_id]['max_hp'] = 100 + (new_lvl - 1) * 10
    
    cursor.execute("UPDATE users SET level = ? WHERE user_id = ?", (new_lvl, target_id))
    conn.commit()
    
    bot.send_message(message.chat.id, f"✅ Игроку {args[0]} установлен {new_lvl} уровень.")
    try:
        bot.send_message(target_id, f"⭐ Ваш уровень изменен администратором на {new_lvl}!")
    except Exception:
        pass

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.chat.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM clans")
    total_clans = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    banned_users = cursor.fetchone()[0]
    
    stats_msg = (
        "📊 **Статистика сервера**\n\n"
        f"Всего игроков: {total_users}\n"
        f"Всего кланов: {total_clans}\n"
        f"Заблокировано пользователей: {banned_users}"
    )
    bot.send_message(message.chat.id, stats_msg, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start_game(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    init_user(message.chat.id, message.from_user.first_name, message.from_user.username)
    players[message.chat.id]['menu_page'] = 1
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! Готов к сражениям?",
        reply_markup=get_main_menu(1)
    )

@bot.message_handler(func=lambda message: message.text in ["➡️ Вперед", "⬅️ Назад"])
def toggle_main_menu(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    
    if message.text == "➡️ Вперед":
        players[user_id]['menu_page'] = 2
        bot.send_message(user_id, "Меню (Страница 2):", reply_markup=get_main_menu(2))
    elif message.text == "⬅️ Назад":
        players[user_id]['menu_page'] = 1
        bot.send_message(user_id, "Главное меню (Страница 1):", reply_markup=get_main_menu(1))

@bot.message_handler(func=lambda message: message.text in ["🎰 Казино", "Казино"])
def open_casino(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    bot.send_message(user_id, "🎰 **Добро пожаловать в Казино!**\nВыберите режим игры:", reply_markup=get_casino_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ["🎲 Кости", "Кости"])
def select_dice(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    user_states[user_id] = 'awaiting_dice_bet'
    bot.send_message(user_id, f"🎲 **Режим: Кости**\nВаш баланс: 💰 {players[user_id]['coins']} монет.\n\nВведите сумму ставки:", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ["💣 Мины 4х3", "Мины 4х3", "Мины"])
def select_mines(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    user_states[user_id] = 'awaiting_mines_bet'
    bot.send_message(user_id, f"💣 **Режим: Мины (Поле 4х3)**\nВаш баланс: 💰 {players[user_id]['coins']} монет.\n\nВведите сумму ставки:", parse_mode="Markdown")

def render_mines_keyboard(game_data, reveal_all=False):
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = []
    board = game_data['board']
    opened = game_data['opened']
    
    for i in range(12):
        if i in opened or reveal_all:
            if board[i] == 'M':
                btn_text = "💥"
            else:
                btn_text = "💎"
            callback = "ignore"
        else:
            btn_text = "❓"
            callback = f"mine:{i}"
        buttons.append(InlineKeyboardButton(btn_text, callback_data=callback))
    
    markup.add(*buttons[0:3])
    markup.add(*buttons[3:6])
    markup.add(*buttons[6:9])
    markup.add(*buttons[9:12])
    
    if not reveal_all and len(opened) > 0:
        markup.add(InlineKeyboardButton(f"💰 Забрать {int(game_data['current_win'])} монет", callback_data="mines_cashout"))
        
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("mine:") or call.data == "mines_cashout")
def handle_mines_callback(call):
    user_id = call.message.chat.id
    if is_user_banned(user_id):
        rem = get_ban_remaining(user_id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.answer_callback_query(call.id, f"⛔ Вы заблокированы.{time_str}")
        return
        
    init_user(user_id, call.from_user.first_name, call.from_user.username)
    game = players[user_id].get('mines_game')
    
    if not game:
        bot.answer_callback_query(call.id, "Игра не найдена.")
        return
        
    if call.data == "mines_cashout":
        win_amount = int(game['current_win'])
        add_xp_and_coins(user_id, 0, win_amount)
        increment_quest_casino(user_id)
        players[user_id]['mines_game'] = None
        bot.edit_message_text(f"🎉 **Вы забрали выигрыш!**\nВы выиграли: 💰 {win_amount} монет!", user_id, call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        return
        
    cell_idx = int(call.data.split(":")[1])
    if cell_idx in game['opened']:
        bot.answer_callback_query(call.id)
        return
        
    if game['board'][cell_idx] == 'M':
        increment_quest_casino(user_id)
        players[user_id]['mines_game'] = None
        markup = render_mines_keyboard(game, reveal_all=True)
        bot.edit_message_text(f"💥 **БОМБА!** Вы подорвались на мине.\nПотеряно: 💰 {game['bet']} монет.", user_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
    else:
        game['opened'].append(cell_idx)
        safe_opened = len(game['opened'])
        multipliers = [1.2, 1.5, 2.0, 2.8, 4.0, 6.0, 9.0, 15.0, 25.0]
        mult = multipliers[min(safe_opened - 1, len(multipliers) - 1)]
        game['current_win'] = game['bet'] * mult
        
        if safe_opened == 9:
            win_amount = int(game['current_win'])
            add_xp_and_coins(user_id, 0, win_amount)
            increment_quest_casino(user_id)
            players[user_id]['mines_game'] = None
            markup = render_mines_keyboard(game, reveal_all=True)
            bot.edit_message_text(f"🏆 **НЕВЕРОЯТНО!** Вы открыли все безопасные ячейки!\nВыигрыш: 💰 {win_amount} монет!", user_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            markup = render_mines_keyboard(game, reveal_all=False)
            bot.edit_message_text(f"💣 **Мины 4х3**\nОткрыто безопасных ячеек: {safe_opened}/9\nТекущий выигрыш: 💰 {int(game['current_win'])} монет", user_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text in ["🏰 Башня", "Башня"])
def tower_menu(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    p = players[user_id]
    
    floor = p['tower_floor']
    enemy_hp = 80 + (floor - 1) * 30
    enemy_dmg = 10 + (floor - 1) * 5
    reward_coins = 30 + floor * 15
    reward_xp = 15 + floor * 5
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"⚔️ Сразиться на {floor} этаже", callback_data="tower_fight"))
    
    msg = (
        f"🏰 **Башня Испытаний**\n\n"
        f"Ваш текущий этаж: **{floor}**\n"
        f"👾 Враг этажа: Страж этажа #{floor}\n"
        f"❤️ HP Врага: {enemy_hp} | ⚔️ Урон Врага: {enemy_dmg}\n\n"
        f"🎁 Награда за победу: 💰 {reward_coins} монет, 🔥 {reward_xp} XP"
    )
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "tower_fight")
def tower_fight_callback(call):
    user_id = call.message.chat.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "⛔ Вы заблокированы.")
        return
    init_user(user_id, call.from_user.first_name, call.from_user.username)
    p = players[user_id]
    
    floor = p['tower_floor']
    enemy_hp = 80 + (floor - 1) * 30
    enemy_dmg = 10 + (floor - 1) * 5
    player_hp = p['max_hp']
    
    battle_log = f"🏰 **Битва на {floor} этаже Башни!**\n\n"
    
    round_num = 1
    while player_hp > 0 and enemy_hp > 0:
        p_dmg = random.randint(15, 25) + (p['level'] * 3)
        enemy_hp -= p_dmg
        battle_log += f"Раунд {round_num}: Вы нанесли {p_dmg} урона. (HP Врага: {max(0, enemy_hp)})\n"
        
        if enemy_hp <= 0:
            break
            
        e_dmg = random.randint(enemy_dmg - 3, enemy_dmg + 3)
        player_hp -= e_dmg
        battle_log += f"Страж ответил ударом на {e_dmg} урона! (Ваше HP: {max(0, player_hp)})\n"
        round_num += 1
        
    if player_hp > 0:
        reward_coins = 30 + floor * 15
        reward_xp = 15 + floor * 5
        p['tower_floor'] += 1
        cursor.execute("UPDATE users SET tower_floor = ? WHERE user_id = ?", (p['tower_floor'], user_id))
        conn.commit()
        
        leveled_up = add_xp_and_coins(user_id, reward_xp, reward_coins)
        battle_log += f"\n🎉 **Победа!** Вы прошли {floor} этаж!\nПолучено: 💰 {reward_coins} монет, 🔥 {reward_xp} XP!"
        if leveled_up:
            battle_log += f"\n🎉 **Уровень повышен до {p['level']}!**"
    else:
        battle_log += f"\n☠️ **Вы пали в бою на {floor} этаже.** Попробуйте прокачаться и вернуться снова!"
        
    bot.edit_message_text(battle_log, user_id, call.message.message_id, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text in ["📜 Квесты", "Квесты"])
def show_quests(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    db_user = get_db_user(user_id)
    
    battles = db_user['quest_battles']
    casino = db_user['quest_casino']
    claimed = db_user['quest_claimed']
    
    status_b = "✅ Выполнено" if battles >= 3 else f"⏳ {battles}/3"
    status_c = "✅ Выполнено" if casino >= 2 else f"⏳ {casino}/2"
    
    msg = (
        f"📜 **Ежедневные Квесты**\n\n"
        f"1. Сыграть 3 боя в дуэлях: {status_b}\n"
        f"2. Сыграть 2 раза в казино: {status_c}\n\n"
        f"🎁 Награда за выполнение всех квестов: 💰 100 монет, 🔥 50 XP"
    )
    
    markup = InlineKeyboardMarkup()
    if battles >= 3 and casino >= 2:
        if claimed == 0:
            markup.add(InlineKeyboardButton("🎁 Забрать награду", callback_data="claim_quests"))
        else:
            markup.add(InlineKeyboardButton("✅ Награда получена", callback_data="ignore"))
            
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "claim_quests")
def claim_quests_callback(call):
    user_id = call.message.chat.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "⛔ Вы заблокированы.")
        return
    db_user = get_db_user(user_id)
    if db_user['quest_battles'] >= 3 and db_user['quest_casino'] >= 2 and db_user['quest_claimed'] == 0:
        cursor.execute("UPDATE users SET quest_claimed = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        add_xp_and_coins(user_id, 50, 100)
        bot.edit_message_text("🎁 **Вы успешно получили награду за ежедневные квесты:** +100 монет 💰 и +50 XP 🔥!", user_id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "Квесты еще не выполнены или награда уже забрана!")

@bot.message_handler(func=lambda message: message.text in ["👹 Рейд на Тирана", "Рейд на Тирана", "Тиран"])
def tyrant_raid_menu(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    
    status = "Актвен" if tyrant_boss['is_alive'] else "Повержен"
    
    msg = (
        f"👹 **Мировой Босс: Древний Тиран**\n\n"
        f"Статус: **{status}**\n"
        f"Уровень босса: **{tyrant_boss['level']}**\n"
        f"❤️ HP Босса: **{tyrant_boss['hp']} / {tyrant_boss['max_hp']}**\n\n"
        f"Каждая атака наносит случайный урон боссу и приносит золото и опыт!"
    )
    
    markup = InlineKeyboardMarkup()
    if tyrant_boss['is_alive']:
        markup.add(InlineKeyboardButton("⚔️ Атаковать Тирана", callback_data="attack_tyrant"))
    else:
        markup.add(InlineKeyboardButton("🔄 Возродить Тирана", callback_data="respawn_tyrant"))
        
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["attack_tyrant", "respawn_tyrant"])
def tyrant_action_callback(call):
    user_id = call.message.chat.id
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "⛔ Вы заблокированы.")
        return
    init_user(user_id, call.from_user.first_name, call.from_user.username)
    p = players[user_id]
    
    if call.data == "respawn_tyrant":
        if not tyrant_boss['is_alive']:
            tyrant_boss['level'] += 1
            tyrant_boss['max_hp'] = 50000 * tyrant_boss['level']
            tyrant_boss['hp'] = tyrant_boss['max_hp']
            tyrant_boss['is_alive'] = True
            bot.answer_callback_query(call.id, "👹 Тиран возродился и стал сильнее!")
            tyrant_raid_menu(call.message)
            return
        else:
            bot.answer_callback_query(call.id, "Тиран еще жив!")
            return

    if not tyrant_boss['is_alive']:
        bot.answer_callback_query(call.id, "Тиран повержен! Возродите его.")
        return
        
    dmg = random.randint(100, 300) + (p['level'] * 20)
    tyrant_boss['hp'] -= dmg
    coins = dmg // 5
    xp = dmg // 10
    
    add_xp_and_coins(user_id, xp, coins)
    
    if tyrant_boss['hp'] <= 0:
        tyrant_boss['hp'] = 0
        tyrant_boss['is_alive'] = False
        msg = f"💥 **ЛЕГЕНДАРНО!** Вы нанесли последний удар ({dmg} урона) и добили **Тирана**!\nВам вручена супернаграда: 💰 1000 монет и 🔥 500 XP!"
        add_xp_and_coins(user_id, 500, 1000)
    else:
        msg = f"⚔️ Вы нанесли Тирану **{dmg}** урона!\nПолучено: 💰 {coins} монет, 🔥 {xp} XP!\nОсталось HP у Тирана: **{tyrant_boss['hp']}/{tyrant_boss['max_hp']}**"
        
    markup = InlineKeyboardMarkup()
    if tyrant_boss['is_alive']:
        markup.add(InlineKeyboardButton("⚔️ Атаковать снова", callback_data="attack_tyrant"))
    else:
        markup.add(InlineKeyboardButton("🔄 Возродить Тирана", callback_data="respawn_tyrant"))
        
    bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text in ["👤 Профиль", "Профиль"])
def show_profile(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    p = players[user_id]
    db_user = get_db_user(user_id)

    rank_name = RANKS.get(p['level'], "Абсолют")
    username_str = f"@{p['username']}" if p.get('username') else p['name']

    clan_str = "Нет"
    if db_user and db_user["clan_id"] is not None:
        clan = get_clan_by_id(db_user["clan_id"])
        if clan:
            clan_str = f"[{clan['tag']}] {clan['name']}"

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
        f"Клан: {clan_str}\n"
        f"Ранг: 🔥 {rank_name} ({p['level']} уровень)\n"
        f"Этаж в Башне: 🏰 {p['tower_floor']}\n"
        f"Монеты: 💰 {p['coins']}\n"
        f"Победы: {p['wins']} | Поражения: {p['losses']}\n"
        f"Опыт: {xp_str}\n"
        f"Прогресс: {progress_str}\n"
        f"До следующего ранга: {left_str}"
    )

    bot.send_message(user_id, profile_text, reply_markup=get_main_menu(p['menu_page']))

@bot.message_handler(func=lambda message: message.text in ["🏆 Топ", "Топ"])
def show_top(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    text, markup = generate_leaderboard('rank', 1)
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ["🛡️ Кланы", "Кланы"])
def show_clan_menu(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    bot.send_message(user_id, "🛡️ **Клановое меню**\nВыберите действие или используйте команды:\n/create_clan <Имя> <Тэг>\n/join_clan <Имя/Тэг/ID>\n/kick <ID>\n/promote <ID>\n/demote <ID>\n/transfer <ID>\n/set_type <open/closed>\n/apps\n/app_accept <ID>\n/app_reject <ID>\n/disband_clan", reply_markup=get_clan_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🛡️ Мой клан")
def show_my_clan(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    res = get_my_clan_info(user_id)
    bot.send_message(user_id, res, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📜 Список кланов")
def show_clans_list(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    res = list_clans_text()
    bot.send_message(user_id, res, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "➕ Создать клан")
def create_clan_hint(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    bot.send_message(message.chat.id, "Для создания клана отправьте команду:\n`/create_clan ИмяКлана ТЭГ`\nПример: `/create_clan Templars TMP`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🚪 Покинуть клан")
def leave_clan_cmd(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    res = leave_clan(user_id)
    bot.send_message(user_id, res)

@bot.message_handler(commands=['create_clan'])
def cmd_create_clan(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.send_message(user_id, "❌ Использование: `/create_clan <Название> <Тэг>`", parse_mode="Markdown")
        return
    clan_name = args[0]
    clan_tag = args[1]
    res = create_clan(user_id, clan_name, clan_tag)
    bot.send_message(user_id, res, parse_mode="Markdown")

@bot.message_handler(commands=['join_clan'])
def cmd_join_clan(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 1:
        bot.send_message(user_id, "❌ Использование: `/join_clan <Название/Тэг/ID>`", parse_mode="Markdown")
        return
    identifier = args[0]
    res = join_clan(user_id, identifier)
    bot.send_message(user_id, res, parse_mode="Markdown")

@bot.message_handler(commands=['kick'])
def cmd_kick(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 1 or not args[0].isdigit():
        bot.send_message(user_id, "❌ Использование: `/kick <User_ID>`", parse_mode="Markdown")
        return
    res = kick_member(user_id, int(args[0]))
    bot.send_message(user_id, res)

@bot.message_handler(commands=['promote'])
def cmd_promote(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 1 or not args[0].isdigit():
        bot.send_message(user_id, "❌ Использование: `/promote <User_ID>`", parse_mode="Markdown")
        return
    res = promote_member(user_id, int(args[0]))
    bot.send_message(user_id, res)

@bot.message_handler(commands=['demote'])
def cmd_demote(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 1 or not args[0].isdigit():
        bot.send_message(user_id, "❌ Использование: `/demote <User_ID>`", parse_mode="Markdown")
        return
    res = demote_member(user_id, int(args[0]))
    bot.send_message(user_id, res)

@bot.message_handler(commands=['transfer'])
def cmd_transfer(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 1 or not args[0].isdigit():
        bot.send_message(user_id, "❌ Использование: `/transfer <User_ID>`", parse_mode="Markdown")
        return
    res = transfer_leadership(user_id, int(args[0]))
    bot.send_message(user_id, res)

@bot.message_handler(commands=['set_type'])
def cmd_set_type(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 1:
        bot.send_message(user_id, "❌ Использование: `/set_type <open/closed>`", parse_mode="Markdown")
        return
    res = set_clan_type(user_id, args[0].lower())
    bot.send_message(user_id, res, parse_mode="Markdown")

@bot.message_handler(commands=['apps'])
def cmd_apps(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    res = get_clan_applications(user_id)
    bot.send_message(user_id, res, parse_mode="Markdown")

@bot.message_handler(commands=['app_accept'])
def cmd_app_accept(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 1 or not args[0].isdigit():
        bot.send_message(user_id, "❌ Использование: `/app_accept <Application_ID>`", parse_mode="Markdown")
        return
    res = process_application(user_id, int(args[0]), "accept")
    bot.send_message(user_id, res)

@bot.message_handler(commands=['app_reject'])
def cmd_app_reject(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    args = message.text.split()[1:]
    if len(args) < 1 or not args[0].isdigit():
        bot.send_message(user_id, "❌ Использование: `/app_reject <Application_ID>`", parse_mode="Markdown")
        return
    res = process_application(user_id, int(args[0]), "reject")
    bot.send_message(user_id, res)

@bot.message_handler(commands=['disband_clan'])
def cmd_disband_clan(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    res = disband_clan(user_id)
    bot.send_message(user_id, res)

@bot.callback_query_handler(func=lambda call: call.data.startswith("top:"))
def handle_top_callback(call):
    if is_user_banned(call.message.chat.id):
        rem = get_ban_remaining(call.message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.answer_callback_query(call.id, f"⛔ Вы заблокированы.{time_str}")
        return
    parts = call.data.split(":")
    lb_type = parts[1]
    page = int(parts[2])
    text, markup = generate_leaderboard(lb_type, page)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ignore")
def handle_ignore_callback(call):
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == "В бой!")
def search_opponent(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
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
        
        players[user_id]['last_activity'] = time.time()
        players[opponent_id]['last_activity'] = time.time()

        for uid in (user_id, opponent_id):
            enemy_name = players[players[uid]['opponent']]['name']
            msg = f"Противник найден: {enemy_name}!\n"
            msg += "Ваш ход!" if players[uid]['is_turn'] else "Ход противника, ожидайте..."
            bot.send_message(uid, msg, reply_markup=get_battle_menu())
    else:
        queue.append(user_id)
        bot.send_message(user_id, "Поиск противника... Ожидайте.")

@bot.message_handler(func=lambda message: message.text == "Атака")
def attack(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    update_activity(user_id)
    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu(players[user_id]['menu_page']))
        return

    if not players[user_id]['is_turn']:
        bot.send_message(user_id, "Сейчас не ваш ход!")
        return

    opponent_id = players[user_id]['opponent']
    damage = random.randint(15, 25)

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
        players[opponent_id]['last_activity'] = time.time()
        bot.send_message(opponent_id, "Ваш ход! Выберите действие.")

@bot.message_handler(func=lambda message: message.text == "Защита")
def defend(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    update_activity(user_id)
    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu(players[user_id]['menu_page']))
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
    players[opponent_id]['last_activity'] = time.time()

@bot.message_handler(func=lambda message: message.text in ["🚪 Покинуть рейд", "Покинуть рейд"])
def leave_raid(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    update_activity(user_id)
    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu(players[user_id]['menu_page']))
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

    win_msg = "🏆 **Противник покинул рейд! Вы победили!**\nНаграда: +10 XP, +20 монет 💰\nЗдоровье восстановлено."
    if leveled_up:
        new_lvl = players[opponent_id]['level']
        new_rank = RANKS.get(new_lvl, "Абсолют")
        win_msg += f"\n\n🎉 **ПОЗДРАВЛЯЕМ!** Вы повысили уровень до {new_lvl} ({new_rank})!"

    bot.send_message(opponent_id, win_msg, reply_markup=get_main_menu(players[opponent_id]['menu_page']), parse_mode="Markdown")
    bot.send_message(user_id, "🚪 **Вы покинули рейд!** Засчитано поражение.\nЗдоровье восстановлено.", reply_markup=get_main_menu(players[user_id]['menu_page']), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ["🏳️ Сдаться", "Сдаться"])
def surrender(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    update_activity(user_id)
    if user_id not in players or players[user_id]['opponent'] is None:
        bot.send_message(user_id, "Вы сейчас не в бою.", reply_markup=get_main_menu(players[user_id]['menu_page']))
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

    win_msg = "🏆 **Противник сдался! Вы победили!**\nНаграда: +10 XP, +20 монет 💰\nЗдоровье восстановлено."
    if leveled_up:
        new_lvl = players[opponent_id]['level']
        new_rank = RANKS.get(new_lvl, "Абсолют")
        win_msg += f"\n\n🎉 **ПОЗДРАВЛЯЕМ!** Вы повысили уровень до {new_lvl} ({new_rank})!"

    bot.send_message(opponent_id, win_msg, reply_markup=get_main_menu(players[opponent_id]['menu_page']), parse_mode="Markdown")
    bot.send_message(user_id, "🏳️ **Вы сдались!** Засчитано поражение.\nЗдоровье восстановлено.", reply_markup=get_main_menu(players[user_id]['menu_page']), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "Инвентарь")
def inventory(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
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
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    init_user(user_id, message.from_user.first_name, message.from_user.username)
    user_states.pop(user_id, None)
    if players[user_id]['opponent'] is not None:
        bot.send_message(user_id, "Вы вернулись в меню боя:", reply_markup=get_battle_menu())
    else:
        bot.send_message(user_id, "Главное меню:", reply_markup=get_main_menu(players[user_id]['menu_page']))

@bot.message_handler(func=lambda message: message.text.startswith("Использовать: "))
def use_item(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    user_id = message.chat.id
    update_activity(user_id)
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
                players[opponent_id]['last_activity'] = time.time()
                bot.send_message(opponent_id, "Противник потратил ход на зелье.\nВаш ход!")
        else:
            bot.send_message(user_id, "Этот предмет нельзя использовать.")
    else:
        bot.send_message(user_id, "У вас больше нет этого предмета!")

@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_bets_input(message):
    user_id = message.chat.id
    if is_user_banned(user_id):
        rem = get_ban_remaining(user_id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(user_id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
        
    state = user_states.get(user_id)
    if not message.text.isdigit():
        bot.send_message(user_id, "❌ Пожалуйста, введите корректное число для ставки.")
        return
        
    bet = int(message.text)
    if bet <= 0:
        bot.send_message(user_id, "❌ Ставка должна быть больше 0.")
        return
        
    if bet > players[user_id]['coins']:
        bot.send_message(user_id, f"❌ У вас недостаточно монет! Ваш баланс: 💰 {players[user_id]['coins']}.")
        return
        
    if state == 'awaiting_dice_bet':
        user_states.pop(user_id, None)
        add_xp_and_coins(user_id, 0, -bet)
        increment_quest_casino(user_id)
        
        bot.send_message(user_id, f"🎲 Вы сделали ставку {bet} монет. Бросаем кости...")
        user_msg = bot.send_dice(user_id, emoji='🎲')
        user_score = user_msg.dice.value
        time.sleep(2)
        
        bot.send_message(user_id, "🎲 Бросок казино...")
        bot_msg = bot.send_dice(user_id, emoji='🎲')
        bot_score = bot_msg.dice.value
        time.sleep(2)
        
        if user_score > bot_score:
            win_amount = bet * 2
            add_xp_and_coins(user_id, 0, win_amount)
            bot.send_message(user_id, f"🎉 **Вы выиграли!** Ваш кубик: {user_score}, Дилер: {bot_score}.\nВыигрыш: 💰 {win_amount} монет!", parse_mode="Markdown")
        elif user_score < bot_score:
            bot.send_message(user_id, f"☠️ **Вы проиграли!** Ваш кубик: {user_score}, Дилер: {bot_score}.\nПотеряно: 💰 {bet} монет.", parse_mode="Markdown")
        else:
            add_xp_and_coins(user_id, 0, bet)
            bot.send_message(user_id, f"🤝 **Ничья!** У обоих выпало {user_score}.\nСтавка 💰 {bet} монет возвращена.", parse_mode="Markdown")
            
    elif state == 'awaiting_mines_bet':
        user_states.pop(user_id, None)
        add_xp_and_coins(user_id, 0, -bet)
        
        board = ['M'] * 3 + ['S'] * 9
        random.shuffle(board)
        
        players[user_id]['mines_game'] = {
            'bet': bet,
            'board': board,
            'opened': [],
            'current_win': 0
        }
        
        markup = render_mines_keyboard(players[user_id]['mines_game'])
        bot.send_message(user_id, f"💣 **Мины 4х3**\nСтавка: 💰 {bet} монет.\nНажмите на любая клетку, чтобы открыть ее!", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['text'])
def global_chat(message):
    if is_user_banned(message.chat.id):
        rem = get_ban_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"⛔ Вы заблокированы и не можете использовать бота.{time_str}")
        return
    if is_user_muted(message.chat.id):
        rem = get_mute_remaining(message.chat.id)
        time_str = f" Осталось: {format_time_remaining(rem)}" if rem > 0 else ""
        bot.send_message(message.chat.id, f"🔇 Вы заблокированы в общем чате.{time_str}")
        return

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

    afk_thread = Thread(target=auto_kick_afk_loop, daemon=True)
    afk_thread.start()

    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            time.sleep(5)
