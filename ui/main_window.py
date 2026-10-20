"""
Главное окно Nexus Launcher.
Магазин (общие игры с паролем внутри) + личная библиотека.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable

from core.auth import AuthManager
from core.library import Library
from core.catalog import Catalog
from core.installer import Installer
from core.updater import Updater
from core.downloader import GameDownloader
from config import (
    APP_NAME, APP_VERSION, ACCENT_COLOR, ACCENT_HOVER,
    BG_DARK, BG_CARD, BG_SIDEBAR, BORDER_GLOW, TEXT_DIM,
    SUCCESS, WARNING, DANGER, GAMES_DIR, TORRENTS_DIR, ARCHIVES_DIR
)


class AddGameDialog(ctk.CTkToplevel):
    """Добавление СВОЕЙ игры (папка / архив). Пароль только здесь."""

    def __init__(self, master, library: Library, on_added: Callable):
        super().__init__(master)
        self.library = library
        self.on_added = on_added
        self.installer = Installer()

        self.title("Добавить свою игру")
        self.geometry("520x520")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.grab_set()

        self.archive_path: Optional[str] = None
        self.folder_path: Optional[str] = None

        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Добавить свою игру",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=ACCENT_COLOR).pack(pady=(24, 6))

        ctk.CTkLabel(self, text="Только для локальных игр. Пароль нужен только тут.",
                     font=ctk.CTkFont(size=13), text_color=TEXT_DIM).pack(pady=(0, 16))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=30, fill="x")

        ctk.CTkLabel(form, text="Название", anchor="w",
                     font=ctk.CTkFont(size=12), text_color=TEXT_DIM).pack(fill="x")
        self.title_entry = ctk.CTkEntry(form, height=40, corner_radius=10,
                                        fg_color="#1A1A24", border_color="#2D2D3A",
                                        placeholder_text="Название игры")
        self.title_entry.pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(form, text="Пароль к архиву (только если добавляешь архив)",
                     anchor="w", font=ctk.CTkFont(size=12), text_color=TEXT_DIM).pack(fill="x")
        self.password_entry = ctk.CTkEntry(form, height=40, corner_radius=10,
                                           fg_color="#1A1A24", border_color="#2D2D3A",
                                           placeholder_text="Пусто = без пароля", show="•")
        self.password_entry.pack(fill="x", pady=(4, 16))

        btn_style = dict(height=42, corner_radius=10, font=ctk.CTkFont(size=13))

        ctk.CTkButton(form, text="📁  Выбрать папку с игрой",
                      fg_color="#1F1F2E", hover_color="#2A2A3A",
                      border_width=1, border_color="#3F3F50",
                      command=self._pick_folder, **btn_style).pack(fill="x", pady=4)

        ctk.CTkButton(form, text="📦  Выбрать архив (ZIP / RAR)",
                      fg_color="#1F1F2E", hover_color="#2A2A3A",
                      border_width=1, border_color="#3F3F50",
                      command=self._pick_archive, **btn_style).pack(fill="x", pady=4)

        self.status = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=12), text_color=TEXT_DIM)
        self.status.pack(pady=(12, 8))

        self.progress = ctk.CTkProgressBar(form, height=6, progress_color=ACCENT_COLOR, fg_color="#2A2A38")
        self.progress.pack(fill="x", pady=(0, 8))
        self.progress.pack_forget()

        self.add_btn = ctk.CTkButton(form, text="Добавить в библиотеку",
                                     height=46, corner_radius=10,
                                     fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
                                     font=ctk.CTkFont(size=14, weight="bold"),
                                     command=self._on_add)
        self.add_btn.pack(fill="x", pady=(8, 0))

    def _pick_folder(self):
        path = filedialog.askdirectory(title="Выбери папку с игрой")
        if path:
            self.folder_path = path
            self.archive_path = None
            self.status.configure(text=f"Папка: {Path(path).name}", text_color=SUCCESS)

    def _pick_archive(self):
        path = filedialog.askopenfilename(title="Выбери архив",
                                          filetypes=[("Архивы", "*.zip *.rar *.7z"), ("Все", "*.*")])
        if path:
            self.archive_path = path
            self.folder_path = None
            self.status.configure(text=f"Архив: {Path(path).name}", text_color=WARNING)

    def _on_add(self):
        title = self.title_entry.get().strip()
        if not title:
            self.status.configure(text="Введи название", text_color=DANGER)
            return

        password = self.password_entry.get() or None

        if self.folder_path:
            exe = self.installer.find_exe(Path(self.folder_path), preferred_names=[title])
            game = self.library.add_game(title=title, install_path=self.folder_path,
                                         exe_path=str(exe) if exe else None)
            if exe:
                self.library.set_exe(game["id"], str(exe))
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
                    self.archive_path, title=title, password=password,
                    progress_callback=prog, delete_archive_after=True)

                def done():
                    self.progress.stop()
                    self.progress.pack_forget()
                    if ok:
                        self.library.add_game(title=title,
                                              install_path=str(install_path) if install_path else None,
                                              exe_path=str(exe_path) if exe_path else None)
                        self.on_added()
                        self.destroy()
                    else:
                        self.status.configure(text=msg, text_color=DANGER)
                        self.add_btn.configure(state="normal", text="Добавить в библиотеку")

                self.after(0, done)

            threading.Thread(target=worker, daemon=True).start()
            return

        self.status.configure(text="Выбери папку или архив", text_color=DANGER)


class GameCard(ctk.CTkFrame):
    """Карточка в личной библиотеке."""

    def __init__(self, master, game: dict, library: Library, installer: Installer, on_change: Callable, **kwargs):
        super().__init__(master, corner_radius=14, fg_color=BG_CARD,
                         border_width=1, border_color="#1F1F2E", **kwargs)
        self.game = game
        self.library = library
        self.installer = installer
        self.on_change = on_change

        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text=game["title"],
                     font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w")

        status = game.get("status", "not_installed")
        if status == "ready":
            status_text, status_color = "Готова", SUCCESS
        elif game.get("torrent_path") or game.get("from_shop"):
            status_text, status_color = "Ожидает распаковки", WARNING
        else:
            status_text, status_color = "Не установлена", TEXT_DIM

        ctk.CTkLabel(top, text=status_text, font=ctk.CTkFont(size=11),
                     text_color=status_color).grid(row=0, column=1, sticky="e")

        path_text = game.get("exe_path") or game.get("install_path") or "—"
        path_text = str(path_text)
        if len(path_text) > 55:
            path_text = "..." + path_text[-52:]

        ctk.CTkLabel(self, text=path_text, font=ctk.CTkFont(size=11),
                     text_color=TEXT_DIM, anchor="w").grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

        if game.get("exe_path") and Path(game["exe_path"]).exists():
            ctk.CTkButton(btns, text="▶  Играть", width=110, height=34,
                          corner_radius=8, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
                          font=ctk.CTkFont(size=13, weight="bold"),
                          command=self._play).pack(side="left", padx=(0, 6))
        else:
            if game.get("archive_password") is not None or game.get("from_shop"):
                ctk.CTkButton(btns, text="📦 Распаковать", width=120, height=34,
                              corner_radius=8, fg_color=WARNING, hover_color="#D97706",
                              font=ctk.CTkFont(size=12, weight="bold"),
                              command=self._unpack_with_stored_password).pack(side="left", padx=(0, 6))
            else:
                ctk.CTkButton(btns, text="Указать .exe", width=110, height=34,
                              corner_radius=8, fg_color="#1F1F2E", hover_color="#2A2A3A",
                              border_width=1, border_color="#3F3F50",
                              font=ctk.CTkFont(size=12),
                              command=self._pick_exe).pack(side="left", padx=(0, 6))

        ctk.CTkButton(btns, text="🗑", width=36, height=34,
                      corner_radius=8, fg_color="transparent",
                      hover_color="#3F1F1F", text_color=DANGER,
                      command=self._delete).pack(side="right")

    def _play(self):
        exe = self.game.get("exe_path")
        if not exe or not Path(exe).exists():
            messagebox.showerror("Ошибка", "Файл запуска не найден")
            return
        try:
            subprocess.Popen([exe], cwd=str(Path(exe).parent))
            self.library.update_game(self.game["id"],
                                     last_played=__import__("datetime").datetime.now().isoformat())
        except Exception as e:
            messagebox.showerror("Ошибка запуска", str(e))

    def _pick_exe(self):
        path = filedialog.askopenfilename(title="Выбери .exe",
                                          filetypes=[("Executable", "*.exe"), ("Все", "*.*")])
        if path:
            self.library.set_exe(self.game["id"], path)
            self.on_change()

    def _unpack_with_stored_password(self):
        path = filedialog.askopenfilename(
            title="Выбери скачанный архив",
            filetypes=[("Архивы", "*.zip *.rar *.7z"), ("Все", "*.*")]
        )
        if not path:
            return

        password = self.game.get("archive_password")

        def worker():
            ok, msg, install_path, exe_path = self.installer.install_from_archive(
                path,
                title=self.game["title"],
                password=password,
                delete_archive_after=True,
            )
            def done():
                if ok:
                    self.library.mark_installed(
                        self.game["id"],
                        install_path=str(install_path) if install_path else "",
                        exe_path=str(exe_path) if exe_path else "",
                    )
                    messagebox.showinfo("Готово", msg)
                    self.on_change()
                else:
                    messagebox.showerror("Ошибка", msg)
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _delete(self):
        if messagebox.askyesno("Удалить", f"Убрать «{self.game['title']}» из библиотеки?\n(файлы не удаляются)"):
            self.library.remove_game(self.game["id"])
            self.on_change()


class ShopCard(ctk.CTkFrame):
    """Карточка в магазине — один клик установки."""

    def __init__(self, master, game: dict, library: Library, downloader: GameDownloader,
                 on_installed: Callable, **kwargs):
        super().__init__(master, corner_radius=14, fg_color=BG_CARD,
                         border_width=1, border_color="#1F1F2E", **kwargs)
        self.game = game
        self.library = library
        self.downloader = downloader
        self.on_installed = on_installed

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=game.get("title", "???"),
                     font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        desc = game.get("description") or ""
        if desc:
            ctk.CTkLabel(self, text=desc, font=ctk.CTkFont(size=12),
                         text_color=TEXT_DIM, wraplength=320, anchor="w", justify="left").grid(
                row=1, column=0, sticky="w", padx=16, pady=(0, 6))

        size = game.get("size_mb")
        meta = f"{size} МБ" if size else "Торрент"
        ctk.CTkLabel(self, text=meta, font=ctk.CTkFont(size=11),
                     text_color=TEXT_DIM).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 10))

        already = any(g.get("catalog_id") == game.get("id") for g in library.get_all())

        btn_text = "В библиотеке" if already else "⬇  Установить"
        btn_state = "disabled" if already else "normal"
        btn_color = "#374151" if already else ACCENT_COLOR

        self.install_btn = ctk.CTkButton(
            self, text=btn_text, height=36, corner_radius=8,
            fg_color=btn_color, hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            state=btn_state, command=self._install
        )
        self.install_btn.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))

    def _install(self):
        g = self.game
        magnet = g.get("magnet")

        lib_game = self.library.add_game(
            title=g.get("title", "Без названия"),
            torrent_path=None,
        )
        self.library.update_game(
            lib_game["id"],
            catalog_id=g.get("id"),
            from_shop=True,
            archive_password=g.get("archive_password"),
            status="downloading",
        )

        if magnet:
            ok = self.downloader.start_torrent_via_qbittorrent(magnet, lib_game["id"])
            if ok:
                title = g.get("title", "Игра")
                messagebox.showinfo(
                    "Торрент запущен",
                    f"«{title}» добавлен в qBittorrent.\n\n"
                    "Когда скачается — зайди в Библиотеку и нажми «Распаковать».\n"
                    "Пароль вводить не нужно, он уже известен лаунчеру."
                )
            else:
                messagebox.showwarning(
                    "qBittorrent",
                    "Не удалось добавить торрент.\n"
                    "Убедись, что qBittorrent запущен и WebUI включен (localhost:8080).\n"
                    "Игра всё равно добавлена в библиотеку — сможешь распаковать архив вручную."
                )
        else:
            messagebox.showinfo("Добавлено", "Игра добавлена в библиотеку. Когда будет архив — нажми «Распаковать».")

        self.on_installed()


class MainWindow(ctk.CTk):
    def __init__(self, auth: AuthManager):
        super().__init__()
        self.auth = auth
        self.library = Library()
        self.catalog = Catalog()
        self.installer = Installer()
        self.downloader = GameDownloader(auth.token)
        self.updater = Updater()

        self.title(f"{APP_NAME}  •  v{APP_VERSION}")
        self.geometry("1150x720")
        self.minsize(960, 640)
        self.configure(fg_color=BG_DARK)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()
        self.show_page("library")

        threading.Thread(target=self._check_updates, daemon=True).start()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=BG_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(28, 32), padx=16)
        ctk.CTkLabel(logo_frame, text="NEXUS",
                     font=ctk.CTkFont(size=24, weight="bold"), text_color=ACCENT_COLOR).pack()
        ctk.CTkLabel(logo_frame, text="LAUNCHER",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_DIM).pack()

        self.nav_buttons = {}
        for key, text, icon in [
            ("library", "Библиотека", "🎮"),
            ("shop", "Магазин", "🛒"),
            ("downloads", "Загрузки", "⬇"),
            ("settings", "Настройки", "⚙"),
        ]:
            btn = ctk.CTkButton(
                self.sidebar, text=f"  {icon}   {text}", anchor="w",
                height=44, corner_radius=10, fg_color="transparent",
                hover_color="#1A1A28", font=ctk.CTkFont(size=14), text_color="#D1D5DB",
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        user_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        user_frame.pack(side="bottom", fill="x", padx=14, pady=18)
        username = (self.auth.user or {}).get("username", "???")
        ctk.CTkLabel(user_frame, text=f"👤  {username}",
                     font=ctk.CTkFont(size=13), text_color=TEXT_DIM, anchor="w").pack(fill="x")
        ctk.CTkButton(user_frame, text="Выйти", height=32, corner_radius=8,
                      fg_color="transparent", border_width=1, border_color="#2D2D3A",
                      hover_color="#1F1F2E", font=ctk.CTkFont(size=12),
                      command=self._logout).pack(fill="x", pady=(8, 0))

    def _set_active_nav(self, key: str):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color="#1A1A28", text_color=ACCENT_COLOR,
                              border_width=1, border_color=BORDER_GLOW)
            else:
                btn.configure(fg_color="transparent", text_color="#D1D5DB", border_width=0)

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.pages = {}

        # Библиотека
        lib = ctk.CTkFrame(self.content, fg_color="transparent")
        lib.grid_columnconfigure(0, weight=1)
        lib.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(lib, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Библиотека",
                     font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header, text="＋  Добавить свою",
                      width=150, height=36, corner_radius=10,
                      fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self._open_add_dialog).grid(row=0, column=1, sticky="e")

        self.games_scroll = ctk.CTkScrollableFrame(lib, fg_color="transparent")
        self.games_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        self.games_scroll.grid_columnconfigure((0, 1), weight=1, uniform="g")
        self.pages["library"] = lib

        # Магазин
        shop = ctk.CTkFrame(self.content, fg_color="transparent")
        shop.grid_columnconfigure(0, weight=1)
        shop.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(shop, text="Магазин",
                     font=ctk.CTkFont(size=26, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 4))
        ctk.CTkLabel(shop, text="Игры для всех. Пароль уже внутри — ставишь в один клик.",
                     font=ctk.CTkFont(size=13), text_color=TEXT_DIM).grid(
            row=0, column=0, sticky="w", padx=28, pady=(56, 12))

        self.shop_scroll = ctk.CTkScrollableFrame(shop, fg_color="transparent")
        self.shop_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        self.shop_scroll.grid_columnconfigure((0, 1), weight=1, uniform="s")
        self.pages["shop"] = shop

        # Загрузки
        dl = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(dl, text="Загрузки",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=28, pady=(24, 8))
        ctk.CTkLabel(dl, text="Очередь и прогресс появятся здесь позже.\nПока смотри статус в qBittorrent.",
                     font=ctk.CTkFont(size=14), text_color=TEXT_DIM, justify="left").pack(
            anchor="w", padx=28, pady=10)
        self.pages["downloads"] = dl

        # Настройки
        st = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(st, text="Настройки",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=28, pady=(24, 16))

        box = ctk.CTkFrame(st, fg_color=BG_CARD, corner_radius=12)
        box.pack(fill="x", padx=28, pady=8)

        ctk.CTkLabel(box, text="Папка игр", font=ctk.CTkFont(size=13),
                     text_color=TEXT_DIM).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(box, text=str(GAMES_DIR), font=ctk.CTkFont(size=13),
                     text_color="#E5E7EB").pack(anchor="w", padx=16, pady=(0, 10))

        ctk.CTkLabel(box, text="Каталог магазина (пароли игр лежат здесь)",
                     font=ctk.CTkFont(size=13), text_color=TEXT_DIM).pack(anchor="w", padx=16, pady=(4, 2))
        ctk.CTkLabel(box, text=str(Path.home() / "NexusLauncher" / "config" / "catalog.json"),
                     font=ctk.CTkFont(size=12), text_color="#9CA3AF").pack(anchor="w", padx=16, pady=(0, 16))

        self.update_info = ctk.CTkLabel(st, text="", font=ctk.CTkFont(size=13), text_color=TEXT_DIM)
        self.update_info.pack(anchor="w", padx=28, pady=12)
        self.pages["settings"] = st

    def show_page(self, key: str):
        self._set_active_nav(key)
        for p in self.pages.values():
            p.grid_forget()
        self.pages[key].grid(row=0, column=0, sticky="nsew")

        if key == "library":
            self._refresh_library()
        elif key == "shop":
            self._refresh_shop()

    def _refresh_library(self):
        for w in self.games_scroll.winfo_children():
            w.destroy()
        games = self.library.get_all()
        if not games:
            ctk.CTkLabel(self.games_scroll,
                         text="Библиотека пуста.\nЗайди в Магазин или добавь свою игру.",
                         font=ctk.CTkFont(size=15), text_color=TEXT_DIM, justify="center").grid(
                row=0, column=0, columnspan=2, pady=80)
            return
        for i, g in enumerate(games):
            card = GameCard(self.games_scroll, g, self.library, self.installer,
                            on_change=self._refresh_library)
            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)

    def _refresh_shop(self):
        for w in self.shop_scroll.winfo_children():
            w.destroy()
        games = self.catalog.get_all()
        if not games:
            ctk.CTkLabel(self.shop_scroll,
                         text="Магазин пока пуст.\nДобавь игры в catalog.json\n(папка NexusLauncher/config/)",
                         font=ctk.CTkFont(size=15), text_color=TEXT_DIM, justify="center").grid(
                row=0, column=0, columnspan=2, pady=80)
            return
        for i, g in enumerate(games):
            card = ShopCard(self.shop_scroll, g, self.library, self.downloader,
                            on_installed=self._refresh_shop)
            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)

    def _open_add_dialog(self):
        AddGameDialog(self, self.library, on_added=self._refresh_library)

    def _check_updates(self):
        has_update, msg = self.updater.check_for_updates()
        color = WARNING if has_update else SUCCESS
        self.after(0, lambda: self.update_info.configure(text=msg, text_color=color))

    def _logout(self):
        self.auth.logout()
        self.destroy()
