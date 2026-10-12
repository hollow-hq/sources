from __future__ import annotations

import json
import os
import sys
import io
import time
from typing import Any, Union, Optional, List, Dict

import discord
from discord.ext import commands

from core import Context

try:
    from cashews import cache
except ImportError:
    def cache(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


def _atomic_write(filepath: str, data: dict) -> None:
    """Write data to a JSON file atomically."""
    temp_path = f"{filepath}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(temp_path, filepath)


def _ensure_guild_entry(data: dict, guild_id: str) -> dict:
    """Ensure a guild entry exists in the data, create with defaults if not."""
    if str(guild_id) not in data["guilds"]:
        data["guilds"][str(guild_id)] = {
            "channel": [],
            "role": None,
            "user": [],
            "bypassrole": None,
            "bypassuser": [],
            "commands": [],
        }
    return data["guilds"][str(guild_id)]


# ─── ignore.json ──────────────────────────────────────────────────────────────

def getIgnore(guild_id: int) -> dict[str, Any]:
    """Get ignore configuration for a guild."""
    with open("data/ignore.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return _ensure_guild_entry(data, guild_id)


def updateIgnore(guild_id: int, data: dict[str, Any]) -> None:
    """Update ignore configuration for a guild."""
    with open("data/ignore.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/ignore.json", config)


# ─── extra.json ───────────────────────────────────────────────────────────────

def getExtra(guild_id: int) -> dict[str, Any]:
    """Get extra configuration for a guild."""
    with open("data/extra.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if str(guild_id) not in data["guilds"]:
        default = {
            "owners": [],
            "antiSpam": False,
            "antiLink": False,
            "antiinvites": False,
            "punishment": "mute",
            "whitelisted": [],
            "channel": None,
            "mods": [],
            "modrole": None,
            "ignorechannels": [],
        }
        data["guilds"][str(guild_id)] = default
        _atomic_write("data/extra.json", data)
        return default
    return data["guilds"][str(guild_id)]


def updateExtra(guild_id: int, data: dict[str, Any]) -> None:
    """Update extra configuration for a guild."""
    with open("data/extra.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/extra.json", config)


# ─── autorole.json ────────────────────────────────────────────────────────────

def getautorole(guild_id: int) -> dict[str, Any]:
    """Get autorole configuration for a guild."""
    with open("data/autorole.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if str(guild_id) not in data["guilds"]:
        default = {"bots": [], "humans": []}
        data["guilds"][str(guild_id)] = default
        _atomic_write("data/autorole.json", data)
        return default
    return data["guilds"][str(guild_id)]


def updateautorole(guild_id: int, data: dict[str, Any]) -> None:
    """Update autorole configuration for a guild."""
    with open("data/autorole.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/autorole.json", config)


# ─── vcrole.json ──────────────────────────────────────────────────────────────

def getvcrole(guild_id: int) -> dict[str, Any]:
    """Get VC role configuration for a guild."""
    with open("data/vcrole.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if str(guild_id) not in data["guilds"]:
        default = {"bots": "", "humans": ""}
        data["guilds"][str(guild_id)] = default
        _atomic_write("data/vcrole.json", data)
    return data["guilds"][str(guild_id)]


def updatevcrole(guild_id: int, data: dict[str, Any]) -> None:
    """Update VC role configuration for a guild."""
    with open("data/vcrole.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/vcrole.json", config)


# ─── greet.json ───────────────────────────────────────────────────────────────

def updategreet(guild_id: int, data: dict[str, Any]) -> None:
    """Update greet configuration for a guild."""
    with open("data/greet.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/greet.json", config)


def getgreet(guild_id: int) -> dict[str, Any]:
    """Get greet configuration for a guild."""
    with open("data/greet.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if str(guild_id) not in data["guilds"]:
        default = {
            "autodel": None,
            "channel": [],
            "color": None,
            "embed": False,
            "footer": "",
            "image": "",
            "message": "<<user.mention>> Welcome To <<server.name>>",
            "ping": False,
            "title": "",
            "thumbnail": "",
        }
        data["guilds"][str(guild_id)] = default
        _atomic_write("data/greet.json", data)
    return data["guilds"][str(guild_id)]


# ─── config.json ──────────────────────────────────────────────────────────────

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


def updateConfig(guild_id: int, data: dict[str, Any]) -> None:
    """Update guild configuration."""
    try:
        with open("data/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {"guilds": {}}
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/config.json", config)


# ─── blacklist.json ───────────────────────────────────────────────────────────

def add_user_to_blacklist(user_id: int) -> None:
    """Add a user ID to the blacklist."""
    try:
        with open("data/blacklist.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"ids": []}
    
    user_str = str(user_id)
    if user_str not in data["ids"]:
        data["ids"].append(user_str)
    
    _atomic_write("data/blacklist.json", data)


def remove_user_from_blacklist(user_id: int) -> None:
    """Remove a user ID from the blacklist."""
    try:
        with open("data/blacklist.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    
    user_str = str(user_id)
    if user_str in data["ids"]:
        data["ids"].remove(user_str)
        _atomic_write("data/blacklist.json", data)


def is_blacklisted(user_id: int) -> bool:
    """Check if a user ID is blacklisted."""
    try:
        with open("data/blacklist.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    return str(user_id) in data.get("ids", [])


# ─── anti.json ────────────────────────────────────────────────────────────────

def getanti(guild_id: int) -> str:
    """Get anti-nuke setting for a guild."""
    try:
        with open("data/anti.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "off"
    return data.get("guilds", {}).get(str(guild_id), "off")


def updateanti(guild_id: int, data: str) -> None:
    """Update anti-nuke setting for a guild."""
    try:
        with open("data/anti.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {"guilds": {}}
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/anti.json", config)


# ─── events.json (Hacker/Antinuke) ───────────────────────────────────────────

def getHacker(guild_id: int) -> dict[str, Any]:
    """Get antinuke event configuration for a guild."""
    try:
        with open("data/events.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"guilds": {}}
    
    if str(guild_id) not in data.get("guilds", {}):
        default = {
            "antinuke": {
                "antirole-delete": True,
                "antirole-create": True,
                "antirole-update": True,
                "antichannel-create": True,
                "antichannel-delete": True,
                "antichannel-update": True,
                "antiban": True,
                "antikick": True,
                "antiwebhook": True,
                "antibot": True,
                "antiserver": True,
                "antiping": True,
                "antiprune": True,
                "antiemoji-delete": True,
                "antiemoji-create": True,
                "antiemoji-update": True,
                "antimemberrole-update": True,
            }
        }
        data.setdefault("guilds", {})[str(guild_id)] = default
        _atomic_write("data/events.json", data)
        return default
    return data["guilds"][str(guild_id)]


def updateHacker(guild_id: int, data: dict[str, Any]) -> None:
    """Update antinuke event configuration for a guild."""
    try:
        with open("data/events.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {"guilds": {}}
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/events.json", config)


# ─── logging.json ─────────────────────────────────────────────────────────────

def getLogging(guild_id: int) -> dict[str, Any]:
    """Get logging configuration for a guild."""
    try:
        with open("data/logging.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"guilds": {}}
    
    if str(guild_id) not in data.get("guilds", {}):
        default = {
            "mod": None,
            "role": None,
            "message": None,
            "member": None,
            "channel": None,
            "server": None,
            "voice": None,
        }
        data.setdefault("guilds", {})[str(guild_id)] = default
        _atomic_write("data/logging.json", data)
    return data["guilds"][str(guild_id)]


def updateLogging(guild_id: int, data: dict[str, Any]) -> None:
    """Update logging configuration for a guild."""
    try:
        with open("data/logging.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {"guilds": {}}
    config["guilds"][str(guild_id)] = data
    _atomic_write("data/logging.json", config)


# ─── predicate checks ─────────────────────────────────────────────────────────


def blacklist_check():
    """Check decorator: deny blacklisted users."""
    def predicate(ctx: Context) -> bool:
        return not is_blacklisted(ctx.author.id)
    return commands.check(predicate)


def ignore_check():
    """Check decorator: deny ignored channels/users."""
    def predicate(ctx: Context) -> bool:
        data = getIgnore(ctx.guild.id)
        ch = data["channel"]
        iuser = data["user"]
        buser = data["bypassuser"]
        
        if str(ctx.author.id) in buser:
            return True
        if str(ctx.author.id) in iuser or str(ctx.channel.id) in ch:
            return False
        return True
    return commands.check(predicate)


# ─── donor / owner / famous checks ────────────────────────────────────────────

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


async def check_donor(bot, user_id: int) -> bool:
    redis_key = f"donor:{user_id}"
    try:
        cached = await bot.redis.get(redis_key)
        if isinstance(cached, bytes):
            cached = cached.decode()
    except Exception:
        cached = None
    if cached is not None:
        return cached == "True"
    try:
        data = _load_json("data/donors.json")
        result = str(user_id) in data.get("ids", [])
    except Exception:
        return False
    try:
        await bot.redis.set(redis_key, str(result), ex=300)
    except Exception:
        pass
    return result


async def check_famous(bot, user_id: int) -> bool:
    redis_key = f"famous:{user_id}"
    cached = await bot.redis.get(redis_key)
    if isinstance(cached, bytes):
        cached = cached.decode()
    if cached is not None:
        return cached == "True"
    try:
        data = _load_json("data/user_data.json")
        result = bool(data.get(str(user_id), {}).get("fame"))
    except Exception:
        return False
    try:
        await bot.redis.set(redis_key, str(result), ex=300)
    except Exception:
        pass
    return result


async def check_owner(bot, user_id: int) -> bool:
    return user_id in getattr(bot, "owner_ids", [])


async def register_user(bot, discord_id: int, username: str, displayname: str) -> None:
    redis_key = f"user:{discord_id}:exists"
    try:
        user_exists_in_cache = await bot.redis.get(redis_key)
    except Exception:
        user_exists_in_cache = None
    if not user_exists_in_cache:
        try:
            data = _load_json("data/user_data.json")
            user_exists = str(discord_id) in data
            if not user_exists:
                data[str(discord_id)] = {"username": username, "displayname": displayname}
                _save_json("data/user_data.json", data)
            try:
                await bot.redis.set(f"user:{discord_id}:limited", "", ex=7 * 24 * 60 * 60)
                await bot.redis.set(f"user:{discord_id}:untrusted", "", ex=60 * 24 * 60 * 60)
                await bot.redis.set(redis_key, "1", ex=600)
            except Exception:
                pass
        except Exception:
            pass


def _make_embed(bot, color, description: str, user=None):
    embed = discord.Embed(description=description, color=color)
    if user:
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    return embed, None


async def get_text(bot, text_type: str) -> str:
    if text_type == "premium":
        return f"{bot.config.get('emojis', {}).get('context', {}).get('premium', '')} This is a **premium-only** command.\n-# **Heist Premium** is **$3.99** monthly or a one-time **$8.99** purchase - </premium buy:0>"
    if text_type == "owner":
        return f"{bot.config.get('emojis', {}).get('context', {}).get('warn', '')} This command is only available to Heist's **owners**."
    return ""


def donor_only():
    async def ctx_check(ctx: Context):
        is_donor = await check_donor(ctx.bot, ctx.author.id)
        if not is_donor:
            text = await get_text(ctx.bot, "premium")
            embed, _ = await _make_embed(ctx.bot, await ctx.bot.get_color(ctx.author.id), text, ctx.author)
            await ctx.send(embed=embed)
            return False
        return True

    async def inter_check(inter: discord.Interaction):
        is_donor = await check_donor(inter.client, inter.user.id)
        if not is_donor:
            text = await get_text(inter.client, "premium")
            embed, _ = await _make_embed(inter.client, await inter.client.get_color(inter.user.id), text, inter.user)
            if inter.response.is_done():
                await inter.followup.send(embed=embed, ephemeral=True)
            else:
                await inter.response.send_message(embed=embed, ephemeral=True)
            raise commands.CheckFailure()
        return True

    def decorator(func):
        return commands.check(ctx_check)(app_commands.check(inter_check)(func))
    return decorator


def owner_only():
    async def ctx_check(ctx: Context):
        is_owner = await check_owner(ctx.bot, ctx.author.id)
        if not is_owner:
            text = await get_text(ctx.bot, "owner")
            embed, _ = await _make_embed(ctx.bot, await ctx.bot.get_color(ctx.author.id), text, ctx.author)
            await ctx.send(embed=embed)
            return False
        return True

    async def inter_check(inter: discord.Interaction):
        is_owner = await check_owner(inter.client, inter.user.id)
        if not is_owner:
            text = await get_text(inter.client, "owner")
            embed, _ = await _make_embed(inter.client, await inter.client.get_color(inter.user.id), text, inter.user)
            if inter.response.is_done():
                await inter.followup.send(embed=embed, ephemeral=True)
            else:
                await inter.response.send_message(embed=embed, ephemeral=True)
            raise commands.CheckFailure()
        return True

    def decorator(func):
        return commands.check(ctx_check)(app_commands.check(inter_check)(func))
    return decorator


async def reset_cache(user_id: int, bot) -> None:
    keys = [
        f"owner:{user_id}",
        f"blacklist:{user_id}:user",
        f"donor:{user_id}",
        f"booster:{user_id}",
        f"famous:{user_id}",
        f"premium_tokens:{user_id}",
    ]
    try:
        await bot.redis.delete(*keys)
    except Exception:
        for key in keys:
            try:
                await bot.redis.delete(key)
            except Exception:
                continue

class Colors:
    DEFAULT = 0xB8D3EA
    SUCCESS = 0xA4EB78
    ERROR = 0xFF6665
    WARNING = 0xFAA81A
    LOADING = 0x7785CC

class Emojis:
    SUCCESS = "<:approve:1477008087536635977>"
    ERROR = "<:deny:1477008083191468082>"
    WARNING = "<:warning:1477008068637360231>"
    INFO = "<:information:000000000000000000>"
    LOADING = "<a:loading:1477259541677609064>"
    FORWARD = "<:right:1477008078342721620>"
    BACKWARD = "<:left:1477008080473423963>"
    SKIPTO = "<:skipto:1477008070835044372>"
    CLOSE = "<:deny:1477008083191468082>"
    LASTFM = "<:lastfm:000000000000000000>"

class Config:    
    COLORS = Colors
    EMOJIS = Emojis