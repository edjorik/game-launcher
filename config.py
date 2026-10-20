"""
Конфиг лаунчера. Здесь всё, что можно крутить.
"""

from pathlib import Path

# Версия лаунчера
APP_VERSION = "0.2.0"
APP_NAME = "Nexus Launcher"
APP_AUTHOR = "edjorik"

# === Главная директория лаунчера (как у Steam) ===
# По умолчанию: C:\Users\<user>\NexusLauncher
LIBRARY_ROOT = Path.home() / "NexusLauncher"
GAMES_DIR = LIBRARY_ROOT / "games"          # сюда ставятся игры
ARCHIVES_DIR = LIBRARY_ROOT / "archives"    # временные архивы
TORRENTS_DIR = LIBRARY_ROOT / "torrents"    # .torrent файлы
CACHE_DIR = LIBRARY_ROOT / "cache"
CONFIG_DIR = LIBRARY_ROOT / "config"

LIBRARY_FILE = CONFIG_DIR / "library.json"  # список добавленных игр
TOKEN_FILE = CONFIG_DIR / "token.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# Сервер (пока заглушка)
API_BASE_URL = "https://your-api-server.com/api/v1"
UPDATE_CHECK_URL = "https://api.github.com/repos/edjorik/game-launcher/releases/latest"

# UI — киберпанк вайб
THEME = "dark"
ACCENT_COLOR = "#A855F7"       # яркий фиолет
ACCENT_HOVER = "#C084FC"
BG_DARK = "#0A0A0F"
BG_CARD = "#12121A"
BG_SIDEBAR = "#0D0D14"
BORDER_GLOW = "#7C3AED"
TEXT_DIM = "#6B7280"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#EF4444"

# Создаём структуру папок как у нормального лаунчера
for d in [LIBRARY_ROOT, GAMES_DIR, ARCHIVES_DIR, TORRENTS_DIR, CACHE_DIR, CONFIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)
