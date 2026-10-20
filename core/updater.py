"""
Автообновление лаунчера через GitHub Releases.
Скачивает новый .exe / архив и предлагает перезапуститься.
"""

import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Callable

import requests
from packaging import version

from config import APP_VERSION, UPDATE_CHECK_URL, CACHE_DIR


class Updater:
    def __init__(self):
        self.latest_version: Optional[str] = None
        self.download_url: Optional[str] = None
        self.release_notes: str = ""

    def check_for_updates(self) -> tuple[bool, str]:
        """
        Проверяет GitHub Releases.
        Возвращает (есть_обновление, сообщение)
        """
        try:
            resp = requests.get(UPDATE_CHECK_URL, timeout=10)
            if resp.status_code != 200:
                return False, "Не удалось проверить обновления"

            data = resp.json()
            tag = data.get("tag_name", "").lstrip("v")
            self.latest_version = tag
            self.release_notes = data.get("body", "") or "Без описания"

            # Ищем ассет (exe или zip)
            for asset in data.get("assets", []):
                name = asset.get("name", "").lower()
                if name.endswith(".exe") or name.endswith(".zip"):
                    self.download_url = asset.get("browser_download_url")
                    break

            if version.parse(tag) > version.parse(APP_VERSION):
                return True, f"Доступна версия {tag} (у тебя {APP_VERSION})"
            return False, f"У тебя самая свежая версия ({APP_VERSION})"
        except Exception as e:
            return False, f"Ошибка проверки: {e}"

    def download_update(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Optional[Path]:
        """
        Скачивает обновление в cache.
        progress_callback(downloaded_bytes, total_bytes)
        """
        if not self.download_url:
            return None

        try:
            resp = requests.get(self.download_url, stream=True, timeout=30)
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            filename = self.download_url.split("/")[-1]
            target = CACHE_DIR / filename

            with open(target, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(downloaded, total)

            return target
        except Exception as e:
            print(f"Ошибка скачивания обновления: {e}")
            return None

    def apply_update(self, update_path: Path):
        """
        Простая логика: если это exe — просто запускаем новый и закрываем старый.
        Если zip — распаковываем рядом.
        В проде лучше делать через отдельный updater-процесс.
        """
        if update_path.suffix.lower() == ".exe":
            # Запускаем новый exe и выходим
            os.startfile(str(update_path))  # Windows
            sys.exit(0)
        elif update_path.suffix.lower() == ".zip":
            extract_to = Path(tempfile.mkdtemp(prefix="nexus_update_"))
            with zipfile.ZipFile(update_path, "r") as z:
                z.extractall(extract_to)
            # Здесь можно скопировать файлы поверх текущих
            print(f"Обновление распаковано в {extract_to}")
            # TODO: умная замена файлов + перезапуск
