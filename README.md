# BiteBox — Order & Product Inventory Management System


**BiteBox** is a cross-platform desktop point-of-sale and inventory management system for food and retail businesses. Built with Python and PyQt6, it combines a staff management portal with a customer self-service ordering experience in one application.

One sign-in screen recognizes the account type and opens the right workspace automatically:

- **Admins and staff** manage products, stock, orders, customers, promotions, reports, and store settings.
- **Customers** browse the menu, build a cart, apply promotions, place orders, and track their order history.

## Highlights

### Staff and admin portal

- Dashboard with KPIs, sales charts, recent orders, and period filters
- Product and category management with images, options, stock levels, and soft deletion
- Order workflow from `Pending` to `Completed`, including cancellation and stock restoration
- Staff-assisted order entry with product customization and promo-code validation
- Customer account search, review, activation, and deactivation
- Percentage and fixed-amount promotions with validity dates, usage limits, and product scope
- Filterable product and order reports with CSV and PDF export
- Role-based staff management for admins
- Store, email, and light/dark theme settings

### Customer portal

- Responsive, category-filtered menu with product images and options
- Cart with live totals, quantity controls, and promotion support
- Dine-in, takeout, and delivery checkout flows
- Cash, GCash, and card payment options with card-number validation
- Personal order history and real-time status notifications
- Profile, password, contact, and saved delivery-address management

### Platform features

- SQLite database initialization and migrations on startup
- Secure password hashing with bcrypt
- Field-level form validation and non-blocking toast notifications
- Optional branded HTML order-confirmation emails through SMTP
- Cross-platform paths, fonts, image handling, and native window behavior

## Tech stack

| Area | Technology |
| --- | --- |
| Language | Python 3.11+ |
| Desktop UI | PyQt6 and PyQt6-Charts |
| Data layer | SQLAlchemy and SQLite |
| Authentication | bcrypt |
| Reports | ReportLab and CSV |
| Icons and images | QtAwesome and Pillow |
| Email | Python `smtplib` and `email` |

Exact dependency versions are pinned in [`requirements.txt`](requirements.txt).

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/nathanaellarida/inventory-system.git
cd inventory-system
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install and run

```bash
pip install -r requirements.txt
python main.py
```

On first launch, BiteBox creates `inventory.db` and seeds it with sample users, products, promotions, and orders. No separate database server is required.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@store.com` | `Admin@1234` |
| Staff | `maria@store.com` | `Staff@1234` |
| Customer | `juan@example.com` | `Customer@1234` |
| Customer | `sofia@example.com` | `Customer@1234` |

> These accounts are intended for local demonstration only. Change or remove them before using the application with real data.

## Sample data

The initial database includes:

- Beverages, Snacks, and Main Dishes categories
- Iced Coffee, Lemonade, Potato Chips, Spaghetti, and Chicken Adobo products
- Completed and pending dine-in, takeout, and delivery orders
- `SAVE10` for 10% off
- `MABUHAY50` for PHP 50 off orders of at least PHP 500

Delete `inventory.db` and restart the application to rebuild the sample database from scratch.

## Configuration

BiteBox creates a local `config.json` when one does not exist. You can also copy [`config.example.json`](config.example.json) to `config.json` before the first run and customize it.

```powershell
Copy-Item config.example.json config.json
```

```bash
cp config.example.json config.json
```

Store settings and SMTP credentials can also be updated from **Settings** in the staff portal. `config.json` is intentionally ignored by Git because it may contain private email credentials.

Email is optional. Without SMTP configuration, all inventory and ordering features still work; only outgoing confirmation messages are skipped.

## Project structure

```text
inventory-system/
|-- main.py                 # Application entry point and portal lifecycle
|-- config.py               # Paths, defaults, and configuration helpers
|-- config.example.json     # Safe configuration template
|-- requirements.txt        # Pinned Python dependencies
|-- database/               # ORM models, sessions, migrations, and seed data
|-- models/                 # Application data-transfer models
|-- services/               # Business logic, reports, exports, and email
|-- gui/                    # Staff and customer PyQt6 interfaces
|   |-- customer/           # Customer portal, cart, checkout, and profile
|   `-- widgets/            # Shared tables, cards, validators, and toasts
`-- assets/                 # Themes and customer-facing images
```

The application follows a layered structure: PyQt6 screens call service modules, services apply business rules, and SQLAlchemy handles persistence.

## Typical workflows

### Customer order

1. Sign in or create a customer account.
2. Browse the menu and add configured products to the cart.
3. Apply an eligible promotion.
4. Choose dine-in, takeout, or delivery and a payment method.
5. Place the order and follow its progress from **My Orders** or **Notifications**.

### Staff order management

1. Sign in with a staff or admin account.
2. Review incoming orders and advance their status.
3. Maintain product availability, options, and stock.
4. Create promotions and export operational reports.
5. Use an admin account to manage staff access.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `ModuleNotFoundError: PyQt6` | Activate the virtual environment and run `pip install -r requirements.txt`. |
| App closes immediately | Run `python main.py` in a terminal and inspect the traceback. |
| PowerShell blocks activation | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate the environment again. |
| Qt plugin error on macOS | Install the Xcode command-line tools with `xcode-select --install`. |
| Charts or icons are missing | Reinstall dependencies with `pip install --force-reinstall -r requirements.txt`. |
| Demo data or password needs resetting | Delete `inventory.db` and launch BiteBox again. |

## Platform support

BiteBox is designed for Windows, macOS, and Linux. Window chrome and font rendering follow each operating system, but the application layout and features remain the same.
