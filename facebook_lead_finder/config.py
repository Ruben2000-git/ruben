"""
Все настройки программы в одном месте.
Меняйте значения тут, остальной код трогать не нужно.
"""

import os

# ---------- Facebook login ----------
# Логин и пароль от вашего личного аккаунта Facebook.
# ВАЖНО: не храните пароль прямо в этом файле в реальном использовании -
# лучше задайте переменные окружения FB_EMAIL и FB_PASSWORD.
FB_EMAIL = os.environ.get("FB_EMAIL", "")
FB_PASSWORD = os.environ.get("FB_PASSWORD", "")

# Файл, куда Playwright сохраняет cookies/сессию после первого ручного логина,
# чтобы не вводить пароль и не проходить проверку безопасности каждый раз.
BROWSER_STATE_FILE = "fb_session.json"

# Показывать окно браузера (True - видно, что происходит; False - скрыто).
# На первом запуске рекомендуется True, чтобы вручную пройти 2FA/капчу.
HEADLESS = False

# ---------- Группы Facebook для мониторинга ----------
# Вставьте сюда полные ссылки на группы, в которых вы УЖЕ состоите.
# Пример: "https://www.facebook.com/groups/123456789012345/"
FACEBOOK_GROUPS = [
    "https://www.facebook.com/groups/wnybuyselltrade",
    "https://www.facebook.com/groups/1164096468323677/",
    "https://www.facebook.com/groups/256851142442942/",
    "https://www.facebook.com/groups/454838724700234/",
    "https://www.facebook.com/groups/406364223299384/",
    "https://www.facebook.com/groups/507095466926196/",
    "https://www.facebook.com/groups/1531519547076377/",
    "https://www.facebook.com/groups/1219311431465828/",
    "https://www.facebook.com/groups/1537933962923290/",
    "https://www.facebook.com/groups/565678137847725/",
]

# ---------- Ключевые слова для поиска лидов ----------
KEYWORDS = [
    "gutter",
    "gutters",
    "fence repair",
    "fence",
    "siding",
    "drywall",
    "handyman",
    "window repair",
    "window screen",
    "deck repair",
    "leak repair",
    "roof repair",
]

# ---------- Фильтрация по времени ----------
# Игнорировать посты старше этого количества часов.
MAX_POST_AGE_HOURS = 48

# ---------- База данных ----------
DATABASE_FILE = "facebookleads.db"

# ---------- Claude API ----------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

# ---------- Планировщик ----------
# Как часто (в минутах) запускать поиск новых постов.
SCAN_INTERVAL_MINUTES = 20

# ---------- Flask-дашборд ----------
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000

# ---------- Логи ----------
LOG_FILE = "facebookleads.log"

# ---------- Инфо о бизнесе (для составления draft_reply) ----------
CONTRACTOR_NAME = "Ruvim"
BUSINESS_DESCRIPTION = (
    "a contractor handling gutter repair, fence repair, siding, drywall, "
    "small handyman jobs and window repair in the Buffalo, NY area"
)
