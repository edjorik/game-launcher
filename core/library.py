"""
Локальная библиотека игр.
Хранит всё в library.json — никаких фейковых игр.
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import LIBRARY_FILE, GAMES_DIR


class Library:
    def __init__(self):
        self.games: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if LIBRARY_FILE.exists():
            try:
                self.games = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
            except Exception:
                self.games = []
        else:
            self.games = []

    def _save(self):
        LIBRARY_FILE.parent.mkdir(parents=True, exist_ok=True)
        LIBRARY_FILE.write_text(
            json.dumps(self.games, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_all(self) -> List[Dict[str, Any]]:
        return self.games

    def get_by_id(self, game_id: str) -> Optional[Dict[str, Any]]:
        for g in self.games:
            if g["id"] == game_id:
                return g
        return None

    def add_game(
        self,
        title: str,
        exe_path: Optional[str] = None,
        install_path: Optional[str] = None,
        archive_path: Optional[str] = None,
        torrent_path: Optional[str] = None,
        password: Optional[str] = None,
        cover: Optional[str] = None,
    ) -> Dict[str, Any]:
        game = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "exe_path": exe_path,
            "install_path": install_path,
            "archive_path": archive_path,
            "torrent_path": torrent_path,
            "password": password,
            "cover": cover,
            "status": "ready" if exe_path else "not_installed",
            "added_at": datetime.now().isoformat(),
            "last_played": None,
        }
        self.games.append(game)
        self._save()
        return game

    def update_game(self, game_id: str, **kwargs):
        for g in self.games:
            if g["id"] == game_id:
                g.update(kwargs)
                self._save()
                return g
        return None

    def remove_game(self, game_id: str) -> bool:
        before = len(self.games)
        self.games = [g for g in self.games if g["id"] != game_id]
        if len(self.games) < before:
            self._save()
            return True
        return False

    def set_exe(self, game_id: str, exe_path: str):
        return self.update_game(game_id, exe_path=exe_path, status="ready")

    def mark_installed(self, game_id: str, install_path: str, exe_path: str):
        return self.update_game(
            game_id,
            install_path=install_path,
            exe_path=exe_path,
            status="ready",
            archive_path=None,  # архив больше не нужен
        )
