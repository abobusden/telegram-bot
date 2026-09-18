import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPPORT_USERNAME = "pegvi"
SUPPORT_ID = 6236795210
DB_PATH = "gta_bot.db"

START_BALANCE = 500
START_HP = 100
START_LEVEL = 1
START_EXP = 0

FACTIONS = {
    "grove":   {"name": "Grove Street Families", "emoji": "🟢", "district": "Ganton"},
    "ballas":  {"name": "Ballas",                 "emoji": "🟣", "district": "Idlewood"},
    "vagos":   {"name": "Los Vagos",              "emoji": "🔵", "district": "East Los Santos"},
    "aztecas": {"name": "Ацтеки",                 "emoji": "⚪", "district": "El Corona"},
}
DEFAULT_DISTRICT = "Ganton"
