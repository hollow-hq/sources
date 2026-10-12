from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from utils.Tools import blacklist_check, ignore_check
from utils.config import get_bot_name
from utils.constants import GreenTick2, error


EMBEDS_FILE = "data/embeds.json"


class EmbedScriptError(ValueError):
    pass


class EmbedScripting(commands.Cog):
    """Classic embed scripting compiler."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.color = 0x5865F2

    async def cog_load(self):
        await self._ensure_file()

    async def _read_data(self) -> dict:
        def load() -> dict:
            if not os.path.exists(EMBEDS_FILE):
                return {}
            with open(EMBEDS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)

        return await asyncio.to_thread(load)

    async def _write_data(self, data: dict):
        def save() -> None:
            temp_path = f"{EMBEDS_FILE}.tmp"
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            os.replace(temp_path, EMBEDS_FILE)

        await asyncio.to_thread(save)

    async def _ensure_file(self):
        data = await self._read_data()
        if not data:
            await self._write_data({})

    async def _get_guild_scripts(self, guild_id: int) -> dict:
        data = await self._read_data()
        guild_scripts = data.setdefault(str(guild_id), {})
        if not isinstance(guild_scripts, dict):
            guild_scripts = {}
            data[str(guild_id)] = guild_scripts
            await self._write_data(data)
        return guild_scripts

    def _validate_name(self, name: str) -> str:
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", name):
            raise EmbedScriptError("Script names may only contain letters, numbers, underscores, and hyphens.")
        return name

    def _split_top_level(self, text: str, delimiter: str = "&&") -> list[str]:
        parts: list[str] = []
        start = 0
        index = 0
        paren_depth = 0

        while index < len(text):
            char = text[index]
            if char == "\\" and index + 1 < len(text):
                index += 2
                continue
            if char == "(":
                paren_depth += 1
            elif char == ")" and paren_depth:
                paren_depth -= 1
            elif paren_depth == 0 and text.startswith(delimiter, index):
                parts.append(text[start:index])
                index += len(delimiter)
                start = index
                continue
            index += 1

        parts.append(text[start:])
        return parts

    def _unescape_script_text(self, value: str) -> str:
        return (
            value.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\{", "{")
            .replace("\\}", "}")
            .replace("\\\\", "\\")
        )

    def _extract_url(self, value: str) -> str:
        value = value.strip()
        markdown_match = re.fullmatch(r"\[(.+)]\(([^)]+)\)", value)
        if markdown_match:
            value = markdown_match.group(2).strip()
        if len(value) >= 2 and value.startswith("(") and value.endswith(")"):
            value = value[1:-1].strip()
        return value

    def _validate_url(self, value: str, label: str) -> None:
        if value and not re.match(r"^https?://", value, re.IGNORECASE):
            raise EmbedScriptError(f"Invalid {label} URL.")

    def _parse_bool(self, value: str) -> bool:
        normalized = value.strip().lower()
        if normalized.startswith("inline="):
            normalized = normalized.split("=", 1)[1]
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        raise EmbedScriptError("Field inline value must be true or false.")

    def _check_length(self, value: str, limit: int, label: str) -> None:
        if len(value) > limit:
            raise EmbedScriptError(f"{label} exceeds Discord's {limit} character limit.")

    def compile_script(self, script: str) -> discord.Embed:
        tags = self._extract_tags(script)
        if not tags:
            raise EmbedScriptError("No embed tags were found in the script.")

        embed = discord.Embed()
        for tag in tags:
            self._apply_tag(embed, tag)
        return embed

    def _extract_tags(self, script: str) -> list[str]:
        tags: list[str] = []
        index = 0
        outside_buffer: list[str] = []

        while index < len(script):
            char = script[index]
            if char == "\\":
                outside_buffer.append(char)
                index += 1
                continue
            if char == "{":
                if "".join(outside_buffer).strip():
                    raise EmbedScriptError("Unexpected text found outside embed tags.")
                outside_buffer.clear()
                depth = 1
                start = index + 1
                index += 1
                while index < len(script):
                    if script[index] == "\\" and index + 1 < len(script):
                        index += 2
                        continue
                    if script[index] == "{":
                        depth += 1
                    elif script[index] == "}":
                        depth -= 1
                        if depth == 0:
                            tags.append(script[start:index].strip())
                            index += 1
                            break
                    index += 1
                else:
                    raise EmbedScriptError("Unclosed embed tag detected.")
                continue
            if not char.isspace():
                outside_buffer.append(char)
            index += 1

        if "".join(outside_buffer).strip():
            raise EmbedScriptError("Unexpected text found outside embed tags.")
        return tags

    def _apply_tag(self, embed: discord.Embed, tag: str) -> None:
        if ":" not in tag:
            raise EmbedScriptError(f"Invalid tag syntax: {{{tag}}}")

        tag_name, raw_params = tag.split(":", 1)
        tag_name = tag_name.strip().lower()
        params = [self._unescape_script_text(part.strip()) for part in self._split_top_level(raw_params)]

        if tag_name == "title":
            if len(params) != 1:
                raise EmbedScriptError("Title tag expects exactly one parameter.")
            self._check_length(params[0], 256, "Title")
            embed.title = params[0]
            return

        if tag_name in {"description", "desc"}:
            if len(params) != 1:
                raise EmbedScriptError("Description tag expects exactly one parameter.")
            self._check_length(params[0], 4096, "Description")
            embed.description = params[0]
            return

        if tag_name == "color":
            if len(params) != 1:
                raise EmbedScriptError("Color tag expects exactly one parameter.")
            color_match = re.fullmatch(r"#?[0-9a-fA-F]{6}", params[0].strip())
            if not color_match:
                raise EmbedScriptError("Color must be a valid 6-digit hex code.")
            embed.color = discord.Color(int(params[0].strip().lstrip("#"), 16))
            return

        if tag_name == "thumbnail":
            if len(params) != 1:
                raise EmbedScriptError("Thumbnail tag expects exactly one URL.")
            url = self._extract_url(params[0])
            self._validate_url(url, "thumbnail")
            embed.set_thumbnail(url=url)
            return

        if tag_name == "image":
            if len(params) != 1:
                raise EmbedScriptError("Image tag expects exactly one URL.")
            url = self._extract_url(params[0])
            self._validate_url(url, "image")
            embed.set_image(url=url)
            return

        if tag_name == "footer":
            if not 1 <= len(params) <= 2:
                raise EmbedScriptError("Footer tag expects text and an optional icon URL.")
            self._check_length(params[0], 2048, "Footer")
            icon_url = self._extract_url(params[1]) if len(params) == 2 else None
            self._validate_url(icon_url, "footer icon")
            embed.set_footer(text=params[0], icon_url=icon_url)
            return

        if tag_name == "author":
            if not 1 <= len(params) <= 3:
                raise EmbedScriptError("Author tag expects name, optional icon URL, and optional URL.")
            self._check_length(params[0], 256, "Author name")
            icon_url = self._extract_url(params[1]) if len(params) >= 2 else None
            author_url = self._extract_url(params[2]) if len(params) == 3 else None
            self._validate_url(icon_url, "author icon")
            self._validate_url(author_url, "author URL")
            embed.set_author(name=params[0], icon_url=icon_url, url=author_url)
            return

        if tag_name == "field":
            if len(params) != 3:
                raise EmbedScriptError("Field tag expects name, value, and inline=true|false.")
            self._check_length(params[0], 256, "Field name")
            self._check_length(params[1], 1024, "Field value")
            if len(embed.fields) >= 25:
                raise EmbedScriptError("Discord embeds cannot contain more than 25 fields.")
            embed.add_field(name=params[0], value=params[1], inline=self._parse_bool(params[2]))
            return

        raise EmbedScriptError(f"Unsupported embed tag: {tag_name}")

    def _escape_script_value(self, value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace("{", "\\{")
            .replace("}", "\\}")
        )

    def _embed_to_script(self, embed: discord.Embed) -> str:
        lines: list[str] = []

        if embed.title:
            lines.append(f"{{title: {self._escape_script_value(embed.title)}}}")
        if embed.description:
            lines.append(f"{{description: {self._escape_script_value(embed.description)}}}")
        if embed.color is not None:
            lines.append(f"{{color: #{embed.color.value:06x}}}")
        if embed.thumbnail and embed.thumbnail.url:
            lines.append(f"{{thumbnail: {self._escape_script_value(embed.thumbnail.url)}}}")
        if embed.image and embed.image.url:
            lines.append(f"{{image: {self._escape_script_value(embed.image.url)}}}")
        if embed.footer.text:
            footer = self._escape_script_value(embed.footer.text)
            if embed.footer.icon_url:
                footer += f" && ({self._escape_script_value(embed.footer.icon_url)})"
            lines.append(f"{{footer: {footer}}}")
        if embed.author.name:
            author = self._escape_script_value(embed.author.name)
            if embed.author.icon_url:
                author += f" && ({self._escape_script_value(embed.author.icon_url)})"
            if embed.author.url:
                author += f" && ({self._escape_script_value(embed.author.url)})"
            lines.append(f"{{author: {author}}}")

        for field in embed.fields:
            lines.append(
                "{field: "
                f"{self._escape_script_value(field.name)} && "
                f"{self._escape_script_value(field.value)} && "
                f"inline={'true' if field.inline else 'false'}"
                "}"
            )

        if not lines:
            raise EmbedScriptError("Target embed has no copyable properties.")
        return " ".join(lines)

    async def _send_code_chunks(self, ctx: commands.Context, script: str) -> None:
        chunk_size = 1800
        for index in range(0, len(script), chunk_size):
            chunk = script[index:index + chunk_size]
            await ctx.reply(f"```xrypton\n{chunk}\n```")

    @commands.hybrid_group(name="embed", aliases=["embeds"], invoke_without_command=True, description=f"Manage {get_bot_name()} embed scripts.")
    async def embed(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            prefix = ctx.prefix if ctx.prefix and ctx.prefix != f"<@!{self.bot.user.id}>" else f"@{self.bot.user.name} "
            embed = discord.Embed(
                title=f"{get_bot_name()} Embed Scripting",
                description=(
                    f"Compile raw {get_bot_name()} embed scripts into fully featured Discord embeds.\n\n"
                    "**Syntax**\n"
                    "`{title: text}`\n"
                    "`{description: text}` or `{desc: text}`\n"
                    "`{color: #ff0000}`\n"
                    "`{thumbnail: url}`\n"
                    "`{image: url}`\n"
                    "`{footer: text && (icon_url)}`\n"
                    "`{author: name && (icon_url) && (url)}`\n"
                    "`{field: name && value && inline=true|false}`\n\n"
                    f"Use `{prefix}embed create <name> <script>` to save a script.\n"
                    f"Use `{prefix}embed run <name> [channel]` to send it."
                ),
                color=self.color,
            )
            embed.set_footer(text=f"{get_bot_name()} Classic Embed Parser")
            await ctx.send(embed=embed)

    @embed.command(name="create", aliases=["add", "save"], description=f"Create or overwrite a {get_bot_name()} embed script.")
    @app_commands.describe(name="Script name", script=f"Raw {get_bot_name()} embed script")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_messages=True)
    async def embed_create(self, ctx: commands.Context, name: str, *, script: str):
        try:
            safe_name = self._validate_name(name)
            self.compile_script(script)
        except (EmbedScriptError, discord.HTTPException) as exc:
            embed = discord.Embed(description=f"{error} | {exc}", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)

        data = await self._read_data()
        guild_id = str(ctx.guild.id)
        data.setdefault(guild_id, {})[safe_name] = {
            "script_source": script,
            "created_by": ctx.author.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._write_data(data)

        embed = discord.Embed(
            description=f"{GreenTick2} | Embed script `{safe_name}` was created successfully.",
            color=self.color,
        )
        await ctx.reply(embed=embed)

    @embed.command(name="run", aliases=["send"], description=f"Send a saved {get_bot_name()} embed script.")
    @app_commands.describe(name="Script name", channel="Target channel")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_messages=True)
    async def embed_run(
        self,
        ctx: commands.Context,
        name: str,
        channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
    ):
        try:
            safe_name = self._validate_name(name)
            guild_scripts = await self._get_guild_scripts(ctx.guild.id)
            if safe_name not in guild_scripts:
                raise EmbedScriptError(f"No embed script named `{safe_name}` exists in this server.")
            embed = self.compile_script(guild_scripts[safe_name]["script_source"])
            target = channel or ctx.channel
            await target.send(embed=embed)
        except (EmbedScriptError, discord.Forbidden, discord.HTTPException) as exc:
            reply_embed = discord.Embed(description=f"{error} | {exc}", color=discord.Color.red())
            return await ctx.reply(embed=reply_embed, ephemeral=True)

        embed = discord.Embed(description=f"{GreenTick2} | Embed script `{safe_name}` was sent.", color=self.color)
        await ctx.reply(embed=embed, ephemeral=True)

    @embed.command(name="list", aliases=["all"], description=f"List saved {get_bot_name()} embed scripts.")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_messages=True)
    async def embed_list(self, ctx: commands.Context):
        guild_scripts = await self._get_guild_scripts(ctx.guild.id)
        if not guild_scripts:
            embed = discord.Embed(description=f"No {get_bot_name()} embed scripts are saved in this server.", color=self.color)
            return await ctx.reply(embed=embed)

        lines = []
        for script_name, script_data in sorted(guild_scripts.items()):
            created_by = script_data.get("created_by", "unknown")
            lines.append(f"`{script_name}` — created by <@{created_by}>")

        embed = discord.Embed(title=f"{get_bot_name()} Embed Scripts ({len(lines)})", color=self.color)
        for index in range(0, len(lines), 10):
            embed.add_field(name="Scripts", value="\n".join(lines[index:index + 10]), inline=False)
        await ctx.reply(embed=embed)

    @embed.command(name="delete", aliases=["remove", "del"], description=f"Delete a saved {get_bot_name()} embed script.")
    @app_commands.describe(name="Script name")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_messages=True)
    async def embed_delete(self, ctx: commands.Context, name: str):
        try:
            safe_name = self._validate_name(name)
            data = await self._read_data()
            guild_scripts = data.setdefault(str(ctx.guild.id), {})
            if safe_name not in guild_scripts:
                raise EmbedScriptError(f"No embed script named `{safe_name}` exists in this server.")
            guild_scripts.pop(safe_name)
            await self._write_data(data)
        except EmbedScriptError as exc:
            embed = discord.Embed(description=f"{error} | {exc}", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)

        embed = discord.Embed(description=f"{GreenTick2} | Embed script `{safe_name}` was deleted.", color=self.color)
        await ctx.reply(embed=embed)

    @embed.command(name="copy", description=f"Copy a replied-to Discord embed as {get_bot_name()} script syntax.")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_messages=True)
    async def embed_copy(self, ctx: commands.Context):
        reference = ctx.message.reference
        if not reference or not isinstance(reference.resolved, discord.Message):
            embed = discord.Embed(description=f"{error} | Reply to a message that contains an embed to copy it.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)

        target = reference.resolved
        if not target.embeds:
            embed = discord.Embed(description=f"{error} | The replied-to message does not contain a copyable Discord embed.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)

        scripts = []
        for discord_embed in target.embeds:
            try:
                scripts.append(self._embed_to_script(discord_embed))
            except EmbedScriptError:
                continue

        if not scripts:
            embed = discord.Embed(description=f"{error} | The target embed has no copyable properties.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)

        await self._send_code_chunks(ctx, "\n\n".join(scripts))


async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedScripting(bot))
