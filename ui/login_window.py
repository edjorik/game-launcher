"""
Окно авторизации. Тёмное, красивое, без лишнего говна.
"""

import customtkinter as ctk
from typing import Callable, Optional

from core.auth import AuthManager
from config import ACCENT_COLOR, APP_NAME


class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master, on_success: Callable, auth: AuthManager):
        super().__init__(master)
        self.auth = auth
        self.on_success = on_success

        self.title(f"{APP_NAME} — Вход")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(fg_color="#0F0F13")

        # Центрируем
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 210
        y = (self.winfo_screenheight() // 2) - 260
        self.geometry(f"+{x}+{y}")

        self._build_ui()
        self.grab_set()  # модальное

    def _build_ui(self):
        # Заголовок
        title = ctk.CTkLabel(
            self,
            text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=ACCENT_COLOR,
        )
        title.pack(pady=(40, 8))

        subtitle = ctk.CTkLabel(
            self,
            text="Войди, чтобы продолжить",
            font=ctk.CTkFont(size=14),
            text_color="#9CA3AF",
        )
        subtitle.pack(pady=(0, 30))

        # Форма
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=40, fill="x")

        self.username_entry = ctk.CTkEntry(
            form,
            placeholder_text="Логин",
            height=44,
            corner_radius=10,
            border_color="#2D2D3A",
            fg_color="#1A1A24",
            font=ctk.CTkFont(size=14),
        )
        self.username_entry.pack(fill="x", pady=(0, 12))

        self.password_entry = ctk.CTkEntry(
            form,
            placeholder_text="Пароль",
            show="•",
            height=44,
            corner_radius=10,
            border_color="#2D2D3A",
            fg_color="#1A1A24",
            font=ctk.CTkFont(size=14),
        )
        self.password_entry.pack(fill="x", pady=(0, 8))

        self.error_label = ctk.CTkLabel(
            form,
            text="",
            text_color="#EF4444",
            font=ctk.CTkFont(size=12),
        )
        self.error_label.pack(pady=(0, 12))

        # Кнопки
        self.login_btn = ctk.CTkButton(
            form,
            text="Войти",
            height=46,
            corner_radius=10,
            fg_color=ACCENT_COLOR,
            hover_color="#6D28D9",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_login,
        )
        self.login_btn.pack(fill="x", pady=(0, 10))

        self.register_btn = ctk.CTkButton(
            form,
            text="Создать аккаунт",
            height=42,
            corner_radius=10,
            fg_color="transparent",
            border_width=1,
            border_color="#3F3F50",
            hover_color="#1F1F2E",
            font=ctk.CTkFont(size=13),
            command=self._on_register,
        )
        self.register_btn.pack(fill="x")

        # Подсказка для mock
        hint = ctk.CTkLabel(
            self,
            text="Mock: admin / 123456",
            font=ctk.CTkFont(size=11),
            text_color="#4B5563",
        )
        hint.pack(side="bottom", pady=20)

        self.username_entry.bind("<Return>", lambda e: self._on_login())
        self.password_entry.bind("<Return>", lambda e: self._on_login())

    def _on_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.error_label.configure(text="Заполни все поля, бля")
            return

        self.login_btn.configure(state="disabled", text="Входим...")
        self.update()

        success, msg = self.auth.login(username, password)

        if success:
            self.destroy()
            self.on_success()
        else:
            self.error_label.configure(text=msg)
            self.login_btn.configure(state="normal", text="Войти")

    def _on_register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.error_label.configure(text="Заполни логин и пароль")
            return

        self.register_btn.configure(state="disabled", text="Регистрируем...")
        self.update()

        success, msg = self.auth.register(username, password)

        self.error_label.configure(
            text=msg,
            text_color="#22C55E" if success else "#EF4444",
        )
        self.register_btn.configure(state="normal", text="Создать аккаунт")
