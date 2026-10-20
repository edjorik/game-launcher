"""
Каталог / «Магазин» игр.
Эти игры видны всем. Пароль к архиву хранится здесь (или потом будет приходить с сервера).
Пользователь ставит в один клик — пароль вводить не нужно.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from config import CONFIG_DIR

CATALOG_FILE = CONFIG_DIR / "catalog.json"


# Пока хардкод + возможность переопределить через catalog.json
# Когда появится сервер — просто будем тянуть оттуда.
DEFAULT_CATALOG: List[Dict[str, Any]] = [
    # Пример. Замени на свои реальные игры.
    # {
    #     "id": "cyber_neon",
    #     "title": "Cyber Neon Runner",
    #     "description": "Неоновый раннер",
    #     "size_mb": 1200,
    #     "torrent_url": None,          # ссылка на .torrent или magnet
    #     "magnet": "magnet:?xt=urn:btih:....",
    #     "archive_password": "mypass123",  # ← пароль уже здесь
    #     "cover": None,
    # },
]


class Catalog:
    def __init__(self):
        self.games: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if CATALOG_FILE.exists():
            try:
                self.games = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
                return
            except Exception:
                pass
        self.games = list(DEFAULT_CATALOG)
        self._save()

    def _save(self):
        CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_FILE.write_text(
            json.dumps(self.games, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_all(self) -> List[Dict[str, Any]]:
        return self.games

    def get_by_id(self, game_id: str) -> Optional[Dict[str, Any]]:
        for g in self.games:
            if g.get("id") == game_id:
                return g
        return None

    def add_game(self, game: Dict[str, Any]):
        """Добавить игру в каталог (для тебя как админа)."""
        self.games.append(game)
        self._save()

    def update_game(self, game_id: str, **kwargs):
        for g in self.games:
            if g.get("id") == game_id:
                g.update(kwargs)
                self._save()
                return g
        return None
