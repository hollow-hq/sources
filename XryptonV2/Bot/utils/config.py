from __future__ import annotations

import json
import os
import typing
from typing import Any

_CONFIG_CACHE: dict | None = None


def _load_info() -> dict:
    """Load and cache info.json data."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    with open("config.json", "r", encoding="utf-8") as f:
        _CONFIG_CACHE = json.load(f)
    return _CONFIG_CACHE


OWNER_IDS = _load_info().get("OWNER_IDS", [])
EXTENSIONS = _load_info().get("EXTENSIONS", [])
NO_PREFIX = _load_info().get("NO_PREFIX", [])


def get_owner_ids() -> list[int]:
    """Get the list of bot owner IDs."""
    return OWNER_IDS


def get_extensions() -> list[str]:
    """Get the list of extension paths to load."""
    return EXTENSIONS


def get_bot_name() -> str:
    """Get the bot name from config.json."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return str(json.load(f).get("bot", {}).get("bot_name", "Bot"))
    except (OSError, json.JSONDecodeError, AttributeError):
        return "Bot"


def _default_config() -> dict[str, Any]:
    """Return default guild configuration."""
    return {
        "whitelisted": [],
        "admins": [],
        "adminrole": None,
        "punishment": "ban",
        "prefix": ".",
        "staff": None,
        "vip": None,
        "girl": None,
        "guest": None,
        "frnd": None,
        "wlrole": None,
        "reqrole": None,
    }


def getConfig(guild_id: int) -> dict[str, Any]:
    """Get guild configuration.
    
    Returns default config with prefix '.' if guild not found.
    Never raises KeyError for missing guilds.
    """
    try:
        with open("data/config.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _default_config()
    
    if str(guild_id) not in data.get("guilds", {}):
        return _default_config()
    return data["guilds"][str(guild_id)]
