"""Application configuration loader/saver."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config.json"
DB_PATH = ROOT_DIR / "inventory.db"
ASSETS_DIR = ROOT_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
ICONS_DIR = ASSETS_DIR / "icons"
STYLES_DIR = ASSETS_DIR / "styles"
EXPORTS_DIR = ROOT_DIR / "exports"

# Ensure directories exist
for _d in (ASSETS_DIR, IMAGES_DIR, ICONS_DIR, STYLES_DIR, EXPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG: dict[str, Any] = {
    "store": {
        "name": "BiteBox",
        "contact": "+63-000-000-0000",
        "email": "hello@bitebox.example",
        "address": "Your store address",
    },
    "smtp": {
        "host": "smtp.gmail.com",
        "port": 587,
        "username": "",
        "password": "",
        "use_tls": True,
        "from_name": "BiteBox",
    },
    "theme": "light",
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # merge defaults to fill missing keys
        merged = DEFAULT_CONFIG.copy()
        for k, v in data.items():
            if isinstance(v, dict) and k in merged:
                merged[k].update(v)
            else:
                merged[k] = v
        return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
