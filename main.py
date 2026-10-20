"""
Nexus Launcher — точка входа.
Запускай этот файл.
"""

import customtkinter as ctk
from config import THEME, APP_NAME
from core.auth import AuthManager
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def main():
    ctk.set_appearance_mode(THEME)
    ctk.set_default_color_theme("dark-blue")  # базовая, мы всё равно переопределяем цвета

    auth = AuthManager()

    # Скрытое корневое окно (нужно для CTkToplevel)
    root = ctk.CTk()
    root.withdraw()

    def open_main():
        app = MainWindow(auth)
        app.protocol("WM_DELETE_WINDOW", app.destroy)
        app.mainloop()

    if auth.is_authenticated():
        open_main()
    else:
        def on_login_success():
            open_main()

        login = LoginWindow(root, on_success=on_login_success, auth=auth)
        login.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()


if __name__ == "__main__":
    main()
