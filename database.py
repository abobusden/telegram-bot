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
                crime_level INTEGER DEFAULT 1,
                crime_deals INTEGER DEFAULT 0,
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
# ОПЫТ + УРОВЕНЬ (общий)
# ============================================
async def add_exp(telegram_id: int, amount: int):
    """Добавляет опыт + авто-повышение уровня. Порог: level * 100"""
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


# ============================================
# УРОВЕНЬ КРИМИНАЛА (1-5)
# ============================================
CRIME_DEALS_PER_LEVEL = 5   # сколько дел на +1 уровень


async def add_crime_deal(telegram_id: int):
    """
    +1 успешное дело к счётчику.
    Каждые 5 дел → +1 crime_level.
    Максимум crime_level = 5.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT crime_level, crime_deals FROM players WHERE telegram_id = ?",
            (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None

        crime_level = row["crime_level"]
        crime_deals = row["crime_deals"] + 1

        leveled_up = False

        # Повышение уровня (максимум 5)
        if crime_deals >= CRIME_DEALS_PER_LEVEL and crime_level < 5:
            crime_deals = 0
            crime_level += 1
            leveled_up = True

        await db.execute(
            "UPDATE players SET crime_level = ?, crime_deals = ? WHERE telegram_id = ?",
            (crime_level, crime_deals, telegram_id)
        )
        await db.commit()

        return {
            "crime_level": crime_level,
            "crime_deals": crime_deals,
            "leveled_up": leveled_up,
        }


def get_crime_bonus(crime_level: int) -> float:
    """
    Возвращает множитель дохода по уровню криминала.
    Ур.1 → 1.0 (0%)
    Ур.2 → 1.1 (+10%)
    Ур.3 → 1.2 (+20%)
    Ур.4 → 1.3 (+30%)
    Ур.5 → 1.5 (+50%)
    """
    bonuses = {
        1: 1.0,
        2: 1.1,
        3: 1.2,
        4: 1.3,
        5: 1.5,
    }
    return bonuses.get(crime_level, 1.0)
