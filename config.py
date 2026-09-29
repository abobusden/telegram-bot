import os

# ===== ОСНОВНОЕ =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ===== ВЛАДЕЛЬЦЫ =====
OWNER_ID = 6479447470
OWNER_IDS = [6479447470, 6236795210]

# ===== ПОДПИСИ ОТВЕТОВ =====
SIGNATURE_MOD = "— Команда Sky World"
SIGNATURE_OWNER = "— Владелец Sky World"

# ===== ПРИВЕТСТВИЯ =====
GREETING_OWNER = "👑 Привет, Владелец!"
GREETING_MOD = "🛡 Привет, {name}!"
GREETING_USER = "Привет, {name}!"

# ===== БАЗА ДАННЫХ =====
DB_PATH = "sky_world.db"

# ===== ОБЯЗАТЕЛЬНАЯ ПОДПИСКА =====
REQUIRE_SUBSCRIBE = True
CHANNELS = [
    {
        "id": -1003495203669,
        "link": "https://t.me/skyworldminemclan",
        "name": "Sky World [Mine]"
    },
    {
        "id": -1003884509138,
        "link": "https://t.me/Sky_world_top",
        "name": "Sky World YouTube"
    },
]

# ===== ТЕКСТЫ =====
TEXT_BUG_SENT = (
    "✅ Спасибо! Твоё сообщение о баге отправлено.\n\n"
    "⏳ Ожидай ответа.\n"
    "Ответ может занять от 5 минут до 24 часов."
)

TEXT_IDEA_SENT = (
    "✅ Спасибо! Твоя идея отправлена.\n\n"
    "⏳ Ожидай ответа.\n"
    "Ответ может занять от 5 минут до 24 часов."
)

TEXT_BLOCKED = (
    "🚫 Вы заблокированы.\n\n"
    "📝 Причина: {reason}\n"
    "⏰ Разблокировка: {until}\n"
    "👤 Кто: {who}\n\n"
    "Если блокировка несправедлива — свяжитесь с владельцем."
)
