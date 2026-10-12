from __future__ import annotations

import discord
import json
import io
import base64
import zlib
from datetime import datetime, timezone
from typing import Union, Optional

from discord.ext import commands
from discord import TextChannel, Embed, Member, Message, PartialEmoji
from discord.ui import Button, ActionRow, View

from core import Cog, Astroz, Context
from utils.Tools import blacklist_check, ignore_check
from utils.config import getConfig

COLOR = 0x2f3136

SNIPE_PATH = "data/snipe.json"
EDITSNIPE_PATH = "data/editsnipe.json"
SNIPEFILTER_PATH = "data/snipefilter.json"
BOOSTER_ROLE_PATH = "data/booster_role.json"
PINGONJOIN_PATH = "data/pingonjoin.json"
REACTION_ROLE_PATH = "data/reaction_role.json"
SKULLBOARD_PATH = "data/skullboard.json"
SKULLBOARDMES_PATH = "data/skullboardmes.json"
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


class Misc(Cog, name="MiscCommands"):
    def __init__(self, bot):
        self.bot = bot

    async def decompress_file(self, compressed_data: str) -> bytes:
        decoded = base64.b64decode(compressed_data.encode("utf-8"))
        return zlib.decompress(decoded)

    def humanize_time(self, seconds):
        if seconds < 60:
            return f"{seconds} seconds ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"

    def embed_to_code(self, embed: Union[dict, Message, Embed], message: Optional[str] = None, escaped: Optional[bool] = True) -> str:
        code = "{embed}"
        msg = None
        if isinstance(embed, dict):
            message = embed.pop("message", embed.pop("content", message))
            embed = Embed.from_dict(embed)
        elif isinstance(embed, Message):
            msg = embed
            message = message or str(embed.content)
            embed = embed.embeds[0]
        if msg:
            for component in msg.components:
                children = []
                if isinstance(component, (Button, ActionRow)):
                    children = component.children if isinstance(component, ActionRow) else [component]
                for child in children:
                    if isinstance(child, (Button, discord.ui.Button)) and child.url:
                        substeps = "$v{button: "
                        if child.label:
                            substeps += f"{child.label} && "
                        if child.emoji:
                            substeps += f"{str(child.emoji)} && "
                        substeps += f"{child.url}}}"
                        code += substeps
        if message:
            code += f"$v{{content: {message}}}"
        if embed.title:
            code += f"$v{{title: {embed.title}}}"
        if embed.description:
            code += f"$v{{description: {embed.description}}}"
        if embed.timestamp:
            code += "$v{timestamp: true}"
        if embed.url:
            code += f"$v{{url: {embed.url}}}"
        if fields := embed.fields:
            for field in fields:
                inline = " && inline" if field.inline else ""
                code += f"$v{{field: {field.name} && {field.value}{inline}}}"
        if embed.footer:
            substeps = ""
            text = embed.footer.text or ""
            icon_url = embed.footer.icon_url or ""
            substeps += f"footer: {text}"
            if icon_url:
                substeps += f" && {icon_url}"
            code += f"$v{{{substeps}}}"
        if embed.author:
            substeps = ""
            icon_url = embed.author.icon_url or ""
            url = embed.author.url or None
            substeps += f"author: {embed.author.name}"
            if url:
                substeps += f" && {url}"
            if icon_url:
                substeps += f" && {icon_url}"
            code += "$v{" + substeps + "}"
        if image_url := embed.image.url:
            code += f"$v{{image: {image_url}}}"
        if thumbnail_url := embed.thumbnail.url:
            code += f"$v{{thumbnail: {thumbnail_url}}}"
        if color := embed.color:
            code += f"$v{{color: #{str(color)}}}".replace("##", "#")
        if escaped:
            code = code.replace("```", "`\u200b`\u200b`")
        return code

    @commands.group(invoke_without_command=True, name="snipefilter")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def snipefilter(self, ctx: Context):
        data = _load_json(SNIPEFILTER_PATH).get(str(ctx.guild.id))
        if not data:
            return await ctx.reply(embed=Embed(description="No snipe filters configured", color=COLOR))

        filters = []
        if data.get("invites"):
            filters.append("Invites")
        if data.get("links"):
            filters.append("Links")
        if data.get("words"):
            filters.append(f"Words: {', '.join(data['words'])}")

        if not filters:
            return await ctx.reply(embed=Embed(description="No snipe filters enabled", color=COLOR))

        embed = Embed(color=COLOR, title="Snipe Filters", description="\n".join(f"• {f}" for f in filters))
        await ctx.send(embed=embed)

    @snipefilter.command(name="add")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def snipefilter_add(self, ctx: Context, filter_type: str, *, value: str = None):
        filter_type = filter_type.lower()
        if filter_type not in ["invites", "links", "words"]:
            return await ctx.reply(embed=Embed(description="Invalid filter type. Use: invites, links, or words", color=COLOR))

        if filter_type == "words" and not value:
            return await ctx.reply(embed=Embed(description="Word filter requires a word to filter", color=COLOR))

        data = _load_json(SNIPEFILTER_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            data[guild_id] = {"invites": False, "links": False, "words": []}

        if filter_type in ["invites", "links"]:
            data[guild_id][filter_type] = True
        else:
            words = data[guild_id].get("words", [])
            if value.lower() in [w.lower() for w in words]:
                return await ctx.reply(embed=Embed(description="Word already in filter", color=COLOR))
            words.append(value.lower())
            data[guild_id]["words"] = words

        _save_json(SNIPEFILTER_PATH, data)
        await ctx.reply(embed=Embed(description=f"Added {filter_type} filter", color=COLOR))

    @snipefilter.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def snipefilter_remove(self, ctx: Context, filter_type: str, *, value: str = None):
        filter_type = filter_type.lower()
        if filter_type not in ["invites", "links", "words"]:
            return await ctx.reply(embed=Embed(description="Invalid filter type. Use: invites, links, or words", color=COLOR))

        data = _load_json(SNIPEFILTER_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            return await ctx.reply(embed=Embed(description="No snipe filters configured", color=COLOR))

        if filter_type in ["invites", "links"]:
            if not data[guild_id][filter_type]:
                return await ctx.reply(embed=Embed(description=f"{filter_type.title()} filter is not enabled", color=COLOR))
            data[guild_id][filter_type] = False
        else:
            if not value:
                return await ctx.reply(embed=Embed(description="Word filter requires a word to remove", color=COLOR))
            words = data[guild_id].get("words", [])
            word_lower = value.lower()
            if word_lower not in [w.lower() for w in words]:
                return await ctx.reply(embed=Embed(description="Word not found in filter", color=COLOR))
            data[guild_id]["words"] = [w for w in words if w.lower() != word_lower]

        _save_json(SNIPEFILTER_PATH, data)
        await ctx.reply(embed=Embed(description=f"Removed {filter_type} filter", color=COLOR))

    @commands.group(invoke_without_command=True, name="boosterrole", aliases=["boosterroles", "br"])
    @blacklist_check()
    @ignore_check()
    async def boosterrole(self, ctx: Context):
        await ctx.send_help(ctx.command)

    async def is_booster(self, ctx: Context):
        if not ctx.author.premium_since:
            await ctx.reply(embed=Embed(description="You must be a server booster to use this command", color=COLOR))
            return False
        return True

    def _get_booster_role(self, guild_id, user_id):
        data = _load_json(BOOSTER_ROLE_PATH)
        guild_id = str(guild_id)
        if guild_id not in data:
            return None
        for role in data[guild_id]:
            if role["user_id"] == user_id:
                return role
        return None

    def _update_booster_role(self, guild_id, user_id, **kwargs):
        data = _load_json(BOOSTER_ROLE_PATH)
        guild_id = str(guild_id)
        if guild_id not in data:
            data[guild_id] = []
        for role in data[guild_id]:
            if role["user_id"] == user_id:
                role.update(kwargs)
                _save_json(BOOSTER_ROLE_PATH, data)
                return
        role = {"user_id": user_id}
        role.update(kwargs)
        data[guild_id].append(role)
        _save_json(BOOSTER_ROLE_PATH, data)

    def _remove_booster_role(self, guild_id, user_id):
        data = _load_json(BOOSTER_ROLE_PATH)
        guild_id = str(guild_id)
        if guild_id in data:
            data[guild_id] = [r for r in data[guild_id] if r["user_id"] != user_id]
            _save_json(BOOSTER_ROLE_PATH, data)

    @boosterrole.command(name="create", aliases=["c"])
    @blacklist_check()
    @ignore_check()
    async def boosterrole_create(self, ctx: Context, color: str, *, name: str):
        if not await self.is_booster(ctx):
            return

        if self._get_booster_role(ctx.guild.id, ctx.author.id):
            return await ctx.reply(embed=Embed(description="You already have a booster role.", color=COLOR))

        color_map = {
            "red": discord.Color.red(),
            "blue": discord.Color.blue(),
            "green": discord.Color.green(),
            "yellow": discord.Color.yellow(),
            "orange": discord.Color.orange(),
            "purple": discord.Color.purple(),
            "teal": discord.Color.teal(),
            "magenta": discord.Color.magenta(),
            "gold": discord.Color.gold(),
            "dark_red": discord.Color.dark_red(),
            "dark_blue": discord.Color.dark_blue(),
            "dark_green": discord.Color.dark_green(),
            "dark_purple": discord.Color.dark_purple(),
            "light_gray": discord.Color.light_gray(),
            "dark_gray": discord.Color.dark_gray(),
            "blurple": discord.Color.blurple(),
        }

        color = color.lower()
        if color.startswith("#"):
            try:
                color_value = discord.Color(int(color.replace("#", ""), 16))
            except Exception:
                color_value = discord.Color.default()
        else:
            color_value = color_map.get(color, discord.Color.default())

        role = await ctx.guild.create_role(name=name, color=color_value, reason="Booster role creation")

        booster_role = discord.utils.find(lambda r: "Server Booster" in r.name, ctx.guild.roles)
        if booster_role:
            try:
                await role.edit(position=booster_role.position + 1)
            except discord.Forbidden:
                pass

        self._update_booster_role(ctx.guild.id, ctx.author.id, role_id=role.id, shared=False, multi_boost_enabled=False)
        await ctx.author.add_roles(role, reason="Booster role created")
        await ctx.reply(embed=Embed(description=f"successfully assigned you {role.mention} as your booster role", color=COLOR))

    @boosterrole.command(name="hoist", aliases=["display"])
    @blacklist_check()
    @ignore_check()
    async def boosterrole_hoist(self, ctx: Context):
        if not await self.is_booster(ctx):
            return

        record = self._get_booster_role(ctx.guild.id, ctx.author.id)
        if not record:
            return await ctx.reply(embed=Embed(description="You do not have a booster role.", color=COLOR))

        role = ctx.guild.get_role(record["role_id"])
        if not role:
            return await ctx.reply(embed=Embed(description="Your booster role has been **DELETED**.", color=COLOR))

        new_state = not role.hoist
        await role.edit(hoist=new_state, reason=f"Booster role hoist toggled by {ctx.author}.")
        state_text = "now **displayed separately**" if new_state else "no longer displayed separately"
        await ctx.reply(embed=Embed(description=f"{role.mention} is {state_text}.", color=COLOR))

    @boosterrole.command(name="color")
    @blacklist_check()
    @ignore_check()
    async def boosterrole_color(self, ctx: Context, *, color: str):
        if not await self.is_booster(ctx):
            return

        record = self._get_booster_role(ctx.guild.id, ctx.author.id)
        if not record:
            return await ctx.reply(embed=Embed(description="You do not have a booster role.", color=COLOR))

        role = ctx.guild.get_role(record["role_id"])
        if not role:
            return await ctx.reply(embed=Embed(description="Your booster role has been **DELETED**.", color=COLOR))

        color_map = {
            "red": discord.Color.red(),
            "blue": discord.Color.blue(),
            "green": discord.Color.green(),
            "yellow": discord.Color.yellow(),
            "orange": discord.Color.orange(),
            "purple": discord.Color.purple(),
            "teal": discord.Color.teal(),
            "magenta": discord.Color.magenta(),
            "gold": discord.Color.gold(),
            "dark_red": discord.Color.dark_red(),
            "dark_blue": discord.Color.dark_blue(),
            "dark_green": discord.Color.dark_green(),
            "dark_purple": discord.Color.dark_purple(),
            "light_gray": discord.Color.light_gray(),
            "dark_gray": discord.Color.dark_gray(),
            "blurple": discord.Color.blurple(),
        }

        color = color.lower().strip()
        if color.startswith("#"):
            try:
                color_value = discord.Color(int(color.replace("#", ""), 16))
            except ValueError:
                return await ctx.reply(embed=Embed(description="Invalid hex color format.", color=COLOR))
        else:
            color_value = color_map.get(color)
            if not color_value:
                return await ctx.reply(embed=Embed(description="Invalid color name or format", color=COLOR))

        await role.edit(color=color_value, reason=f"Booster role recolored by {ctx.author}")
        await ctx.reply(embed=Embed(description=f"Successfully re-colored your role to {str(color_value)}", color=COLOR))

    @boosterrole.command(name="share")
    @blacklist_check()
    @ignore_check()
    async def boosterrole_share(self, ctx: Context, *, member: discord.Member):
        if not await self.is_booster(ctx):
            return

        record = self._get_booster_role(ctx.guild.id, ctx.author.id)
        if not record:
            return await ctx.reply(embed=Embed(description="You do not have a booster role.", color=COLOR))

        role = ctx.guild.get_role(record["role_id"])
        if not role:
            return await ctx.reply(embed=Embed(description="Your booster role has been **DELETED**.", color=COLOR))

        if member.id == ctx.author.id:
            return await ctx.reply(embed=Embed(description="You cannot share your booster role to yourself.", color=COLOR))

        await member.add_roles(role, reason="Booster Role Shared")
        self._update_booster_role(ctx.guild.id, ctx.author.id, shared=True)
        await ctx.reply(embed=Embed(description=f"successfully shared your booster role with {member.mention}", color=COLOR))

    @boosterrole.command(name="cleanup")
    @commands.has_permissions(manage_roles=True)
    @blacklist_check()
    @ignore_check()
    async def boosterrole_cleanup(self, ctx: Context):
        data = _load_json(BOOSTER_ROLE_PATH)
        guild_id = str(ctx.guild.id)
        roles = data.get(guild_id, [])
        if not roles:
            return await ctx.reply(embed=Embed(description="there are no booster roles", color=COLOR))

        delete = []
        cleanable_roles = []

        for record in roles:
            role = ctx.guild.get_role(record["role_id"])
            if not role:
                delete.append(record["role_id"])
                continue

            members = [m for m in role.members if m.premium_since]
            if len(members) == 0:
                cleanable_roles.append(role)
                delete.append(record["role_id"])

        if not cleanable_roles:
            return await ctx.reply(embed=Embed(description="there are no unused booster roles", color=COLOR))

        for role in cleanable_roles:
            await role.delete(reason="Booster Role Cleanup")

        if delete:
            data[guild_id] = [r for r in data[guild_id] if r["role_id"] not in delete]
            _save_json(BOOSTER_ROLE_PATH, data)

        await ctx.reply(embed=Embed(description=f"successfully cleaned up `{len(cleanable_roles)}` **booster roles**", color=COLOR))

    @boosterrole.command(name="name")
    @blacklist_check()
    @ignore_check()
    async def boosterrole_name(self, ctx: Context, *, name: str):
        if not await self.is_booster(ctx):
            return

        record = self._get_booster_role(ctx.guild.id, ctx.author.id)
        if not record:
            return await ctx.reply(embed=Embed(description="You do not have a booster role.", color=COLOR))

        role = ctx.guild.get_role(record["role_id"])
        if not role:
            return await ctx.reply(embed=Embed(description="your booster role has been **DELETED**", color=COLOR))

        await role.edit(name=name)
        await ctx.reply(embed=Embed(description=f"successfully renamed your booster role to **{name}**", color=COLOR))

    @boosterrole.command(name="delete", aliases=["remove"])
    @blacklist_check()
    @ignore_check()
    async def boosterrole_delete(self, ctx: Context):
        if not await self.is_booster(ctx):
            return

        record = self._get_booster_role(ctx.guild.id, ctx.author.id)
        if not record:
            return await ctx.reply(embed=Embed(description="You do not have a booster role.", color=COLOR))

        role = ctx.guild.get_role(record["role_id"])
        if role:
            await role.delete(reason="Booster role deleted by owner")

        self._remove_booster_role(ctx.guild.id, ctx.author.id)
        await ctx.reply(embed=Embed(description="successfully deleted your booster role", color=COLOR))

    @commands.group(invoke_without_command=True, name="pingonjoin")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def pingonjoin(self, ctx: Context):
        config = _load_json(PINGONJOIN_PATH).get(str(ctx.guild.id))
        if not config:
            return await ctx.reply(embed=Embed(description="Pingonjoin is not configured", color=COLOR))

        channel = ctx.guild.get_channel(config["channel_id"])
        delete_info = "No" if not config["delete_ping"] else ("Instant" if config["delete_after"] == 0 else f"{config['delete_after']}s")

        embed = Embed(color=COLOR, title="Pingonjoin Configuration")
        embed.add_field(name="Channel", value=channel.mention if channel else "Unknown")
        embed.add_field(name="Delete Ping", value=delete_info)
        await ctx.send(embed=embed)

    @pingonjoin.command(name="set")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def pingonjoin_set(self, ctx: Context, channel: TextChannel, delete: bool = False, delete_after: str = None):
        delete_seconds = None

        if delete and delete_after:
            if delete_after.lower() == "instant":
                delete_seconds = 0
            else:
                try:
                    if delete_after.endswith("s"):
                        delete_seconds = int(delete_after[:-1])
                    elif delete_after.endswith("m"):
                        delete_seconds = int(delete_after[:-1]) * 60
                    elif delete_after.endswith("h"):
                        delete_seconds = int(delete_after[:-1]) * 3600
                    else:
                        delete_seconds = int(delete_after)
                except ValueError:
                    return await ctx.reply(embed=Embed(description="Invalid time format. Use: instant, 5s, 10m, 1h, or just a number", color=COLOR))
        elif delete and not delete_after:
            return await ctx.reply(embed=Embed(description="Delete time is required when delete is enabled", color=COLOR))

        data = _load_json(PINGONJOIN_PATH)
        data[str(ctx.guild.id)] = {"channel_id": channel.id, "delete_ping": delete, "delete_after": delete_seconds}
        _save_json(PINGONJOIN_PATH, data)

        delete_info = "disabled" if not delete else ("instant" if delete_seconds == 0 else f"after {delete_after}")
        await ctx.reply(embed=Embed(description=f"Pingonjoin set to {channel.mention} with deletion {delete_info}", color=COLOR))

    @pingonjoin.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def pingonjoin_remove(self, ctx: Context):
        data = _load_json(PINGONJOIN_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            return await ctx.reply(embed=Embed(description="Pingonjoin is not configured", color=COLOR))
        del data[guild_id]
        _save_json(PINGONJOIN_PATH, data)
        await ctx.reply(embed=Embed(description="Pingonjoin configuration removed", color=COLOR))

    @commands.command(
        name="embedcode",
        description="get the code of an already existing embed",
    )
    @commands.has_permissions(manage_messages=True)
    @blacklist_check()
    @ignore_check()
    async def embedcode(self, ctx: Context, message: Message = None):
        target_message = message or ctx.message.reference.resolved if ctx.message.reference else None
        if not target_message:
            return await ctx.reply(embed=Embed(description="Reply to a message or provide a message link", color=COLOR))
        code = self.embed_to_code(target_message)
        await ctx.reply(embed=Embed(description=f"**Successfully copied the embed code**\n```{code}```", color=COLOR))

    @commands.group(invoke_without_command=True, aliases=["rr"])
    @blacklist_check()
    @ignore_check()
    async def reactionrole(self, ctx: Context):
        await ctx.send_help(ctx.command)

    @reactionrole.command(name="add")
    @commands.has_permissions(manage_roles=True)
    @blacklist_check()
    @ignore_check()
    async def rr_add(self, ctx: Context, message_id: int, channel: TextChannel, emoji: Union[discord.Emoji, str], *, role: Union[discord.Role, str]):
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.reply(embed=Embed(description="Message not found", color=COLOR))

        if isinstance(role, str):
            role = discord.utils.get(ctx.guild.roles, name=role)
            if not role:
                return await ctx.reply(embed=Embed(description="Role not found", color=COLOR))

        emoji_str = str(emoji)

        data = _load_json(REACTION_ROLE_PATH)
        guild_data = data.get(str(ctx.guild.id), [])
        if any(r["message_id"] == message.id and r["channel_id"] == channel.id and r["emoji"] == emoji_str for r in guild_data):
            return await ctx.reply(embed=Embed(description="A reaction role with this emoji already exists on this message", color=COLOR))

        try:
            await message.add_reaction(emoji)
            guild_data.append({
                "channel_id": channel.id,
                "message_id": message.id,
                "role_id": role.id,
                "emoji": emoji_str,
            })
            data[str(ctx.guild.id)] = guild_data
            _save_json(REACTION_ROLE_PATH, data)
            await ctx.reply(embed=Embed(description=f"Added reaction role {emoji} for {role.mention}", color=COLOR))
        except discord.Forbidden:
            await ctx.reply(embed=Embed(description="I don't have permission to add reactions or manage this role", color=COLOR))
        except Exception:
            await ctx.reply(embed=Embed(description="Unable to add reaction role", color=COLOR))

    @reactionrole.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    @blacklist_check()
    @ignore_check()
    async def rr_remove(self, ctx: Context, message_id: int, channel: TextChannel, emoji: Union[discord.Emoji, str]):
        emoji_str = str(emoji)

        data = _load_json(REACTION_ROLE_PATH)
        guild_data = data.get(str(ctx.guild.id), [])
        if not any(r["message_id"] == message_id and r["channel_id"] == channel.id and r["emoji"] == emoji_str for r in guild_data):
            return await ctx.reply(embed=Embed(description="No reaction role found with the given arguments", color=COLOR))

        data[str(ctx.guild.id)] = [r for r in guild_data if not (r["message_id"] == message_id and r["channel_id"] == channel.id and r["emoji"] == emoji_str)]
        _save_json(REACTION_ROLE_PATH, data)
        await ctx.reply(embed=Embed(description="Removed reaction role", color=COLOR))

    @reactionrole.command(name="removeall")
    @commands.has_permissions(manage_roles=True)
    @blacklist_check()
    @ignore_check()
    async def rr_removeall(self, ctx: Context, channel: TextChannel = None):
        data = _load_json(REACTION_ROLE_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            return await ctx.reply(embed=Embed(description="No reaction roles found in this server", color=COLOR))

        if channel:
            old_len = len(data[guild_id])
            data[guild_id] = [r for r in data[guild_id] if r["channel_id"] != channel.id]
            new_len = len(data[guild_id])
            if old_len == new_len:
                return await ctx.reply(embed=Embed(description=f"No reaction roles found in {channel.mention}", color=COLOR))
            _save_json(REACTION_ROLE_PATH, data)
            await ctx.reply(embed=Embed(description=f"Removed all reaction roles from {channel.mention}", color=COLOR))
        else:
            count = len(data[guild_id])
            del data[guild_id]
            _save_json(REACTION_ROLE_PATH, data)
            await ctx.reply(embed=Embed(description="Removed all reaction roles from this server", color=COLOR))

    @reactionrole.command(name="list")
    async def rr_list(self, ctx: Context):
        results = _load_json(REACTION_ROLE_PATH).get(str(ctx.guild.id), [])
        if not results:
            return await ctx.reply(embed=Embed(description="No reaction roles found", color=COLOR))

        entries = []
        for result in results:
            channel = ctx.guild.get_channel(result["channel_id"])
            role = ctx.guild.get_role(result["role_id"])

            if not channel or not role:
                continue

            try:
                message = await channel.fetch_message(result["message_id"])
                message_link = message.jump_url
            except Exception:
                message_link = "Message not found"

            entries.append(f"{result['emoji']} - {role.mention} [message link]({message_link})")

        if not entries:
            return await ctx.reply(embed=Embed(description="No valid reaction roles found", color=COLOR))

        pages = [entries[i:i+10] for i in range(0, len(entries), 10)]
        embeds = []
        for i, page in enumerate(pages):
            embed = Embed(
                color=COLOR,
                title=f"Reaction Roles ({len(entries)})",
                description="\n".join(f"`{j+1+(i*10)}` {entry}" for j, entry in enumerate(page))
            )
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            from utils.paginator import Paginator
            from utils.paginators import DescriptionEmbedPaginator
            paginator = Paginator(source=DescriptionEmbedPaginator(entries=entries, title=f"Reaction Roles ({len(entries)})", description="", per_page=10), ctx=ctx)
            await paginator.paginate()

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def skull(self, ctx: Context):
        await ctx.send_help(ctx.command)

    @skull.command(name="count", aliases=["amount"])
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def skull_count(self, ctx: Context, count: int):
        if count < 1:
            return await ctx.reply(embed=Embed(description="Count can't be less than 1", color=COLOR))

        data = _load_json(SKULLBOARD_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            data[guild_id] = {}
        data[guild_id]["count"] = count
        _save_json(SKULLBOARD_PATH, data)
        await ctx.reply(embed=Embed(description=f"Skull count set to **{count}**", color=COLOR))

    @skull.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def skull_channel(self, ctx: Context, *, channel: TextChannel):
        data = _load_json(SKULLBOARD_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            data[guild_id] = {}
        data[guild_id]["channel_id"] = channel.id
        _save_json(SKULLBOARD_PATH, data)
        await ctx.reply(embed=Embed(description=f"Skullboard channel set to {channel.mention}", color=COLOR))

    @skull.command(name="remove", aliases=["disable"])
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def skull_remove(self, ctx: Context):
        data = _load_json(SKULLBOARD_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            return await ctx.reply(embed=Embed(description="Skullboard is not enabled", color=COLOR))

        del data[guild_id]
        _save_json(SKULLBOARD_PATH, data)

        mes_data = _load_json(SKULLBOARDMES_PATH)
        if guild_id in mes_data:
            del mes_data[guild_id]
            _save_json(SKULLBOARDMES_PATH, mes_data)

        await ctx.reply(embed=Embed(description="Disabled skullboard successfully", color=COLOR))

    @skull.command(name="stats", aliases=["settings", "status"])
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def skull_stats(self, ctx: Context):
        data = _load_json(SKULLBOARD_PATH).get(str(ctx.guild.id))
        if not data:
            return await ctx.reply(embed=Embed(description="Skullboard is not enabled", color=COLOR))

        embed = Embed(color=COLOR, title="Skullboard Settings")

        if data.get("channel_id"):
            channel = ctx.guild.get_channel(data["channel_id"])
            embed.add_field(name="Channel", value=channel.mention if channel else "Unknown")

        if data.get("count"):
            embed.add_field(name="Amount", value=data["count"])

        if data.get("emoji_text"):
            embed.add_field(name="Emoji", value=data["emoji_text"])

        await ctx.send(embed=embed)

    @skull.command(name="emoji")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def skull_emoji(self, ctx: Context, emoji: Union[discord.PartialEmoji, str]):
        emoji_id = emoji.id if isinstance(emoji, discord.PartialEmoji) else ord(str(emoji))

        data = _load_json(SKULLBOARD_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            data[guild_id] = {}
        data[guild_id]["emoji_id"] = emoji_id
        data[guild_id]["emoji_text"] = str(emoji)
        _save_json(SKULLBOARD_PATH, data)
        await ctx.reply(embed=Embed(description=f"Skullboard emoji set to {emoji}", color=COLOR))

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def joindm(self, ctx: Context):
        config = _load_json(JOINDM_PATH).get(str(ctx.guild.id))
        if not config:
            return await ctx.reply(embed=Embed(description="Joindm is not configured", color=COLOR))

        status = "Enabled" if config.get("enabled") else "Disabled"
        embed = Embed(color=COLOR, title="Joindm Configuration")
        embed.add_field(name="Status", value=status)
        embed.add_field(name="Message", value=config.get("message") or "None")
        await ctx.send(embed=embed)

    @joindm.command(name="set")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def joindm_set(self, ctx: Context, *, message: str):
        data = _load_json(JOINDM_PATH)
        data[str(ctx.guild.id)] = {"message": message, "enabled": True}
        _save_json(JOINDM_PATH, data)
        await ctx.reply(embed=Embed(description="Joindm message set and enabled", color=COLOR))

    @joindm.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def joindm_disable(self, ctx: Context):
        data = _load_json(JOINDM_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            return await ctx.reply(embed=Embed(description="Joindm is not configured", color=COLOR))
        data[guild_id]["enabled"] = False
        _save_json(JOINDM_PATH, data)
        await ctx.reply(embed=Embed(description="Joindm disabled", color=COLOR))

    @joindm.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def joindm_enable(self, ctx: Context):
        data = _load_json(JOINDM_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data or not data[guild_id].get("message"):
            return await ctx.reply(embed=Embed(description="Set a joindm message first", color=COLOR))
        data[guild_id]["enabled"] = True
        _save_json(JOINDM_PATH, data)
        await ctx.reply(embed=Embed(description="Joindm enabled", color=COLOR))

    @joindm.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    @blacklist_check()
    @ignore_check()
    async def joindm_remove(self, ctx: Context):
        data = _load_json(JOINDM_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            return await ctx.reply(embed=Embed(description="Joindm is not configured", color=COLOR))
        del data[guild_id]
        _save_json(JOINDM_PATH, data)
        await ctx.reply(embed=Embed(description="Joindm configuration removed", color=COLOR))

    @commands.command(aliases=["esnipe", "es"])
    @commands.has_permissions(manage_messages=True)
    @blacklist_check()
    @ignore_check()
    async def editsnipe(self, ctx: Context, number: int = 1):
        edits = _load_json(EDITSNIPE_PATH).get(str(ctx.guild.id), {}).get(str(ctx.channel.id), [])
        if not edits:
            return await ctx.reply(embed=Embed(description="No edited messages found", color=COLOR))

        if number < 1 or number > len(edits):
            return await ctx.reply(embed=Embed(description=f"Invalid edit number. Available: 1-{len(edits)}", color=COLOR))

        edit = edits[number - 1]
        user = self.bot.get_user(edit["user_id"])

        edited_at = datetime.fromisoformat(edit["edited_at"].replace("Z", "+00:00"))
        seconds_ago = int((datetime.now(timezone.utc) - edited_at).total_seconds())

        old_content = edit["old_content"] or "*No content*"
        new_content = edit["new_content"] or "*No content*"

        embed = Embed(color=COLOR, description=f"**Before:** {old_content}\n**After:** {new_content}")

        if user:
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

        if edit.get("old_stickers") or edit.get("new_stickers"):
            old_stickers = ""
            new_stickers = ""

            if edit.get("old_stickers"):
                try:
                    stickers = json.loads(edit["old_stickers"])
                    old_stickers = ", ".join([f":{s['name']}:" for s in stickers])
                except Exception:
                    pass

            if edit.get("new_stickers"):
                try:
                    stickers = json.loads(edit["new_stickers"])
                    new_stickers = ", ".join([f":{s['name']}:" for s in stickers])
                except Exception:
                    pass

            if old_stickers or new_stickers:
                embed.add_field(
                    name="Stickers",
                    value=f"**Before:** {old_stickers or '*None*'}\n**After:** {new_stickers or '*None*'}",
                    inline=False,
                )

        if edit.get("old_attachments") or edit.get("new_attachments"):
            old_attachments = ""
            new_attachments = ""

            if edit.get("old_attachments"):
                try:
                    attachments = json.loads(edit["old_attachments"])
                    old_attachments = "\n".join([f"[{a['filename']}]({a['url']})" for a in attachments])
                except Exception:
                    pass

            if edit.get("new_attachments"):
                try:
                    attachments = json.loads(edit["new_attachments"])
                    new_attachments = "\n".join([f"[{a['filename']}]({a['url']})" for a in attachments])
                except Exception:
                    pass

            if old_attachments or new_attachments:
                embed.add_field(
                    name="Attachments",
                    value=f"**Before:**\n{old_attachments or '*None*'}\n**After:**\n{new_attachments or '*None*'}",
                    inline=False,
                )

        embed.set_footer(text=f"{number}/{len(edits)} • Edited {self.humanize_time(seconds_ago)}")
        await ctx.send(embed=embed)

    @commands.command(aliases=["cs"])
    @commands.has_permissions(manage_messages=True)
    @blacklist_check()
    @ignore_check()
    async def clearsnipe(self, ctx: Context):
        data = _load_json(SNIPE_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data or str(ctx.channel.id) not in data[guild_id]:
            return await ctx.reply(embed=Embed(description="No snipes found in this channel", color=COLOR))
        data[guild_id][str(ctx.channel.id)] = []
        _save_json(SNIPE_PATH, data)
        await ctx.reply(embed=Embed(description="Cleared all snipes in this channel", color=COLOR))

    @commands.command(aliases=["ces"])
    @commands.has_permissions(manage_messages=True)
    @blacklist_check()
    @ignore_check()
    async def cleareditsnipe(self, ctx: Context):
        data = _load_json(EDITSNIPE_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in data or str(ctx.channel.id) not in data[guild_id]:
            return await ctx.reply(embed=Embed(description="No editsnipes found in this channel", color=COLOR))
        data[guild_id][str(ctx.channel.id)] = []
        _save_json(EDITSNIPE_PATH, data)
        await ctx.reply(embed=Embed(description="Cleared all editsnipes in this channel", color=COLOR))


async def setup(bot):
    await bot.add_cog(Misc(bot))
