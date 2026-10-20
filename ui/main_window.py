"""
Главное окно лаунчера.
Тёмный, современный, с карточками игр. Steam может идти курить.
"""

import customtkinter as ctk
from typing import Optional
import threading

from core.auth import AuthManager
from core.downloader import GameDownloader
from core.updater import Updater
from config import APP_NAME, APP_VERSION, ACCENT_COLOR, GAMES_DIR


class GameCard(ctk.CTkFrame):
    def __init__(self, master, game: dict, downloader: GameDownloader, **kwargs):
        super().__init__(master, corner_radius=16, fg_color="#16161F", **kwargs)
        self.game = game
        self.downloader = downloader
        self.is_downloading = False

        self.grid_columnconfigure(0, weight=1)

        # Заголовок + версия
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text=game["title"],
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="w")

        version = ctk.CTkLabel(
            header,
            text=f"v{game.get('version', '?')}",
            font=ctk.CTkFont(size=12),
            text_color="#6B7280",
        )
        version.grid(row=0, column=1, sticky="e")

        # Описание
        desc = ctk.CTkLabel(
            self,
            text=game.get("description", ""),
            font=ctk.CTkFont(size=13),
            text_color="#9CA3AF",
            wraplength=340,
            justify="left",
            anchor="w",
        )
        desc.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        # Размер + тип
        meta = ctk.CTkLabel(
            self,
            text=f"{game.get('size_mb', '?')} МБ  •  {game.get('download_type', 'http').upper()}",
            font=ctk.CTkFont(size=12),
            text_color="#6B7280",
        )
        meta.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))

        # Прогресс
        self.progress = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            progress_color=ACCENT_COLOR,
            fg_color="#2A2A38",
        )
        self.progress.set(0)
        self.progress.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.progress.grid_remove()

        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF",
        )
        self.status_label.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 8))
        self.status_label.grid_remove()

        # Кнопка
        self.action_btn = ctk.CTkButton(
            self,
            text="Скачать",
            height=38,
            corner_radius=10,
            fg_color=ACCENT_COLOR,
            hover_color="#6D28D9",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_action,
        )
        self.action_btn.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._update_button_state()

    def _update_button_state(self):
        if self.downloader.is_installed(self.game["id"]):
            self.action_btn.configure(text="Играть", fg_color="#059669", hover_color="#047857")
        else:
            self.action_btn.configure(text="Скачать", fg_color=ACCENT_COLOR, hover_color="#6D28D9")

    def _on_action(self):
        if self.downloader.is_installed(self.game["id"]):
            # TODO: запуск игры
            self.status_label.configure(text="Запуск пока в разработке, брат")
            self.status_label.grid()
            return

        if self.is_downloading:
            return

        self.is_downloading = True
        self.action_btn.configure(state="disabled", text="Скачиваем...")
        self.progress.grid()
        self.status_label.grid()

        def worker():
            def progress(pct, text):
                self.after(0, lambda: self._set_progress(pct, text))

            if self.game.get("download_type") == "torrent" and self.game.get("magnet"):
                ok = self.downloader.start_torrent_via_qbittorrent(
                    self.game["magnet"], self.game["id"]
                )
                self.after(0, lambda: self._on_torrent_result(ok))
            else:
                url = self.game.get("download_url")
                if not url:
                    self.after(0, lambda: self._set_progress(0, "Нет ссылки на скачивание"))
                    self.after(0, self._finish_download)
                    return
                path = self.downloader.download_http(
                    url, self.game["id"], self.game["title"], progress
                )
                self.after(0, lambda: self._finish_download(path is not None))

        threading.Thread(target=worker, daemon=True).start()

    def _set_progress(self, pct: float, text: str):
        self.progress.set(pct / 100)
        self.status_label.configure(text=text)

    def _on_torrent_result(self, ok: bool):
        if ok:
            self.status_label.configure(text="Торрент добавлен в qBittorrent")
            self.action_btn.configure(text="В qBittorrent", state="normal")
        else:
            self.status_label.configure(text="Не удалось добавить торрент (запусти qBittorrent)")
            self.action_btn.configure(state="normal", text="Скачать")
        self.is_downloading = False

    def _finish_download(self, success: bool = True):
        self.is_downloading = False
        if success:
            self.status_label.configure(text="Скачано!")
            self._update_button_state()
        else:
            self.status_label.configure(text="Ошибка скачивания")
            self.action_btn.configure(state="normal", text="Скачать")


class MainWindow(ctk.CTk):
    def __init__(self, auth: AuthManager):
        super().__init__()
        self.auth = auth
        self.downloader = GameDownloader(auth.token)
        self.updater = Updater()

        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color="#0B0B0F")

        # Сетка
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

        # Проверка обновлений в фоне
        threading.Thread(target=self._check_updates, daemon=True).start()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#111118")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Лого
        logo = ctk.CTkLabel(
            sidebar,
            text=APP_NAME,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=ACCENT_COLOR,
        )
        logo.pack(pady=(30, 40), padx=20)

        # Навигация
        nav_items = [
            ("🎮  Библиотека", self._show_library),
            ("⬇️  Загрузки", lambda: None),
            ("⚙️  Настройки", lambda: None),
        ]

        for text, cmd in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                anchor="w",
                height=42,
                corner_radius=10,
                fg_color="transparent",
                hover_color="#1F1F2E",
                font=ctk.CTkFont(size=14),
                command=cmd,
            )
            btn.pack(fill="x", padx=12, pady=3)

        # Юзер внизу
        user_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        user_frame.pack(side="bottom", fill="x", padx=16, pady=20)

        username = self.auth.user.get("username", "???") if self.auth.user else "???"
        user_label = ctk.CTkLabel(
            user_frame,
            text=f"👤  {username}",
            font=ctk.CTkFont(size=13),
            text_color="#9CA3AF",
        )
        user_label.pack(anchor="w")

        logout_btn = ctk.CTkButton(
            user_frame,
            text="Выйти",
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color="#3F3F50",
            hover_color="#1F1F2E",
            font=ctk.CTkFont(size=12),
            command=self._logout,
        )
        logout_btn.pack(fill="x", pady=(8, 0))

    def _build_main(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Хедер
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Библиотека",
            font=ctk.CTkFont(size=26, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        self.update_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#6B7280",
        )
        self.update_label.grid(row=0, column=1, sticky="e")

        # Скролл с играми
        self.scroll = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color="transparent",
            corner_radius=0,
        )
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure((0, 1), weight=1, uniform="cards")

        self._load_games()

    def _load_games(self):
        games = self.downloader.get_games_list()

        for i, game in enumerate(games):
            card = GameCard(self.scroll, game, self.downloader)
            row = i // 2
            col = i % 2
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)

    def _check_updates(self):
        has_update, msg = self.updater.check_for_updates()
        self.after(0, lambda: self.update_label.configure(
            text=msg,
            text_color="#22C55E" if not has_update else "#F59E0B",
        ))

        if has_update:
            # Можно показать кнопку "Обновить"
            pass

    def _show_library(self):
        pass  # уже показано

    def _logout(self):
        self.auth.logout()
        self.destroy()
        # В main.py перезапустим логин
