"""
Каталог / «Магазин» игр.

Источник правды — файл catalog.json в GitHub-репозитории.
Лаунчер при запуске скачивает его. Обычные пользователи
не могут менять магазин — только ты, через репозиторий.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import urllib.request
import urllib.error

from config import CONFIG_DIR

# Куда кэшируем локально (только для офлайна)
CACHE_FILE = CONFIG_DIR / "catalog_cache.json"

# Публичный URL каталога (raw с GitHub)
# Менять не нужно — он всегда указывает на твой репозиторий
REMOTE_CATALOG_URL = (
    "https://raw.githubusercontent.com/edjorik/game-launcher/main/catalog.json"
)


class Catalog:
    def __init__(self):
        self.games: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        # 1. Пытаемся скачать свежий каталог с GitHub
        remote = self._fetch_remote()
        if remote is not None:
            self.games = remote
            self._save_cache()
            return

        # 2. Если интернета нет — берём кэш
        if CACHE_FILE.exists():
            try:
                self.games = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                return
            except Exception:
                pass

        # 3. Совсем пусто
        self.games = []

    def _fetch_remote(self) -> Optional[List[Dict[str, Any]]]:
        try:
            req = urllib.request.Request(
                REMOTE_CATALOG_URL,
                headers={"User-Agent": "NexusLauncher/1.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"[Catalog] Не удалось скачать каталог: {e}")
        return None

    def _save_cache(self):
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(self.games, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def refresh(self) -> bool:
        """Принудительно обновить каталог с сервера."""
        remote = self._fetch_remote()
        if remote is not None:
            self.games = remote
            self._save_cache()
            return True
        return False

    def get_all(self) -> List[Dict[str, Any]]:
        return self.games

    def get_by_id(self, game_id: str) -> Optional[Dict[str, Any]]:
        for g in self.games:
            if g.get("id") == game_id:
                return g
        return None
