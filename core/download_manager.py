"""
Менеджер загрузок: торрент → ожидание завершения → умная установка.

После скачивания лаунчер сам определяет, что пришло:
  1. Архив (.zip / .rar / .7z)  → распаковывает (с паролем) → ищет .exe
  2. Готовый .exe               → сразу ставит кнопку «Играть»
  3. Папка с игрой              → ищет .exe внутри (рекурсивно)
"""

import threading
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from core.torrent_engine import TorrentEngine
from core.installer import Installer
from core.library import Library
from config import GAMES_DIR

ARCHIVE_EXTS = {".zip", ".rar", ".7z"}


class DownloadManager:
    def __init__(self, library: Library):
        self.library = library
        self.engine = TorrentEngine()
        self.installer = Installer()
        self.active: Dict[str, Dict[str, Any]] = {}
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

        # ========== Скачивание закончено — разбираемся, что пришло ==========
        if on_progress:
            on_progress(game_id, 100, "Скачано, определяю тип...")

        download_dir: Path = info["download_dir"]
        title = info["title"]
        password = info.get("password")

        # Собираем все скачанные файлы
        all_files: List[Path] = []
        try:
            all_files = [f for f in self.engine.get_downloaded_files(gid) if f.exists()]
        except Exception:
            pass

        if not all_files:
            all_files = [f for f in download_dir.rglob("*") if f.is_file()]

        # ---- Вариант 1: есть архив ----
        archive = self._find_archive(all_files, download_dir)
        if archive:
            if on_progress:
                on_progress(game_id, 100, f"Найден архив {archive.name}, распаковываю...")

            ok, msg, install_path, exe_path = self.installer.install_from_archive(
                archive,
                title=title,
                password=password,
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
                    on_finished(game_id, False, msg or "Не удалось распаковать архив")

            with self._lock:
                self.active.pop(game_id, None)
            return

        # ---- Вариант 2: торрент отдал готовый .exe (или папку с игрой) ----
        exe = self.installer.find_exe(download_dir, preferred_names=[title])

        # Дополнительно: если среди скачанных файлов один жирный .exe — берём его
        if exe is None:
            exe_candidates = [
                f for f in all_files
                if f.suffix.lower() == ".exe" and f.is_file()
            ]
            # отсеиваем мусор
            ignore = ("unins", "vcredist", "directx", "unitycrash", "crashhandler", "setup", "install")
            exe_candidates = [
                f for f in exe_candidates
                if not any(k in f.name.lower() for k in ignore)
            ]
            if exe_candidates:
                # самый большой = скорее всего игра
                exe_candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
                exe = exe_candidates[0]

        if exe:
            self.library.mark_installed(
                game_id,
                install_path=str(download_dir),
                exe_path=str(exe),
            )
            if on_finished:
                on_finished(game_id, True, f"Готово! Это был .exe / папка. Найден: {exe.name}")
            with self._lock:
                self.active.pop(game_id, None)
            return

        # ---- Вариант 3: нихуя не понятно ----
        self.library.update_game(game_id, status="error")
        if on_finished:
            on_finished(
                game_id,
                False,
                "Скачалось, но не удалось найти ни архив, ни .exe. "
                "Можешь указать файл запуска вручную в библиотеке."
            )
        with self._lock:
            self.active.pop(game_id, None)

    def _find_archive(self, files: List[Path], root: Path) -> Optional[Path]:
        """Ищет архив среди скачанных файлов."""
        for f in files:
            if f.suffix.lower() in ARCHIVE_EXTS and f.is_file():
                return f
        # на всякий случай ещё раз по папке
        for f in root.rglob("*"):
            if f.suffix.lower() in ARCHIVE_EXTS and f.is_file():
                return f
        return None

    def get_active_progress(self, game_id: str) -> Optional[tuple[float, str]]:
        info = self.active.get(game_id)
        if not info:
            return None
        try:
            return self.engine.get_progress(info["gid"])
        except Exception:
            return None
