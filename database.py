# ============================================
# РАБОТА С БАЗОЙ ДАННЫХ (SQLite)
# ============================================

import aiosqlite
from config import DB_PATH, START_BALANCE, START_HP, START_LEVEL, START_EXP


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                nickname TEXT UNIQUE NOT NULL,
                gender TEXT NOT NULL,
                faction TEXT,
                district TEXT NOT NULL,
                balance INTEGER DEFAULT 500,
                hp INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                wanted INTEGER DEFAULT 0,
                weapon TEXT,
                car TEXT,
                home TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def get_player(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM players WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def nickname_exists(nickname: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM players WHERE LOWER(nickname) = LOWER(?)", (nickname,)
        ) as cur:
            return await cur.fetchone() is not None


async def create_player(telegram_id, nickname, gender, faction, district):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO players
                (telegram_id, nickname, gender, faction, district,
                 balance, hp, level, exp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_id, nickname, gender, faction, district,
            START_BALANCE, START_HP, START_LEVEL, START_EXP,
        ))
        await db.commit()


async def update_player(telegram_id: int, **fields):
    if not fields:
        return
    keys = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [telegram_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE players SET {keys} WHERE telegram_id = ?", values)
        await db.commit()


# ============================================
# ДОБАВЛЕНИЕ ОПЫТА + АВТО-ПОВЫШЕНИЕ УРОВНЯ
# ============================================
async def add_exp(telegram_id: int, amount: int):
    """
    Добавляет опыт и повышает уровень.
    Порог для ур.N: level * 100
    Пример:
      ур.1 → нужно 100 опыта
      ур.2 → нужно 200 опыта
      ур.3 → нужно 300 опыта
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT level, exp FROM players WHERE telegram_id = ?",
            (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None

        level = row["level"]
        exp = row["exp"] + amount

        # Повышение уровня (может быть несколько сразу)
        levels_up = 0
        while exp >= level * 100:
            exp -= level * 100
            level += 1
            levels_up += 1

        await db.execute(
            "UPDATE players SET level = ?, exp = ? WHERE telegram_id = ?",
            (level, exp, telegram_id)
        )
        await db.commit()

        return {
            "level": level,
            "exp": exp,
            "levels_up": levels_up,
    }
