"""
Менеджер загрузок: торрент → ожидание завершения → автораспаковка → готово.
"""

import threading
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from core.torrent_engine import TorrentEngine
from core.installer import Installer
from core.library import Library
from config import GAMES_DIR


class DownloadManager:
    def __init__(self, library: Library):
        self.library = library
        self.engine = TorrentEngine()
        self.installer = Installer()
        self.active: Dict[str, Dict[str, Any]] = {}  # game_id -> info
        self._lock = threading.Lock()

    def start_shop_game(
        self,
        game_id: str,
        title: str,
        magnet: Optional[str],
        archive_password: Optional[str],
        on_progress: Optional[Callable[[str, float, str], None]] = None,
        on_finished: Optional[Callable[[str, bool, str], None]] = None,
    ):
        """
        Запускает скачивание магазинной игры.
        on_progress(game_id, percent, status_text)
        on_finished(game_id, success, message)
        """
        if not magnet:
            if on_finished:
                on_finished(game_id, False, "Нет magnet-ссылки")
            return

        download_dir = GAMES_DIR / f"_downloading_{game_id}"
        download_dir.mkdir(parents=True, exist_ok=True)

        try:
            gid = self.engine.add_magnet(magnet, download_dir=download_dir)
        except Exception as e:
            if on_finished:
                on_finished(game_id, False, f"Не удалось начать загрузку: {e}")
            return

        with self._lock:
            self.active[game_id] = {
                "gid": gid,
                "title": title,
                "password": archive_password,
                "download_dir": download_dir,
                "on_progress": on_progress,
                "on_finished": on_finished,
            }

        self.library.update_game(game_id, status="downloading", download_gid=gid)

        # Фоновый мониторинг
        threading.Thread(target=self._monitor, args=(game_id,), daemon=True).start()

    def _monitor(self, game_id: str):
        info = self.active.get(game_id)
        if not info:
            return

        gid = info["gid"]
        on_progress = info.get("on_progress")
        on_finished = info.get("on_finished")

        while True:
            try:
                pct, text = self.engine.get_progress(gid)
                if on_progress:
                    on_progress(game_id, pct, text)

                if self.engine.is_finished(gid):
                    break

                st = self.engine.get_status(gid)
                if st.get("status") in ("error", "removed"):
                    msg = st.get("errorMessage") or "Ошибка загрузки"
                    if on_finished:
                        on_finished(game_id, False, msg)
                    self.library.update_game(game_id, status="error")
                    with self._lock:
                        self.active.pop(game_id, None)
                    return

            except Exception as e:
                if on_progress:
                    on_progress(game_id, 0, str(e))

            time.sleep(1.5)

        # Скачивание закончено → ищем архив и ставим
        if on_progress:
            on_progress(game_id, 100, "Скачано, устанавливаю...")

        files = self.engine.get_downloaded_files(gid)
        archive = None
        for f in files:
            if f.suffix.lower() in (".zip", ".rar", ".7z") and f.exists():
                archive = f
                break

        # Иногда торрент качает папку с архивом внутри
        if archive is None:
            for f in info["download_dir"].rglob("*"):
                if f.suffix.lower() in (".zip", ".rar", ".7z") and f.is_file():
                    archive = f
                    break

        if archive is None:
            # Может торрент уже отдал готовую папку с игрой
            exe = self.installer.find_exe(info["download_dir"], preferred_names=[info["title"]])
            if exe:
                self.library.mark_installed(
                    game_id,
                    install_path=str(info["download_dir"]),
                    exe_path=str(exe),
                )
                if on_finished:
                    on_finished(game_id, True, f"Готово! Найден {exe.name}")
                with self._lock:
                    self.active.pop(game_id, None)
                return

            if on_finished:
                on_finished(game_id, False, "Архив не найден после скачивания")
            self.library.update_game(game_id, status="error")
            with self._lock:
                self.active.pop(game_id, None)
            return

        # Распаковываем с паролем из каталога
        ok, msg, install_path, exe_path = self.installer.install_from_archive(
            archive,
            title=info["title"],
            password=info.get("password"),
            delete_archive_after=True,
        )

        if ok and exe_path:
            self.library.mark_installed(
                game_id,
                install_path=str(install_path) if install_path else "",
                exe_path=str(exe_path),
            )
            if on_finished:
                on_finished(game_id, True, msg)
        else:
            self.library.update_game(game_id, status="error")
            if on_finished:
                on_finished(game_id, False, msg or "Не удалось установить")

        with self._lock:
            self.active.pop(game_id, None)

    def get_active_progress(self, game_id: str) -> Optional[tuple[float, str]]:
        info = self.active.get(game_id)
        if not info:
            return None
        try:
            return self.engine.get_progress(info["gid"])
        except Exception:
            return None
