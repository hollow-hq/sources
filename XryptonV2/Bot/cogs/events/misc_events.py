from __future__ import annotations

import discord
import json
import asyncio
import aiohttp
import io
import base64
import zlib
from datetime import datetime, timezone

from core import Astroz, Cog

from utils.Tools import getIgnore

SNIPE_PATH = "data/snipe.json"
EDITSNIPE_PATH = "data/editsnipe.json"
SKULLBOARD_PATH = "data/skullboard.json"
SKULLBOARDMES_PATH = "data/skullboardmes.json"
PINGONJOIN_PATH = "data/pingonjoin.json"
JOINDM_PATH = "data/joindm.json"


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class MiscEvents(Cog):
    def __init__(self, bot: Astroz):
        self.bot = bot

    async def compress_file(self, file_data: bytes) -> str:
        compressed = zlib.compress(file_data, level=9)
        return base64.b64encode(compressed).decode("utf-8")

    async def decompress_file(self, compressed_data: str) -> bytes:
        decoded = base64.b64decode(compressed_data.encode("utf-8"))
        return zlib.decompress(decoded)

    async def download_attachment(self, url: str) -> bytes:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        ct = resp.headers.get("Content-Length")
                        if ct and int(ct) < 8 * 1024 * 1024:
                            return await resp.read()
        except Exception:
            pass
        return b""

    @Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return

        ping_config = _load_json(PINGONJOIN_PATH).get(str(member.guild.id))
        if ping_config:
            ping_channel = member.guild.get_channel(ping_config["channel_id"])
            if ping_channel:
                try:
                    message = await ping_channel.send(f"{member.mention}")
                    if ping_config.get("delete_ping"):
                        if ping_config.get("delete_after") == 0:
                            await message.delete()
                        elif ping_config.get("delete_after"):
                            await asyncio.sleep(ping_config["delete_after"])
                            await message.delete()
                except discord.HTTPException:
                    pass

        joindm_config = _load_json(JOINDM_PATH).get(str(member.guild.id))
        if joindm_config and joindm_config.get("enabled") and joindm_config.get("message"):
            try:
                template = joindm_config["message"]
                for key, val in [
                    ("{user.mention}", member.mention),
                    ("{user.name}", member.name),
                    ("{user.id}", str(member.id)),
                    ("{server.name}", member.guild.name),
                    ("{server.member_count}", str(member.guild.member_count)),
                ]:
                    template = template.replace(key, val)
                await member.send(template)
            except discord.HTTPException:
                pass

    @Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot:
            return

        if not message.content and not message.attachments and not message.stickers:
            return

        ignore_data = getIgnore(message.guild.id)
        iuser = ignore_data.get("user", [])
        ichannel = ignore_data.get("channel", [])
        buser = ignore_data.get("bypassuser", [])

        if str(message.author.id) in buser:
            return
        if str(message.author.id) in iuser or str(message.channel.id) in ichannel:
            return

        filter_data = _load_json("data/snipefilter.json").get(str(message.guild.id))
        if filter_data and message.content:
            content_lower = message.content.lower()
            if filter_data.get("invites") and ("discord.gg/" in content_lower or "discord.com/invite/" in content_lower):
                return
            if filter_data.get("links") and ("http://" in content_lower or "https://" in content_lower):
                return
            if filter_data.get("words") and any(word.lower() in content_lower for word in filter_data.get("words", [])):
                return

        sticker_data = None
        if message.stickers:
            sticker_data = json.dumps([
                {
                    "id": s.id,
                    "name": s.name,
                    "format": str(s.format),
                    "url": s.url,
                }
                for s in message.stickers
            ])

        attachment_data = None
        file_data = None

        if message.attachments:
            attachment_info = []
            files = []

            for attachment in message.attachments:
                attachment_info.append({
                    "id": attachment.id,
                    "filename": attachment.filename,
                    "size": attachment.size,
                    "url": attachment.url,
                    "content_type": attachment.content_type,
                })

                if attachment.size < 8 * 1024 * 1024:
                    try:
                        file_bytes = await self.download_attachment(attachment.url)
                        if file_bytes:
                            compressed = await self.compress_file(file_bytes)
                            files.append({
                                "filename": attachment.filename,
                                "data": compressed,
                            })
                    except Exception:
                        pass

            attachment_data = json.dumps(attachment_info)
            if files:
                file_data = json.dumps(files)

        snipe_entry = {
            "user_id": message.author.id,
            "content": message.content,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "stickers": sticker_data,
            "attachments": attachment_data,
            "files": file_data,
        }

        data = _load_json(SNIPE_PATH)
        guild_id = str(message.guild.id)
        if guild_id not in data:
            data[guild_id] = {}
        channel_id = str(message.channel.id)
        if channel_id not in data[guild_id]:
            data[guild_id][channel_id] = []

        data[guild_id][channel_id].append(snipe_entry)

        if len(data[guild_id][channel_id]) > 30:
            data[guild_id][channel_id] = data[guild_id][channel_id][-30:]

        _save_json(SNIPE_PATH, data)

    @Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild or before.author.bot or before.content == after.content:
            return

        ignore_data = getIgnore(before.guild.id)
        iuser = ignore_data.get("user", [])
        ichannel = ignore_data.get("channel", [])
        buser = ignore_data.get("bypassuser", [])

        if str(before.author.id) in buser:
            return
        if str(before.author.id) in iuser or str(before.channel.id) in ichannel:
            return

        filter_data = _load_json("data/snipefilter.json").get(str(before.guild.id))
        if filter_data:
            old_content_lower = (before.content or "").lower()
            new_content_lower = (after.content or "").lower()

            if filter_data.get("invites") and ("discord.gg/" in old_content_lower or "discord.com/invite/" in old_content_lower or "discord.gg/" in new_content_lower or "discord.com/invite/" in new_content_lower):
                return
            if filter_data.get("links") and ("http://" in old_content_lower or "https://" in old_content_lower or "http://" in new_content_lower or "https://" in new_content_lower):
                return
            if filter_data.get("words") and (
                any(word.lower() in old_content_lower for word in filter_data.get("words", []))
                or any(word.lower() in new_content_lower for word in filter_data.get("words", []))
            ):
                return

        old_stickers = None
        new_stickers = None

        if before.stickers:
            old_stickers = json.dumps([
                {
                    "id": s.id,
                    "name": s.name,
                    "format": str(s.format),
                    "url": s.url,
                }
                for s in before.stickers
            ])

        if after.stickers:
            new_stickers = json.dumps([
                {
                    "id": s.id,
                    "name": s.name,
                    "format": str(s.format),
                    "url": s.url,
                }
                for s in after.stickers
            ])

        old_attachments = None
        new_attachments = None

        if before.attachments:
            old_attachments = json.dumps([
                {
                    "id": a.id,
                    "filename": a.filename,
                    "size": a.size,
                    "url": a.url,
                    "content_type": a.content_type,
                }
                for a in before.attachments
            ])

        if after.attachments:
            new_attachments = json.dumps([
                {
                    "id": a.id,
                    "filename": a.filename,
                    "size": a.size,
                    "url": a.url,
                    "content_type": a.content_type,
                }
                for a in after.attachments
            ])

        edit_entry = {
            "user_id": before.author.id,
            "old_content": before.content,
            "new_content": after.content,
            "edited_at": datetime.now(timezone.utc).isoformat(),
            "old_stickers": old_stickers,
            "new_stickers": new_stickers,
            "old_attachments": old_attachments,
            "new_attachments": new_attachments,
        }

        data = _load_json(EDITSNIPE_PATH)
        guild_id = str(before.guild.id)
        if guild_id not in data:
            data[guild_id] = {}
        channel_id = str(before.channel.id)
        if channel_id not in data[guild_id]:
            data[guild_id][channel_id] = []

        data[guild_id][channel_id].append(edit_entry)

        if len(data[guild_id][channel_id]) > 30:
            data[guild_id][channel_id] = data[guild_id][channel_id][-30:]

        _save_json(EDITSNIPE_PATH, data)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id or payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        emoji_str = str(payload.emoji)

        rr_data = _load_json("data/reaction_role.json")
        guild_rr = rr_data.get(str(payload.guild_id), [])
        rr_match = next((r for r in guild_rr if r["channel_id"] == payload.channel_id and r["message_id"] == payload.message_id and r["emoji"] == emoji_str), None)

        if rr_match and member and not member.bot:
            role = guild.get_role(rr_match["role_id"])
            if role:
                try:
                    await member.add_roles(role, reason="Reaction role")
                except Exception:
                    pass

        skull_data = _load_json(SKULLBOARD_PATH).get(str(payload.guild_id))
        if not skull_data:
            return

        emoji_match = False
        if payload.emoji.is_unicode_emoji():
            emoji_match = ord(str(payload.emoji)) == skull_data.get("emoji_id")
        elif payload.emoji.is_custom_emoji():
            emoji_match = getattr(payload.emoji, "id", None) == skull_data.get("emoji_id")

        if not emoji_match:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        skull_channel = guild.get_channel(skull_data.get("channel_id"))
        if not skull_channel:
            return

        mes_data = _load_json(SKULLBOARDMES_PATH)
        guild_mes = mes_data.get(str(payload.guild_id), [])
        existing = next((m for m in guild_mes if m["channel_message_id"] == payload.channel_id and m["message_id"] == payload.message_id), None)

        if existing:
            skull_message = await skull_channel.fetch_message(existing["message_skullboard_id"])
            reaction_count = sum(r.count for r in message.reactions if str(r.emoji) == str(payload.emoji))
            await skull_message.edit(content=f"{payload.emoji} <#{payload.channel_id}>")
            return

        for reaction in message.reactions:
            matched = False
            if isinstance(reaction.emoji, str) and ord(str(reaction.emoji)) == skull_data.get("emoji_id"):
                matched = True
            elif hasattr(reaction.emoji, "id") and reaction.emoji.id == skull_data.get("emoji_id"):
                matched = True

            if matched and reaction.count >= (skull_data.get("count") or 3):
                embed = discord.Embed(
                    color=message.embeds[0].color if message.embeds else 0x2f3136,
                    title=message.embeds[0].title if message.embeds else None,
                    description=message.embeds[0].description if message.embeds else message.content,
                    timestamp=message.created_at,
                )

                if message.embeds and message.embeds[0].image:
                    embed.set_image(url=message.embeds[0].image.url)
                if message.embeds and message.embeds[0].footer:
                    embed.set_footer(text=message.embeds[0].footer.text, icon_url=message.embeds[0].footer.icon_url)

                embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)

                files = []
                if message.attachments:
                    first = message.attachments[0]
                    if first.url.endswith((".mp4", ".mov")):
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(first.url) as resp:
                                    if resp.status == 200:
                                        data = await resp.read()
                                        files.append(discord.File(io.BytesIO(data), filename=first.filename))
                        except Exception:
                            pass
                    else:
                        embed.set_image(url=first.url)

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Message", style=discord.ButtonStyle.link, url=message.jump_url))

                skull_msg = await skull_channel.send(
                    content=f"{reaction.emoji} <#{payload.channel_id}>",
                    embed=embed,
                    view=view,
                    files=files,
                )

                guild_mes.append({
                    "channel_skullboard_id": skull_channel.id,
                    "channel_message_id": payload.channel_id,
                    "message_skullboard_id": skull_msg.id,
                    "message_id": payload.message_id,
                })
                mes_data[str(payload.guild_id)] = guild_mes
                _save_json(SKULLBOARDMES_PATH, mes_data)
                break

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        emoji_str = str(payload.emoji)

        if member and not member.bot and payload.user_id != self.bot.user.id:
            rr_data = _load_json("data/reaction_role.json")
            guild_rr = rr_data.get(str(payload.guild_id), [])
            rr_match = next((r for r in guild_rr if r["channel_id"] == payload.channel_id and r["message_id"] == payload.message_id and r["emoji"] == emoji_str), None)

            if rr_match:
                role = guild.get_role(rr_match["role_id"])
                if role:
                    try:
                        await member.remove_roles(role, reason="Reaction role removed")
                    except Exception:
                        pass

        skull_data = _load_json(SKULLBOARD_PATH).get(str(payload.guild_id))
        if not skull_data:
            return

        emoji_match = False
        if payload.emoji.is_unicode_emoji():
            emoji_match = ord(str(payload.emoji)) == skull_data.get("emoji_id")
        elif payload.emoji.is_custom_emoji():
            emoji_match = getattr(payload.emoji, "id", None) == skull_data.get("emoji_id")

        if not emoji_match:
            return

        mes_data = _load_json(SKULLBOARDMES_PATH)
        guild_mes = mes_data.get(str(payload.guild_id), [])
        existing = next((m for m in guild_mes if m["channel_message_id"] == payload.channel_id and m["message_id"] == payload.message_id), None)

        if existing:
            channel = guild.get_channel(payload.channel_id)
            if not channel:
                return

            try:
                message = await channel.fetch_message(payload.message_id)
            except Exception:
                return

            skull_channel = guild.get_channel(existing["channel_skullboard_id"])
            if not skull_channel:
                return

            try:
                skull_message = await skull_channel.fetch_message(existing["message_skullboard_id"])
                for reaction in message.reactions:
                    matched = False
                    if isinstance(reaction.emoji, str) and ord(str(reaction.emoji)) == skull_data.get("emoji_id"):
                        matched = True
                    elif hasattr(reaction.emoji, "id") and reaction.emoji.id == skull_data.get("emoji_id"):
                        matched = True

                    if matched:
                        await skull_message.edit(content=f"{reaction.emoji} <#{payload.channel_id}>")
                        break
            except Exception:
                pass


async def setup(bot: Astroz):
    await bot.add_cog(MiscEvents(bot))
