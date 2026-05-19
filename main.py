"""Application entry point.

A single Sign In window handles both staff and customer credentials.
The right portal opens based on which authentication succeeded.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QEventLoop, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow

from config import STYLES_DIR, load_config
from database.db_manager import init_db
from gui.main_window import MainWindow
from gui.customer.customer_login_window import CustomerLoginWindow
from gui.customer.customer_main_window import CustomerMainWindow

_app: QApplication | None = None


def apply_theme() -> None:
    if _app is None:
        return
    theme = load_config().get("theme", "light")
    qss_file = STYLES_DIR / ("theme_dark.qss" if theme == "dark" else "theme.qss")
    try:
        _app.setStyleSheet(qss_file.read_text(encoding="utf-8"))
    except Exception:
        _app.setStyleSheet("")


def _show_window_modally(window: QMainWindow) -> None:
    """Show a top-level window and block until it closes.

    Closing returns control to the outer login loop instead of exiting
    the whole application.
    """
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    loop = QEventLoop()
    window.destroyed.connect(loop.quit)
    window.show()
    loop.exec()


def main() -> int:
    global _app
    init_db()
    _app = QApplication(sys.argv)
    # We manage window lifecycle manually so the app doesn't exit
    # between successive sign-ins.
    _app.setQuitOnLastWindowClosed(False)
    apply_theme()

    while True:
        login = CustomerLoginWindow()
        if not login.exec():
            break
        if login.staff is not None:
            _show_window_modally(MainWindow(login.staff))
        elif login.customer is not None:
            _show_window_modally(CustomerMainWindow(login.customer))
        else:
            break
        # Re-apply theme in case the user toggled it inside Settings.
        apply_theme()
    return 0


if __name__ == "__main__":
    sys.exit(main())
