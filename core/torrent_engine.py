"""
Встроенный торрент-движок на aria2.
Человеку ничего ставить не нужно — лаунчер сам управляет скачиванием.
"""

import json
import os
import subprocess
import time
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
import threading
import urllib.request
import urllib.error

from config import LIBRARY_ROOT, CACHE_DIR, GAMES_DIR

ARIA2_DIR = LIBRARY_ROOT / "aria2"
ARIA2_EXE = ARIA2_DIR / "aria2c.exe"
ARIA2_RPC_PORT = 6800
ARIA2_RPC_SECRET = "nexus_launcher_secret"


class TorrentEngine:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._ensure_aria2()
        self._start_aria2()

    def _ensure_aria2(self):
        """Если aria2c.exe нет — скачиваем официальный релиз (Windows)."""
        ARIA2_DIR.mkdir(parents=True, exist_ok=True)
        if ARIA2_EXE.exists():
            return

        # Официальный релиз aria2 1.37.0 (Windows 64-bit)
        url = "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip"
        zip_path = CACHE_DIR / "aria2.zip"

        try:
            print("[TorrentEngine] Скачиваю aria2...")
            urllib.request.urlretrieve(url, zip_path)

            import zipfile
            with zipfile.ZipFile(zip_path, "r") as z:
                # Ищем aria2c.exe внутри архива
                for name in z.namelist():
                    if name.lower().endswith("aria2c.exe"):
                        with z.open(name) as src, open(ARIA2_EXE, "wb") as dst:
                            dst.write(src.read())
                        break
            zip_path.unlink(missing_ok=True)
            print("[TorrentEngine] aria2 готов")
        except Exception as e:
            print(f"[TorrentEngine] Не удалось скачать aria2: {e}")
            print("Положи aria2c.exe вручную в", ARIA2_DIR)

    def _start_aria2(self):
        if not ARIA2_EXE.exists():
            return

        # Уже запущен?
        if self._rpc_alive():
            return

        cmd = [
            str(ARIA2_EXE),
            "--enable-rpc",
            f"--rpc-listen-port={ARIA2_RPC_PORT}",
            f"--rpc-secret={ARIA2_RPC_SECRET}",
            "--rpc-allow-origin-all",
            "--dir=" + str(GAMES_DIR),
            "--continue=true",
            "--max-connection-per-server=16",
            "--split=16",
            "--min-split-size=1M",
            "--bt-max-peers=100",
            "--seed-time=0",          # после скачивания не сидируем вечно
            "--check-integrity=true",
            "--file-allocation=none",
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            # Даём секунду подняться
            time.sleep(1.2)
        except Exception as e:
            print(f"[TorrentEngine] Не удалось запустить aria2: {e}")

    def _rpc(self, method: str, params: list = None) -> Any:
        if params is None:
            params = []
        payload = {
            "jsonrpc": "2.0",
            "id": "nexus",
            "method": method,
            "params": [f"token:{ARIA2_RPC_SECRET}"] + params,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{ARIA2_RPC_PORT}/jsonrpc",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if "error" in result:
                    raise RuntimeError(result["error"])
                return result.get("result")
        except Exception as e:
            raise RuntimeError(f"aria2 RPC error: {e}")

    def _rpc_alive(self) -> bool:
        try:
            self._rpc("aria2.getVersion")
            return True
        except Exception:
            return False

    def add_magnet(self, magnet: str, download_dir: Optional[Path] = None) -> str:
        """Добавляет magnet. Возвращает gid."""
        self._start_aria2()
        options = {}
        if download_dir:
            options["dir"] = str(download_dir)
        gid = self._rpc("aria2.addUri", [[magnet], options])
        return gid

    def add_torrent_file(self, torrent_path: str | Path, download_dir: Optional[Path] = None) -> str:
        import base64
        data = Path(torrent_path).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        options = {}
        if download_dir:
            options["dir"] = str(download_dir)
        gid = self._rpc("aria2.addTorrent", [b64, [], options])
        return gid

    def get_status(self, gid: str) -> Dict[str, Any]:
        keys = [
            "gid", "status", "totalLength", "completedLength",
            "downloadSpeed", "files", "errorMessage", "dir"
        ]
        return self._rpc("aria2.tellStatus", [gid, keys])

    def is_finished(self, gid: str) -> bool:
        try:
            st = self.get_status(gid)
            return st.get("status") == "complete"
        except Exception:
            return False

    def get_progress(self, gid: str) -> tuple[float, str]:
        """Возвращает (процент 0-100, текст статуса)."""
        try:
            st = self.get_status(gid)
            total = int(st.get("totalLength") or 0)
            done = int(st.get("completedLength") or 0)
            speed = int(st.get("downloadSpeed") or 0)
            status = st.get("status", "unknown")

            if total > 0:
                pct = (done / total) * 100
            else:
                pct = 0.0

            speed_mb = speed / 1024 / 1024
            text = f"{status} • {done // 1024 // 1024} / {total // 1024 // 1024} МБ • {speed_mb:.1f} МБ/с"
            return pct, text
        except Exception as e:
            return 0.0, str(e)

    def get_downloaded_files(self, gid: str) -> List[Path]:
        try:
            st = self.get_status(gid)
            files = []
            for f in st.get("files", []):
                path = f.get("path")
                if path:
                    files.append(Path(path))
            return files
        except Exception:
            return []

    def stop(self):
        if self.process and self.process.poll() is None:
            try:
                self._rpc("aria2.shutdown")
            except Exception:
                self.process.terminate()
