import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS moderators (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            added_by INTEGER,
            added_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS owners (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            added_by INTEGER,
            added_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            until TEXT,
            reason TEXT,
            blocked_by INTEGER,
            blocked_by_role TEXT,
            blocked_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            type TEXT,
            text TEXT,
            photo_id TEXT,
            status TEXT DEFAULT 'new',
            assigned_to INTEGER,
            answer TEXT,
            answered_by INTEGER,
            answered_by_role TEXT,
            created_at TEXT,
            answered_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            user_id INTEGER,
            mod_id INTEGER,
            rating TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            user_id INTEGER,
            by_id INTEGER,
            by_role TEXT,
            reason TEXT,
            duration TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def now_str():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


# ================= МОДЕРАТОРЫ =================

def add_moderator(user_id, username, full_name, added_by):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO moderators (user_id, username, full_name, added_by, added_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, username, full_name, added_by, now_str())
    )
    conn.commit()
    conn.close()


def remove_moderator(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM moderators WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_moderators():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM moderators").fetchall()
    conn.close()
    return rows


def is_moderator(user_id):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM moderators WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row is not None


# ================= ВЛАДЕЛЬЦЫ =================

def add_owner(user_id, username, full_name, added_by):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO owners (user_id, username, full_name, added_by, added_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, username, full_name, added_by, now_str())
    )
    conn.commit()
    conn.close()


def remove_owner(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM owners WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_owners():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM owners").fetchall()
    conn.close()
    return rows


# ================= БЛОКИРОВКИ =================

def block_user(user_id, username, full_name, until, reason, blocked_by, role):
    conn = get_conn()
    until_clean = str(until).strip() if until != "forever" else "forever"
    conn.execute(
        "INSERT OR REPLACE INTO blocked (user_id, username, full_name, until, reason, blocked_by, blocked_by_role, blocked_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, full_name, until_clean, reason, blocked_by, role, now_str())
    )
    conn.execute(
        "INSERT INTO history (action, user_id, by_id, by_role, reason, duration, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("block", user_id, blocked_by, role, reason, until_clean, now_str())
    )
    conn.commit()
    conn.close()


def unblock_user(user_id, by_id, role):
    conn = get_conn()
    conn.execute("DELETE FROM blocked WHERE user_id = ?", (user_id,))
    conn.execute(
        "INSERT INTO history (action, user_id, by_id, by_role, reason, duration, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("unblock", user_id, by_id, role, "", "", now_str())
    )
    conn.commit()
    conn.close()


def get_blocked(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM blocked WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()

    if not row:
        return None

    until = row["until"]
    if until == "forever":
        return row

    try:
        until_str = str(until).strip()
        until_dt = datetime.strptime(until_str, "%d.%m.%Y %H:%M")
        if until_dt <= datetime.now():
            unblock_user(user_id, 0, "system")
            return None
    except Exception as e:
        print(f"[DB] Ошибка разбора даты '{until}': {e}")
        unblock_user(user_id, 0, "system")
        return None

    return row


def get_all_blocked():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM blocked").fetchall()
    conn.close()
    return rows


# ================= ОБРАЩЕНИЯ =================

def create_ticket(user_id, username, full_name, ttype, text, photo_id=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tickets (user_id, username, full_name, type, text, photo_id, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'new', ?)",
        (user_id, username, full_name, ttype, text, photo_id, now_str())
    )
    ticket_id = cur.lastrowid
    conn.commit()
    conn.close()
    return ticket_id


def get_ticket(ticket_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    conn.close()
    return row


def get_active_tickets():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tickets WHERE status != 'closed' ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return rows


def get_user_tickets(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def set_ticket_status(ticket_id, status, assigned_to=None):
    conn = get_conn()
    if assigned_to is not None:
        conn.execute(
            "UPDATE tickets SET status = ?, assigned_to = ? WHERE id = ?",
            (status, assigned_to, ticket_id)
        )
    else:
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
    conn.commit()
    conn.close()


def answer_ticket(ticket_id, answer, by_id, role):
    conn = get_conn()
    conn.execute(
        "UPDATE tickets SET answer = ?, answered_by = ?, answered_by_role = ?, "
        "answered_at = ?, status = 'answered' WHERE id = ?",
        (answer, by_id, role, now_str(), ticket_id)
    )
    conn.commit()
    conn.close()


# ================= ОЦЕНКИ =================

def add_rating(ticket_id, user_id, mod_id, rating):
    conn = get_conn()
    conn.execute(
        "INSERT INTO ratings (ticket_id, user_id, mod_id, rating, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (ticket_id, user_id, mod_id, rating, now_str())
    )
    conn.commit()
    conn.close()


def get_mod_ratings(mod_id):
    conn = get_conn()
    plus = conn.execute(
        "SELECT COUNT(*) FROM ratings WHERE mod_id = ? AND rating = 'up'", (mod_id,)
    ).fetchone()[0]
    minus = conn.execute(
        "SELECT COUNT(*) FROM ratings WHERE mod_id = ? AND rating = 'down'", (mod_id,)
    ).fetchone()[0]
    conn.close()
    return plus, minus


# ================= СТАТИСТИКА =================

def get_mod_stats(mod_id):
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE answered_by = ?", (mod_id,)
    ).fetchone()[0]
    bugs = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE answered_by = ? AND type = 'bug'", (mod_id,)
    ).fetchone()[0]
    ideas = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE answered_by = ? AND type = 'idea'", (mod_id,)
    ).fetchone()[0]
    blocks = conn.execute(
        "SELECT COUNT(*) FROM history WHERE by_id = ? AND action = 'block'", (mod_id,)
    ).fetchone()[0]
    unblocks = conn.execute(
        "SELECT COUNT(*) FROM history WHERE by_id = ? AND action = 'unblock'", (mod_id,)
    ).fetchone()[0]
    conn.close()
    return {
        "total": total, "bugs": bugs, "ideas": ideas,
        "blocks": blocks, "unblocks": unblocks
    }


def get_bot_stats():
    conn = get_conn()
    users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM tickets").fetchone()[0]
    bugs = conn.execute("SELECT COUNT(*) FROM tickets WHERE type = 'bug'").fetchone()[0]
    ideas = conn.execute("SELECT COUNT(*) FROM tickets WHERE type = 'idea'").fetchone()[0]
    closed = conn.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM tickets WHERE status != 'closed'").fetchone()[0]
    blocks = conn.execute("SELECT COUNT(*) FROM history WHERE action = 'block'").fetchone()[0]
    conn.close()
    return {
        "users": users, "bugs": bugs, "ideas": ideas,
        "closed": closed, "active": active, "blocks": blocks
    }
