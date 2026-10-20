"""
Загрузчик игр.
Поддерживает обычный HTTP + заготовку под торренты через qBittorrent WebAPI
(чтобы не убивать твой сервак).
"""

import os
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any

import requests

from config import GAMES_DIR, API_BASE_URL


class GameDownloader:
    def __init__(self, auth_token: Optional[str] = None):
        self.token = auth_token
        self.headers = {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    def get_games_list(self) -> list[Dict[str, Any]]:
        """Получает список игр с сервера. Если сервер мёртв — отдаёт mock."""
        try:
            resp = requests.get(
                f"{API_BASE_URL}/games",
                headers=self.headers,
                timeout=8,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

        # Mock-игры, чтобы было что смотреть прямо сейчас
        return [
            {
                "id": 1,
                "title": "Cyber Neon Runner",
                "description": "Бесконечный раннер в неоновом аду 2077 года",
                "cover": None,
                "size_mb": 1200,
                "version": "1.2.0",
                "download_type": "http",  # или "torrent"
                "download_url": "https://example.com/games/cyber_neon.zip",
                "magnet": None,
                "installed": False,
            },
            {
                "id": 2,
                "title": "Pixel Warlords",
                "description": "Пиксельная стратегия, где ты — бог войны",
                "cover": None,
                "size_mb": 450,
                "version": "0.9.5",
                "download_type": "torrent",
                "download_url": None,
                "magnet": "magnet:?xt=urn:btih:EXAMPLEHASH&dn=PixelWarlords",
                "installed": False,
            },
            {
                "id": 3,
                "title": "Void Echoes",
                "description": "Хоррор-бродилка в пустоте. Не играй ночью.",
                "cover": None,
                "size_mb": 2800,
                "version": "2.1.0",
                "download_type": "http",
                "download_url": "https://example.com/games/void_echoes.zip",
                "magnet": None,
                "installed": False,
            },
        ]

    def download_http(
        self,
        url: str,
        game_id: int,
        title: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Optional[Path]:
        """
        Скачивает игру по HTTP.
        progress_callback(percent, status_text)
        """
        game_folder = GAMES_DIR / f"game_{game_id}"
        game_folder.mkdir(parents=True, exist_ok=True)

        filename = url.split("/")[-1] or f"{title}.zip"
        target = game_folder / filename

        try:
            with requests.get(url, stream=True, timeout=30, headers=self.headers) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                downloaded = 0

                with open(target, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total > 0:
                                pct = (downloaded / total) * 100
                                progress_callback(pct, f"Скачано {downloaded // 1024 // 1024} МБ")

            if progress_callback:
                progress_callback(100.0, "Готово")
            return target
        except Exception as e:
            if progress_callback:
                progress_callback(0.0, f"Ошибка: {e}")
            return None

    def start_torrent_via_qbittorrent(
        self,
        magnet: str,
        game_id: int,
        qb_host: str = "localhost",
        qb_port: int = 8080,
        qb_user: str = "admin",
        qb_pass: str = "adminadmin",
    ) -> bool:
        """
        Добавляет торрент в локальный qBittorrent через WebAPI.
        Пользователь должен иметь запущенный qBittorrent с включённым WebUI.
        Это спасает твой сервер от DDoS-а.
        """
        try:
            from qbittorrentapi import Client

            client = Client(
                host=qb_host,
                port=qb_port,
                username=qb_user,
                password=qb_pass,
            )
            client.auth_log_in()

            save_path = str(GAMES_DIR / f"game_{game_id}")
            client.torrents_add(urls=magnet, save_path=save_path)
            return True
        except Exception as e:
            print(f"Не удалось добавить торрент в qBittorrent: {e}")
            return False

    def is_installed(self, game_id: int) -> bool:
        folder = GAMES_DIR / f"game_{game_id}"
        return folder.exists() and any(folder.iterdir())
