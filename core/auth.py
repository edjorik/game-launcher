"""
Авторизация. Пока локальный mock + готовность к реальному API.
Можно легко заменить на JWT / OAuth / свой бэкенд.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from config import API_BASE_URL, TOKEN_FILE, CONFIG_DIR


class AuthManager:
    def __init__(self):
        self.token: Optional[str] = None
        self.user: Optional[Dict[str, Any]] = None
        self._load_token()

    def _load_token(self):
        if TOKEN_FILE.exists():
            try:
                data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
                self.token = data.get("token")
                self.user = data.get("user")
            except Exception:
                self.token = None
                self.user = None

    def _save_token(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"token": self.token, "user": self.user}
        TOKEN_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _clear_token(self):
        self.token = None
        self.user = None
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()

    def is_authenticated(self) -> bool:
        return bool(self.token and self.user)

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        Пытается залогиниться через API.
        Если сервер недоступен — fallback на локальный mock (для разработки).
        """
        try:
            resp = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={"username": username, "password": password},
                timeout=8,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token") or data.get("token")
                self.user = data.get("user", {"username": username})
                self._save_token()
                return True, "Успешный вход"
            return False, data.get("detail", "Неверный логин или пароль")
        except requests.RequestException:
            # Mock-режим (чтобы можно было тестировать без бэкенда)
            return self._mock_login(username, password)

    def register(self, username: str, password: str, email: str = "") -> tuple[bool, str]:
        try:
            resp = requests.post(
                f"{API_BASE_URL}/auth/register",
                json={"username": username, "password": password, "email": email},
                timeout=8,
            )
            if resp.status_code in (200, 201):
                return True, "Регистрация успешна. Теперь войди."
            data = resp.json()
            return False, data.get("detail", "Ошибка регистрации")
        except requests.RequestException:
            return self._mock_register(username, password)

    def logout(self):
        self._clear_token()

    def _mock_login(self, username: str, password: str) -> tuple[bool, str]:
        """Локальный mock для разработки. Пароль: 123456"""
        users_file = CONFIG_DIR / "mock_users.json"
        if not users_file.exists():
            # Создаём тестового юзера
            users = {
                "admin": {
                    "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
                    "username": "admin",
                }
            }
            users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")

        users = json.loads(users_file.read_text(encoding="utf-8"))
        user = users.get(username)
        if not user:
            return False, "Пользователь не найден (mock)"

        if user["password_hash"] == hashlib.sha256(password.encode()).hexdigest():
            self.token = "mock_token_" + username
            self.user = {"username": username, "id": 1}
            self._save_token()
            return True, "Вход через mock (сервер недоступен)"
        return False, "Неверный пароль (mock)"

    def _mock_register(self, username: str, password: str) -> tuple[bool, str]:
        users_file = CONFIG_DIR / "mock_users.json"
        users = {}
        if users_file.exists():
            users = json.loads(users_file.read_text(encoding="utf-8"))

        if username in users:
            return False, "Пользователь уже существует (mock)"

        users[username] = {
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            "username": username,
        }
        users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")
        return True, "Зарегистрирован в mock. Логин: твой ник, пароль тот же."
