"""
Главное окно Nexus Launcher.
Киберпанк-вайб, рабочие разделы, добавление своих игр, установка из архивов.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable

from core.auth import AuthManager
from core.library import Library
from core.installer import Installer
from core.updater import Updater
from config import (
    APP_NAME, APP_VERSION, ACCENT_COLOR, ACCENT_HOVER,
    BG_DARK, BG_CARD, BG_SIDEBAR, BORDER_GLOW, TEXT_DIM,
    SUCCESS, WARNING, DANGER, GAMES_DIR, TORRENTS_DIR, ARCHIVES_DIR
)


class AddGameDialog(ctk.CTkToplevel):
    """Диалог добавления игры — папка / архив / торрент."""

    def __init__(self, master, library: Library, on_added: Callable):
        super().__init__(master)
        self.library = library
        self.on_added = on_added
        self.installer = Installer()

        self.title("Добавить игру")
        self.geometry("520x580")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.grab_set()

        self.archive_path: Optional[str] = None
        self.torrent_path: Optional[str] = None
        self.folder_path: Optional[str] = None

        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Добавить игру",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=ACCENT_COLOR
        ).pack(pady=(24, 6))

        ctk.CTkLabel(
            self, text="Выбери способ добавления",
            font=ctk.CTkFont(size=13), text_color=TEXT_DIM
        ).pack(pady=(0, 16))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=30, fill="x")

        # Название
        ctk.CTkLabel(form, text="Название игры", anchor="w",
                     font=ctk.CTkFont(size=12), text_color=TEXT_DIM).pack(fill="x")
        self.title_entry = ctk.CTkEntry(
            form, height=40, corner_radius=10,
            fg_color="#1A1A24", border_color="#2D2D3A",
            placeholder_text="Например: Cyberpunk 2077"
        )
        self.title_entry.pack(fill="x", pady=(4, 14))

        # Пароль (для архивов)
        ctk.CTkLabel(form, text="Пароль к архиву (если есть)", anchor="w",
                     font=ctk.CTkFont(size=12), text_color=TEXT_DIM).pack(fill="x")
        self.password_entry = ctk.CTkEntry(
            form, height=40, corner_radius=10,
            fg_color="#1A1A24", border_color="#2D2D3A",
            placeholder_text="Оставь пустым, если без пароля", show="•"
        )
        self.password_entry.pack(fill="x", pady=(4, 18))

        # Кнопки выбора
        btn_style = dict(height=42, corner_radius=10, font=ctk.CTkFont(size=13))

        self.btn_folder = ctk.CTkButton(
            form, text="📁  Выбрать папку с игрой",
            fg_color="#1F1F2E", hover_color="#2A2A3A",
            border_width=1, border_color="#3F3F50",
            command=self._pick_folder, **btn_style
        )
        self.btn_folder.pack(fill="x", pady=4)

        self.btn_archive = ctk.CTkButton(
            form, text="📦  Выбрать архив (ZIP / RAR)",
            fg_color="#1F1F2E", hover_color="#2A2A3A",
            border_width=1, border_color="#3F3F50",
            command=self._pick_archive, **btn_style
        )
        self.btn_archive.pack(fill="x", pady=4)

        self.btn_torrent = ctk.CTkButton(
            form, text="🧲  Выбрать .torrent файл",
            fg_color="#1F1F2E", hover_color="#2A2A3A",
            border_width=1, border_color="#3F3F50",
            command=self._pick_torrent, **btn_style
        )
        self.btn_torrent.pack(fill="x", pady=4)

        self.status = ctk.CTkLabel(
            form, text="", font=ctk.CTkFont(size=12), text_color=TEXT_DIM
        )
        self.status.pack(pady=(12, 8))

        self.progress = ctk.CTkProgressBar(
            form, height=6, progress_color=ACCENT_COLOR, fg_color="#2A2A38"
        )
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        self.progress.pack_forget()

        # Добавить
        self.add_btn = ctk.CTkButton(
            form, text="Добавить в библиотеку",
            height=46, corner_radius=10,
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_add
        )
        self.add_btn.pack(fill="x", pady=(8, 0))

    def _pick_folder(self):
        path = filedialog.askdirectory(title="Выбери папку с игрой")
        if path:
            self.folder_path = path
            self.archive_path = None
            self.torrent_path = None
            self.status.configure(text=f"Папка: {Path(path).name}", text_color=SUCCESS)

    def _pick_archive(self):
        path = filedialog.askopenfilename(
            title="Выбери архив",
            filetypes=[("Архивы", "*.zip *.rar *.7z"), ("Все файлы", "*.*")]
        )
        if path:
            self.archive_path = path
            self.folder_path = None
            self.torrent_path = None
            self.status.configure(text=f"Архив: {Path(path).name}", text_color=WARNING)

    def _pick_torrent(self):
        path = filedialog.askopenfilename(
            title="Выбери .torrent",
            filetypes=[("Torrent", "*.torrent"), ("Все файлы", "*.*")]
        )
        if path:
            self.torrent_path = path
            self.archive_path = None
            self.folder_path = None
            # Копируем торрент в нашу папку
            dest = TORRENTS_DIR / Path(path).name
            try:
                import shutil
                shutil.copy2(path, dest)
                self.torrent_path = str(dest)
            except Exception:
                pass
            self.status.configure(text=f"Torrent: {Path(path).name}", text_color=ACCENT_COLOR)

    def _on_add(self):
        title = self.title_entry.get().strip()
        if not title:
            self.status.configure(text="Введи название игры, бля", text_color=DANGER)
            return

        password = self.password_entry.get() or None

        if self.folder_path:
            # Просто добавляем папку, ищем exe
            exe = self.installer.find_exe(Path(self.folder_path), preferred_names=[title])
            game = self.library.add_game(
                title=title,
                install_path=self.folder_path,
                exe_path=str(exe) if exe else None,
            )
            if exe:
                self.library.set_exe(game["id"], str(exe))
            self.on_added()
            self.destroy()
            return

        if self.torrent_path:
            game = self.library.add_game(
                title=title,
                torrent_path=self.torrent_path,
            )
            self.on_added()
            self.destroy()
            return

        if self.archive_path:
            self.add_btn.configure(state="disabled", text="Устанавливаю...")
            self.progress.pack(fill="x", pady=(0, 8))
            self.progress.start()

            def worker():
                def prog(msg):
                    self.after(0, lambda: self.status.configure(text=msg))

                ok, msg, install_path, exe_path = self.installer.install_from_archive(
                    self.archive_path,
                    title=title,
                    password=password,
                    progress_callback=prog,
                    delete_archive_after=True,
                )

                def done():
                    self.progress.stop()
                    self.progress.pack_forget()
                    if ok:
                        self.library.add_game(
                            title=title,
                            install_path=str(install_path) if install_path else None,
                            exe_path=str(exe_path) if exe_path else None,
                        )
                        self.on_added()
                        self.destroy()
                    else:
                        self.status.configure(text=msg, text_color=DANGER)
                        self.add_btn.configure(state="normal", text="Добавить в библиотеку")

                self.after(0, done)

            threading.Thread(target=worker, daemon=True).start()
            return

        self.status.configure(text="Выбери папку, архив или торрент", text_color=DANGER)


class GameCard(ctk.CTkFrame):
    def __init__(self, master, game: dict, library: Library, on_change: Callable, **kwargs):
        super().__init__(
            master, corner_radius=14, fg_color=BG_CARD,
            border_width=1, border_color="#1F1F2E", **kwargs
        )
        self.game = game
        self.library = library
        self.on_change = on_change

        self.grid_columnconfigure(0, weight=1)

        # Заголовок
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top, text=game["title"],
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")

        status_color = SUCCESS if game.get("status") == "ready" else TEXT_DIM
        status_text = "Готова" if game.get("status") == "ready" else "Не установлена"
        if game.get("torrent_path") and not game.get("exe_path"):
            status_text = "Торрент"
            status_color = ACCENT_COLOR

        ctk.CTkLabel(
            top, text=status_text, font=ctk.CTkFont(size=11),
            text_color=status_color
        ).grid(row=0, column=1, sticky="e")

        # Путь
        path_text = game.get("exe_path") or game.get("install_path") or game.get("torrent_path") or "—"
        path_text = str(path_text)
        if len(path_text) > 55:
            path_text = "..." + path_text[-52:]

        ctk.CTkLabel(
            self, text=path_text, font=ctk.CTkFont(size=11),
            text_color=TEXT_DIM, anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        # Кнопки
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

        if game.get("exe_path") and Path(game["exe_path"]).exists():
            ctk.CTkButton(
                btns, text="▶  Играть", width=110, height=34,
                corner_radius=8, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=self._play
            ).pack(side="left", padx=(0, 6))
        else:
            ctk.CTkButton(
                btns, text="Указать .exe", width=110, height=34,
                corner_radius=8, fg_color="#1F1F2E", hover_color="#2A2A3A",
                border_width=1, border_color="#3F3F50",
                font=ctk.CTkFont(size=12),
                command=self._pick_exe
            ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btns, text="🗑", width=36, height=34,
            corner_radius=8, fg_color="transparent",
            hover_color="#3F1F1F", text_color=DANGER,
            command=self._delete
        ).pack(side="right")

    def _play(self):
        exe = self.game.get("exe_path")
        if not exe or not Path(exe).exists():
            messagebox.showerror("Ошибка", "Файл запуска не найден")
            return
        try:
            subprocess.Popen([exe], cwd=str(Path(exe).parent))
            self.library.update_game(self.game["id"], last_played=__import__("datetime").datetime.now().isoformat())
        except Exception as e:
            messagebox.showerror("Ошибка запуска", str(e))

    def _pick_exe(self):
        path = filedialog.askopenfilename(
            title="Выбери .exe игры",
            filetypes=[("Executable", "*.exe"), ("Все файлы", "*.*")]
        )
        if path:
            self.library.set_exe(self.game["id"], path)
            self.on_change()

    def _delete(self):
        if messagebox.askyesno("Удалить", f"Убрать «{self.game['title']}» из библиотеки?\n(файлы игры не удаляются)"):
            self.library.remove_game(self.game["id"])
            self.on_change()


class MainWindow(ctk.CTk):
    def __init__(self, auth: AuthManager):
        super().__init__()
        self.auth = auth
        self.library = Library()
        self.updater = Updater()
        self.current_page = "library"

        self.title(f"{APP_NAME}  •  v{APP_VERSION}")
        self.geometry("1150x720")
        self.minsize(960, 640)
        self.configure(fg_color=BG_DARK)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()

        self.show_page("library")

        # Проверка обновлений
        threading.Thread(target=self._check_updates, daemon=True).start()

    # ───────────────────────── Sidebar ─────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=BG_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Лого
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(28, 36), padx=16)

        ctk.CTkLabel(
            logo_frame, text="NEXUS",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=ACCENT_COLOR
        ).pack()
        ctk.CTkLabel(
            logo_frame, text="LAUNCHER",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_DIM
        ).pack()

        # Навигация — ровные кнопки
        self.nav_buttons = {}
        nav_items = [
            ("library", "Библиотека", "🎮"),
            ("downloads", "Загрузки", "⬇"),
            ("settings", "Настройки", "⚙"),
        ]

        for key, text, icon in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {icon}   {text}",
                anchor="w",
                height=44,
                corner_radius=10,
                fg_color="transparent",
                hover_color="#1A1A28",
                font=ctk.CTkFont(size=14),
                text_color="#D1D5DB",
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        # Юзер внизу
        user_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        user_frame.pack(side="bottom", fill="x", padx=14, pady=18)

        username = (self.auth.user or {}).get("username", "???")
        ctk.CTkLabel(
            user_frame, text=f"👤  {username}",
            font=ctk.CTkFont(size=13), text_color=TEXT_DIM, anchor="w"
        ).pack(fill="x")

        ctk.CTkButton(
            user_frame, text="Выйти",
            height=32, corner_radius=8,
            fg_color="transparent", border_width=1, border_color="#2D2D3A",
            hover_color="#1F1F2E", font=ctk.CTkFont(size=12),
            command=self._logout
        ).pack(fill="x", pady=(8, 0))

    def _set_active_nav(self, key: str):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color="#1A1A28", text_color=ACCENT_COLOR,
                              border_width=1, border_color=BORDER_GLOW)
            else:
                btn.configure(fg_color="transparent", text_color="#D1D5DB",
                              border_width=0)

    # ───────────────────────── Content ─────────────────────────
    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Три страницы
        self.pages = {}

        # --- Библиотека ---
        lib_page = ctk.CTkFrame(self.content, fg_color="transparent")
        lib_page.grid_columnconfigure(0, weight=1)
        lib_page.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(lib_page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Библиотека",
            font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="＋  Добавить игру",
            width=150, height=36, corner_radius=10,
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_add_dialog
        ).grid(row=0, column=1, sticky="e")

        self.games_scroll = ctk.CTkScrollableFrame(
            lib_page, fg_color="transparent", corner_radius=0
        )
        self.games_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        self.games_scroll.grid_columnconfigure((0, 1), weight=1, uniform="g")

        self.pages["library"] = lib_page

        # --- Загрузки ---
        dl_page = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(
            dl_page, text="Загрузки",
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(anchor="w", padx=28, pady=(24, 8))

        ctk.CTkLabel(
            dl_page,
            text="Здесь будет очередь загрузок и прогресс торрентов.\nПока что добавляй игры через «Добавить игру».",
            font=ctk.CTkFont(size=14), text_color=TEXT_DIM, justify="left"
        ).pack(anchor="w", padx=28, pady=10)

        self.pages["downloads"] = dl_page

        # --- Настройки ---
        st_page = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(
            st_page, text="Настройки",
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(anchor="w", padx=28, pady=(24, 16))

        settings_box = ctk.CTkFrame(st_page, fg_color=BG_CARD, corner_radius=12)
        settings_box.pack(fill="x", padx=28, pady=8)

        ctk.CTkLabel(
            settings_box, text="Папка библиотеки игр",
            font=ctk.CTkFont(size=13), text_color=TEXT_DIM
        ).pack(anchor="w", padx=16, pady=(14, 2))

        ctk.CTkLabel(
            settings_box, text=str(GAMES_DIR),
            font=ctk.CTkFont(size=13), text_color="#E5E7EB"
        ).pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            settings_box, text="Архивы временно кладутся сюда, после установки удаляются.",
            font=ctk.CTkFont(size=12), text_color=TEXT_DIM
        ).pack(anchor="w", padx=16, pady=(0, 4))

        ctk.CTkLabel(
            settings_box, text=str(ARCHIVES_DIR),
            font=ctk.CTkFont(size=12), text_color="#9CA3AF"
        ).pack(anchor="w", padx=16, pady=(0, 16))

        self.update_info = ctk.CTkLabel(
            st_page, text="",
            font=ctk.CTkFont(size=13), text_color=TEXT_DIM
        )
        self.update_info.pack(anchor="w", padx=28, pady=12)

        self.pages["settings"] = st_page

    def show_page(self, key: str):
        self.current_page = key
        self._set_active_nav(key)

        for k, page in self.pages.items():
            page.grid_forget()

        self.pages[key].grid(row=0, column=0, sticky="nsew")

        if key == "library":
            self._refresh_games()

    def _refresh_games(self):
        for w in self.games_scroll.winfo_children():
            w.destroy()

        games = self.library.get_all()

        if not games:
            ctk.CTkLabel(
                self.games_scroll,
                text="Библиотека пуста.\nНажми «Добавить игру», чтобы закинуть свою.",
                font=ctk.CTkFont(size=15), text_color=TEXT_DIM, justify="center"
            ).grid(row=0, column=0, columnspan=2, pady=80)
            return

        for i, game in enumerate(games):
            card = GameCard(self.games_scroll, game, self.library, on_change=self._refresh_games)
            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)

    def _open_add_dialog(self):
        AddGameDialog(self, self.library, on_added=self._refresh_games)

    def _check_updates(self):
        has_update, msg = self.updater.check_for_updates()
        color = WARNING if has_update else SUCCESS
        self.after(0, lambda: self.update_info.configure(text=msg, text_color=color))

    def _logout(self):
        self.auth.logout()
        self.destroy()
