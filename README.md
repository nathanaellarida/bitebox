# BiteBox — Order & Product Inventory Management System

A desktop **Point-of-Sale (POS) and inventory management** application built with **Python 3.11+** and **PyQt6**, designed for small to mid-sized retail and food businesses.

A single **Sign In** window serves as the shared entry point. It automatically routes to the correct portal based on the credentials entered — no role selection required.

- **Staff / Admin credentials** → Management Portal (Dashboard, Products, Orders, Reports, and more)
- **Customer credentials** → Customer Self-Service Portal (Menu, Cart, Orders, Profile, Notifications)

Closing either portal returns the user to Sign In, so the next person can log in without restarting the app.

---

## Cross-Platform Compatibility

The project runs on **Windows, macOS, and Linux** without any code changes. Here is why:

| Concern | How it is handled |
|---|---|
| File paths | All paths use `pathlib.Path` — never hardcoded backslashes |
| Database | SQLite file stored relative to `main.py` via `Path(__file__).resolve().parent` |
| Fonts | QSS font stack: Inter → SF Pro Text (macOS) → Segoe UI (Windows) → Helvetica Neue → Arial |
| Icons | `qtawesome` renders vector icons at runtime — no platform-specific icon files |
| Images | `Pillow` decodes JPG/PNG/WEBP reliably on all platforms |
| Emoji fallbacks | Used only as placeholder text inside `QLabel`, which Qt renders via the system emoji font on every OS |
| SMTP | Uses Python's standard-library `smtplib` — identical on all platforms |

**What will look slightly different across platforms:**
- Window chrome (title bar, close/minimize buttons) follows the native OS style — this is expected Qt behavior.
- Font rendering is slightly crisper on macOS (Core Text) vs. Windows (DirectWrite). The layout and spacing are identical.
- On macOS, the app may ask for network permission the first time it sends a test email — click Allow.

---

## Tech Stack

| Component | Library | Version |
|---|---|---|
| Language | Python | 3.11+ |
| GUI framework | PyQt6 | 6.11.0 |
| Qt runtime | PyQt6-Qt6 | 6.11.0 |
| Charts | PyQt6-Charts | 6.11.0 |
| ORM | SQLAlchemy | 2.0.49 |
| Database | SQLite | (bundled with Python) |
| Password hashing | bcrypt | 5.0.0 |
| PDF export | reportlab | 4.5.1 |
| Vector icons | qtawesome | 1.4.2 |
| Image decoding | Pillow | 12.2.0 |
| Email | smtplib / email | (Python stdlib) |

---

## Features

### Staff / Admin Portal
- **Dashboard** — KPI cards with period filter; bar, pie, and line charts; recent-orders table; auto-refresh every 60 s
- **Products** — Full CRUD with images, option groups (size, toppings, etc.), soft-delete, active/inactive toggle
- **Categories** — Add, rename, soft-delete
- **Orders** — Status workflow (`Pending → Processing → Ready → Completed`), full audit trail, email confirmation
- **New Order** — Staff-side order placement with product grid, options dialog, promo-code validation
- **Customers** — Search, view, deactivate / reactivate accounts
- **Promotions** — Percentage or fixed-amount discount codes with date ranges, usage limits, and product scoping
- **Reports** — Products and Orders reports with filters; export to **CSV** or **PDF**
- **Staff Management** *(Admin only)* — Add, edit, deactivate staff; assign Admin or Staff roles
- **Settings** — Store info, SMTP config with test-send, light / dark theme toggle

### Customer Portal
- **Menu** — Hero banner, category filter, responsive product card grid with food images
- **Cart** — Side panel with quantity controls, promo-code entry, live discount; badge on cart icon shows item count
- **Checkout** — 2-step dialog: order type, structured delivery address, payment method (Cash / GCash / Card with Luhn check)
- **Orders** — Personal order history with status and item details
- **Notifications** — Bell-icon popup with real-time order-status feed
- **Profile** — Edit name, contact, structured delivery address, change password; saved address auto-fills checkout

### Cross-Cutting
- Strict per-field form validation with red-outline error markers on every form
- Toast notifications for non-blocking confirmations (fade in / hold / fade out)
- HTML order-confirmation emails with itemized table and store branding
- Light and dark themes switchable at runtime
- SQLite migrations applied automatically on startup — no manual schema management

---

## Requirements

- **Python 3.11 or newer** — download from [python.org](https://www.python.org/downloads/)
- A desktop OS: Windows 10/11, macOS 12 or newer, or Ubuntu 20.04+
- Internet access only if you plan to send emails via SMTP

> **macOS note:** If Python is not installed, the easiest way is via [Homebrew](https://brew.sh):
> ```bash
> brew install python@3.11
> ```

---

## Setup

Open a terminal in the project root folder (`Larida_OrderAndProductInventoryManagementSystem`) and follow the steps for your OS.

### Windows — Command Prompt

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python main.py
```

### Windows — PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

> **macOS — if you see `qt.qpa.plugin` errors:** Qt on macOS sometimes needs the Xcode command-line tools.
> Run `xcode-select --install` once, then retry.

On the very first launch, `inventory.db` is created in the project root and pre-seeded with default accounts, sample products, orders, and promo codes. No separate database setup is needed.

---

## Running the App

1. Activate your virtual environment (see Setup above).
2. From the project root, run:
   - Windows: `python main.py`
   - macOS / Linux: `python main.py`
3. The **Sign In** window appears. Use one of the default accounts below, or click **Create account** to register a new customer.
4. Closing any portal window returns you to Sign In. Closing the Sign In window exits the app.

---

## Default Accounts

| Role | Email | Password |
|---|---|---|
| Admin | admin@store.com | `Admin@1234` |
| Staff | maria@store.com | `Staff@1234` |
| Customer | juan@example.com | `Customer@1234` |
| Customer | sofia@example.com | `Customer@1234` |

---

## Seeded Sample Data

The first launch pre-populates the database so every screen is immediately usable:

**Categories:** Beverages · Snacks · Main Dishes

**Products:**

| Product | Category | Price | Stock |
|---|---|---|---|
| Iced Coffee | Beverages | ₱120.00 | 50 |
| Lemonade | Beverages | ₱90.00 | 40 |
| Potato Chips | Snacks | ₱55.00 | 100 |
| Spaghetti | Main Dishes | ₱180.00 | 25 |
| Chicken Adobo | Main Dishes | ₱220.00 | 20 |

**Sample Orders:** 4 orders spread over the past week (Dine-In, Takeout, Delivery; Cash, GCash, Credit Card) with full audit trails.

**Promo Codes:**

| Code | Type | Value | Minimum |
|---|---|---|---|
| `SAVE10` | Percentage | 10% off | None |
| `MABUHAY50` | Fixed Amount | ₱50.00 off | ₱500.00 |

To reset to a clean state, delete `inventory.db` and rerun `python main.py`.

---

## Sample Workflows

### As a customer

1. Sign in (or click **Create account** to register — the form includes a structured delivery address block).
2. Browse the menu, click **+** to add items. The cart icon shows a live count badge.
3. Enter a promo code (`SAVE10` or `MABUHAY50`) and click **Apply**.
4. Click **Checkout** → pick Dine-In, Takeout, or Delivery → choose a payment method → **Place Order**.
5. A success toast appears; if SMTP is configured, an email confirmation is sent.
6. Switch to **Order History** to track status, or **Profile** to update your saved delivery address.

### As staff or admin

1. Sign in with a staff account.
2. Use **Products** to add or edit items, including option groups and stock counts.
3. Use **Orders** to advance status or cancel; cancelling restores stock automatically.
4. Use **Promotions** to issue discount codes.
5. Use **Reports** to filter and export to CSV or PDF.
6. Admins additionally manage **Staff** accounts and can permanently delete products/categories.

---

## Project Structure

```
├── main.py                    # Entry point; manages the login loop
├── config.py / config.json    # Path constants and runtime settings
├── requirements.txt           # Pinned dependencies
├── database/
│   ├── models.py              # SQLAlchemy ORM models (10 tables)
│   ├── db_manager.py          # Session factory, migrations, init
│   └── seed_data.py           # First-run seed: staff, customers, products, orders
├── models/                    # Python dataclasses (data transfer objects)
├── services/                  # Business logic layer
│   ├── exporters.py           # Abstract BaseExporter + concrete subclasses
│   └── ...                    # auth, cart, order, product, report, email services
├── gui/
│   ├── widgets/
│   │   ├── validators.py      # Shared form validators (email, phone, card, etc.)
│   │   ├── badged_icon_button.py  # Cart icon with live count badge
│   │   └── toast.py           # Non-blocking fade-in/out notifications
│   ├── customer/              # Customer portal windows and tabs
│   └── ...                    # Admin portal tabs
└── assets/
    ├── styles/                # theme.qss and theme_dark.qss
    └── images/customer/       # Product images (auto-matched by product name)
```

---

## SMTP Configuration

Open **Settings → Email** in the running app, fill in host, port, and credentials, then click **Test Email**. Settings are saved to `config.json`. Email is optional — the app runs fine without it; only order-confirmation emails will be skipped.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: PyQt6` | Virtual environment not activated, or `pip install -r requirements.txt` not run |
| App closes immediately | Run `python main.py` from the project root; check the terminal for a traceback |
| Forgot admin password | Delete `inventory.db` and rerun `python main.py` to reseed |
| Charts or icons missing | Run `pip install --force-reinstall -r requirements.txt` |
| macOS: `qt.qpa.plugin` error | Run `xcode-select --install`, then retry |
| macOS: permission dialog on email send | Click Allow — this is a one-time macOS network permission prompt |
| PowerShell: `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first |
