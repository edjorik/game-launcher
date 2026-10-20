"""
Установщик игр:
- Распаковка ZIP / RAR (с паролем)
- Поиск .exe внутри
- Удаление архива после успешной установки
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional, Callable, List, Tuple

try:
    import pyzipper
except ImportError:
    pyzipper = None

try:
    import rarfile
except ImportError:
    rarfile = None

from config import GAMES_DIR, ARCHIVES_DIR


class Installer:
    def __init__(self):
        self._7z_path = self._find_7z()

    def _find_7z(self) -> Optional[str]:
        """Ищем 7-Zip — он почти всегда есть у тех, кто качает репаки."""
        candidates = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
            shutil.which("7z"),
            shutil.which("7z.exe"),
        ]
        for p in candidates:
            if p and Path(p).exists():
                return p
        return None

    def extract(
        self,
        archive_path: str | Path,
        password: Optional[str] = None,
        target_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Распаковывает архив.
        Возвращает (успех, сообщение, путь_куда_распаковали)
        """
        archive_path = Path(archive_path)
        if not archive_path.exists():
            return False, "Архив не найден", None

        if target_dir is None:
            # Создаём папку с именем архива
            folder_name = archive_path.stem
            target_dir = GAMES_DIR / folder_name

        target_dir.mkdir(parents=True, exist_ok=True)

        suffix = archive_path.suffix.lower()

        try:
            if suffix == ".zip":
                ok, msg = self._extract_zip(archive_path, target_dir, password, progress_callback)
            elif suffix in (".rar", ".r00", ".r01"):
                ok, msg = self._extract_rar(archive_path, target_dir, password, progress_callback)
            else:
                # Пробуем через 7z на всё остальное
                ok, msg = self._extract_7z(archive_path, target_dir, password, progress_callback)

            if ok:
                return True, msg, target_dir
            return False, msg, None

        except Exception as e:
            return False, f"Ошибка распаковки: {e}", None

    def _extract_zip(
        self,
        archive: Path,
        target: Path,
        password: Optional[str],
        progress_callback: Optional[Callable[[str], None]],
    ) -> Tuple[bool, str]:
        if progress_callback:
            progress_callback("Распаковываю ZIP...")

        pwd = password.encode("utf-8") if password else None

        # Сначала пробуем pyzipper (лучше работает с AES-паролями)
        if pyzipper:
            try:
                with pyzipper.AESZipFile(archive, "r") as zf:
                    if pwd:
                        zf.setpassword(pwd)
                    zf.extractall(target)
                return True, "ZIP успешно распакован"
            except Exception:
                pass  # fallback на обычный zipfile

        try:
            with zipfile.ZipFile(archive, "r") as zf:
                if pwd:
                    zf.setpassword(pwd)
                zf.extractall(target)
            return True, "ZIP успешно распакован"
        except RuntimeError as e:
            if "password" in str(e).lower() or "Bad password" in str(e):
                return False, "Неверный пароль к ZIP"
            return False, str(e)
        except Exception as e:
            return False, f"Ошибка ZIP: {e}"

    def _extract_rar(
        self,
        archive: Path,
        target: Path,
        password: Optional[str],
        progress_callback: Optional[Callable[[str], None]],
    ) -> Tuple[bool, str]:
        if progress_callback:
            progress_callback("Распаковываю RAR...")

        # 1. Пробуем через 7-Zip (самый надёжный способ на Windows)
        if self._7z_path:
            return self._extract_7z(archive, target, password, progress_callback)

        # 2. Пробуем rarfile
        if rarfile is None:
            return False, "Нужен 7-Zip или rarfile + UnRAR для RAR-архивов"

        try:
            rf = rarfile.RarFile(archive)
            if password:
                rf.setpassword(password)
            rf.extractall(target)
            return True, "RAR успешно распакован"
        except rarfile.BadRarFile:
            return False, "Повреждённый RAR"
        except rarfile.PasswordRequired:
            return False, "Нужен пароль к RAR"
        except rarfile.BadPassword:
            return False, "Неверный пароль к RAR"
        except Exception as e:
            return False, f"Ошибка RAR: {e}"

    def _extract_7z(
        self,
        archive: Path,
        target: Path,
        password: Optional[str],
        progress_callback: Optional[Callable[[str], None]],
    ) -> Tuple[bool, str]:
        if not self._7z_path:
            return False, "7-Zip не найден. Установи 7-Zip для поддержки RAR/7z"

        if progress_callback:
            progress_callback("Распаковываю через 7-Zip...")

        cmd = [self._7z_path, "x", str(archive), f"-o{target}", "-y"]
        if password:
            cmd.append(f"-p{password}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if result.returncode == 0:
                return True, "Успешно распаковано через 7-Zip"
            err = result.stderr or result.stdout or "неизвестная ошибка"
            if "Wrong password" in err or "password" in err.lower():
                return False, "Неверный пароль"
            return False, f"7-Zip ошибка: {err[:200]}"
        except Exception as e:
            return False, f"Не удалось запустить 7-Zip: {e}"

    def find_exe(self, folder: Path, preferred_names: Optional[List[str]] = None) -> Optional[Path]:
        """
        Ищет самый вероятный .exe для запуска игры.
        Игнорирует unins*, unity crash handler и прочий мусор.
        """
        if not folder.exists():
            return None

        exes = []
        ignore_keywords = [
            "unins", "unitycrash", "crashhandler", "redist", "vcredist",
            "directx", "setup", "install", "launcher_old", "dotnet",
        ]

        for root, dirs, files in os.walk(folder):
            # не лезем глубоко в ненужные папки
            dirs[:] = [d for d in dirs if d.lower() not in ("__macosx", ".git", "node_modules")]

            for f in files:
                if f.lower().endswith(".exe"):
                    full = Path(root) / f
                    name_lower = f.lower()
                    if any(k in name_lower for k in ignore_keywords):
                        continue
                    exes.append(full)

        if not exes:
            return None

        # Если есть предпочтительные имена — ищем их
        if preferred_names:
            for pref in preferred_names:
                for e in exes:
                    if pref.lower() in e.name.lower():
                        return e

        # Берём самый большой по размеру (обычно это основная игра)
        exes.sort(key=lambda p: p.stat().st_size, reverse=True)
        return exes[0]

    def install_from_archive(
        self,
        archive_path: str | Path,
        title: str,
        password: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        delete_archive_after: bool = True,
    ) -> Tuple[bool, str, Optional[Path], Optional[Path]]:
        """
        Полный цикл: распаковка → поиск exe → удаление архива.
        Возвращает (успех, сообщение, install_path, exe_path)
        """
        archive_path = Path(archive_path)

        ok, msg, install_path = self.extract(
            archive_path, password=password, progress_callback=progress_callback
        )
        if not ok or install_path is None:
            return False, msg, None, None

        if progress_callback:
            progress_callback("Ищу исполняемый файл...")

        exe = self.find_exe(install_path, preferred_names=[title])

        if exe is None:
            return False, "Распаковалось, но .exe не найден. Укажи его вручную.", install_path, None

        if delete_archive_after:
            try:
                archive_path.unlink(missing_ok=True)
                if progress_callback:
                    progress_callback("Архив удалён")
            except Exception:
                pass  # не критично

        return True, f"Игра установлена! Найден: {exe.name}", install_path, exe
