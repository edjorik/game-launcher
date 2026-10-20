# Nexus Launcher 🚀

Красивый игровой лаунчер на Python, от которого Steam курит в сторонке.

## Что уже есть

- ✨ Современный тёмный UI на **CustomTkinter**
- 🔐 Авторизация (реальный API + mock-режим для разработки)
- 📦 Список игр с карточками
- ⬇️ Скачивание игр по HTTP
- 🧲 Поддержка торрентов через **qBittorrent WebAPI** (твой сервер не сдохнет)
- 🔄 Автопроверка обновлений через GitHub Releases
- 🪟 Готовность к сборке в `.exe`

## Быстрый старт

```bash
# 1. Клонируй
git clone https://github.com/edjorik/game-launcher.git
cd game-launcher

# 2. Создай виртуалку (рекомендуется)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. Поставь зависимости
pip install -r requirements.txt

# 4. Запусти
python main.py
```

### Тестовый аккаунт (mock)
- Логин: `admin`
- Пароль: `123456`

## Сборка в .exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "NexusLauncher" --icon=assets/icon.ico main.py
```

Или через Nuitka (быстрее и меньше ложных срабатываний антивируса):

```bash
pip install nuitka
python -m nuitka --onefile --windows-disable-console --enable-plugin=tk-inter main.py
```

## Структура проекта

```
game-launcher/
├── main.py              # Точка входа
├── config.py            # Настройки, пути, цвета
├── requirements.txt
├── core/
│   ├── auth.py          # Авторизация + mock
│   ├── downloader.py    # HTTP + торренты через qBittorrent
│   └── updater.py       # Проверка обновлений через GitHub
└── ui/
    ├── login_window.py  # Окно входа/регистрации
    └── main_window.py   # Главное окно с библиотекой
```

## Что дальше можно добавить

- [ ] Реальный бэкенд (FastAPI / Django)
- [ ] Красивые обложки игр
- [ ] Запуск установленных игр
- [ ] Прогресс торрентов прямо в лаунчере
- [ ] Темы (светлая / кастомные)
- [ ] Система достижений / друзья
- [ ] Автообновление с заменой файлов без боли

## Важно

Сейчас `API_BASE_URL` в `config.py` указывает на заглушку.  
Пока сервер не готов — работает **mock-режим**.  
Когда поднимешь бэкенд — просто поменяй URL.

Для торрентов нужно, чтобы у пользователя был запущен **qBittorrent** с включённым WebUI (обычно `localhost:8080`).

---

Сделано с ненавистью к уродливым лаунчерам.  
Если что-то сломалось — пиши issue или орёшь в чат.
