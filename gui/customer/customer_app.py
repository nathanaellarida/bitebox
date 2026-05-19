"""Entry-point helper for launching the customer portal flow."""
from __future__ import annotations

from gui.customer.customer_login_window import CustomerLoginWindow
from gui.customer.customer_main_window import CustomerMainWindow


def run_customer_portal() -> None:
    """Show the login/register dialog, then the main customer window."""
    login = CustomerLoginWindow()
    if not login.exec():
        return
    if not login.customer:
        return
    win = CustomerMainWindow(login.customer)
    win.show()
    # Keep a reference so the window isn't garbage-collected
    global _open_customer_window
    _open_customer_window = win  # noqa


_open_customer_window: CustomerMainWindow | None = None
