"""
Конфиг лаунчера. Здесь всё, что можно крутить.
"""

import os
from pathlib import Path

# Версия лаунчера (для автообновлений)
APP_VERSION = "0.1.0"
APP_NAME = "Nexus Launcher"
APP_AUTHOR = "edjorik"

# Пути
BASE_DIR = Path(__file__).parent
GAMES_DIR = BASE_DIR / "games"
CACHE_DIR = BASE_DIR / "cache"
CONFIG_DIR = Path.home() / ".nexus_launcher"
TOKEN_FILE = CONFIG_DIR / "token.json"

# Сервер (замени на свой, когда будет готов)
API_BASE_URL = "https://your-api-server.com/api/v1"  # ← сюда свой бэкенд
UPDATE_CHECK_URL = "https://api.github.com/repos/edjorik/game-launcher/releases/latest"

# UI
THEME = "dark"
ACCENT_COLOR = "#7C3AED"  # Фиолетовый, чтобы Steam курил в сторонке
SECONDARY_COLOR = "#1E1B4B"

# Создаём нужные папки
for d in [GAMES_DIR, CACHE_DIR, CONFIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)
