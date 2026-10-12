from __future__ import annotations

import json
import os
from typing import Optional

import aiohttp
import discord
from discord.ext import commands
from discord.ui import Button, View

from core import Cog, Context

DATA_FILE = "data/confessions_data.json"


def _ensure_file() -> None:
    """Create the data dir and empty JSON file if they don't exist."""
    dir_ = os.path.dirname(DATA_FILE)
    if dir_:
        os.makedirs(dir_, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)


class ConfessionsCog(Cog):
    """Full anonymous confession system for Discord servers."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.color = 0x9B59B6
        self.data: dict[str, dict] = {}
        _ensure_file()
        self._load()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def _save(self) -> None:
        tmp = f"{DATA_FILE}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)

    def _guild(self, guild_id: int) -> dict:
        gid = str(guild_id)
        if gid not in self.data:
            self.data[gid] = {
                "confession_channel_id": None,
                "report_channel_id": None,
                "webhook_name": "Confessions",
                "webhook_avatar_url": None,
                "disabled": False,
                "muted_users": [],
                "blacklist": [],
                "confessions": [],
            }
            self._save()
        return self.data[gid]

    # ------------------------------------------------------------------
    # Webhook handling
    # ------------------------------------------------------------------
    async def _get_or_create_webhook(
        self, guild_data: dict, channel: discord.TextChannel
    ) -> discord.Webhook:
        """Fetch an existing matching webhook or create a new one."""
        webhook = None
        for wh in await channel.webhooks():
            if wh.name == guild_data["webhook_name"]:
                webhook = wh
                break

        avatar_bytes = None
        avatar_url = guild_data.get("webhook_avatar_url")
        if avatar_url:
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(avatar_url) as resp:
                        if resp.status == 200:
                            avatar_bytes = await resp.read()
            except Exception:
                pass

        if webhook is None:
            kwargs: dict = {"name": guild_data["webhook_name"], "reason": "Confessions webhook"}
            if avatar_bytes:
                kwargs["avatar"] = avatar_bytes
            webhook = await channel.create_webhook(**kwargs)
        else:
            if avatar_bytes and avatar_url:
                await webhook.edit(avatar=avatar_bytes, reason="Refresh confessions avatar")

        return webhook

    # ------------------------------------------------------------------
    # Permission errors
    # ------------------------------------------------------------------
    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="You need Manage Server permission to use this command.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                description=str(error),
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)

    # ------------------------------------------------------------------
    # ,confessions group
    # ------------------------------------------------------------------
    @commands.group(name="confessions", invoke_without_command=True)
    async def confessions_group(self, ctx: Context) -> None:
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Confessions System",
                description="Manage anonymous confessions for this server.",
                color=self.color,
            )
            embed.add_field(
                name=",confessions add <message>",
                value="Submit an anonymous confession",
                inline=False,
            )
            embed.add_field(
                name=",confessions reportchannel [channel|clear]",
                value="Set or view the report channel",
                inline=False,
            )
            embed.add_field(
                name=",confessions report <number>",
                value="Report a confession to moderators",
                inline=False,
            )
            embed.add_field(
                name=",confessions disable",
                value="Toggle confessions on/off",
                inline=False,
            )
            embed.add_field(
                name=",confessions name <name>",
                value="Set webhook display name",
                inline=False,
            )
            embed.add_field(
                name=",confessions avatar <url>",
                value="Set webhook avatar URL (or `clear`)",
                inline=False,
            )
            embed.add_field(
                name=",confessions config",
                value="View current configuration",
                inline=False,
            )
            embed.add_field(
                name=",confessions mute <number>",
                value="Mute a confession author",
                inline=False,
            )
            embed.add_field(
                name=",confessions unmute <number>",
                value="Unmute a confession author",
                inline=False,
            )
            embed.add_field(
                name=",confessions mutelist",
                value="List muted confession authors",
                inline=False,
            )
            embed.add_field(
                name=",confessions blacklist",
                value="Manage blacklisted phrases",
                inline=False,
            )
            await ctx.reply(embed=embed)

    # ------------------------------------------------------------------
    # ,confessions add
    # ------------------------------------------------------------------
    @confessions_group.command(name="add")
    async def add(self, ctx: Context, *, message: str) -> None:
        if ctx.guild is None:
            return

        gd = self._guild(ctx.guild.id)

        if gd.get("disabled"):
            embed = discord.Embed(
                description="Confessions are currently disabled for this server.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        if ctx.author.id in gd.get("muted_users", []):
            return

        content_lower = message.lower()
        for phrase in gd.get("blacklist", []):
            if phrase.lower() in content_lower:
                embed = discord.Embed(
                    description="Your confession contains a blacklisted phrase.",
                    color=0xE74C3C,
                )
                await ctx.reply(embed=embed)
                return

        channel_id = gd.get("confession_channel_id")
        if not channel_id:
            embed = discord.Embed(
                description="The confession channel has not been set up yet.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        channel = ctx.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                description="The configured confession channel was not found.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        number = len(gd["confessions"]) + 1
        entry = {
            "number": number,
            "author_id": ctx.author.id,
            "content": message,
            "message_id": None,
        }
        gd["confessions"].append(entry)
        self._save()

        try:
            webhook = await self._get_or_create_webhook(gd, channel)
            embed = discord.Embed(
                title=f"Confession #{number}",
                description=message,
                color=0x9B59B6,
            )
            embed.set_footer(text="Submit your own with ,confessions add <message>")
            webhook_msg = await webhook.send(embed=embed, wait=True)
            entry["message_id"] = webhook_msg.id
            self._save()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # ,confessions mute / unmute
    # ------------------------------------------------------------------
    @confessions_group.command(name="mute")
    @commands.has_guild_permissions(manage_guild=True)
    async def mute(self, ctx: Context, number: int) -> None:
        gd = self._guild(ctx.guild.id)
        confession = next((c for c in gd["confessions"] if c["number"] == number), None)
        if not confession:
            embed = discord.Embed(
                description="No confession found with that number.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        uid = confession["author_id"]
        if uid not in gd.setdefault("muted_users", []):
            gd["muted_users"].append(uid)
            self._save()

        embed = discord.Embed(
            description="Confession author has been muted.",
            color=self.color,
        )
        await ctx.reply(embed=embed)

    @confessions_group.command(name="unmute")
    @commands.has_guild_permissions(manage_guild=True)
    async def unmute(self, ctx: Context, number: int) -> None:
        gd = self._guild(ctx.guild.id)
        confession = next((c for c in gd["confessions"] if c["number"] == number), None)
        if not confession:
            embed = discord.Embed(
                description="No confession found with that number.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        uid = confession["author_id"]
        if uid in gd.get("muted_users", []):
            gd["muted_users"].remove(uid)
            self._save()

        embed = discord.Embed(
            description="Confession author has been unmuted.",
            color=self.color,
        )
        await ctx.reply(embed=embed)

    # ------------------------------------------------------------------
    # ,confessions mutelist (paginated)
    # ------------------------------------------------------------------
    @confessions_group.command(name="mutelist")
    @commands.has_guild_permissions(manage_guild=True)
    async def mutelist(self, ctx: Context) -> None:
        gd = self._guild(ctx.guild.id)
        muted = gd.get("muted_users", [])

        if not muted:
            embed = discord.Embed(
                description="No users are currently muted.",
                color=self.color,
            )
            await ctx.reply(embed=embed)
            return

        entries: list[str] = []
        for uid in muted:
            numbers = [str(c["number"]) for c in gd["confessions"] if c["author_id"] == uid]
            entries.append(f"User ID: {uid} — Confessions: {', '.join(numbers) if numbers else 'None'}")

        per_page = 10
        pages = [entries[i : i + per_page] for i in range(0, len(entries), per_page)]
        view = PaginationView(ctx, pages, self.color)
        await ctx.reply(embed=view.get_embed(), view=view)

    # ------------------------------------------------------------------
    # ,confessions reportchannel
    # ------------------------------------------------------------------
    @confessions_group.command(name="reportchannel")
    @commands.has_guild_permissions(manage_guild=True)
    async def reportchannel(self, ctx: Context, *, target: Optional[str] = None) -> None:
        gd = self._guild(ctx.guild.id)

        if target is None:
            cid = gd.get("report_channel_id")
            if cid:
                ch = ctx.guild.get_channel(cid)
                mention = ch.mention if ch else f"ID: {cid}"
                embed = discord.Embed(
                    description=f"Report channel is set to: {mention}",
                    color=self.color,
                )
            else:
                embed = discord.Embed(
                    description="Report channel is not set.",
                    color=self.color,
                )
            await ctx.reply(embed=embed)
            return

        if target.lower() == "clear":
            gd["report_channel_id"] = None
            self._save()
            embed = discord.Embed(
                description="Report channel has been cleared.",
                color=self.color,
            )
            await ctx.reply(embed=embed)
            return

        try:
            channel = await commands.TextChannelConverter().convert(ctx, target)
        except commands.BadArgument:
            embed = discord.Embed(
                description="Could not find that channel.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        gd["report_channel_id"] = channel.id
        self._save()
        embed = discord.Embed(
            description=f"Report channel has been set to {channel.mention}.",
            color=self.color,
        )
        await ctx.reply(embed=embed)

    # ------------------------------------------------------------------
    # ,confessions report
    # ------------------------------------------------------------------
    @confessions_group.command(name="report")
    async def report(self, ctx: Context, number: int) -> None:
        if ctx.guild is None:
            return

        gd = self._guild(ctx.guild.id)
        cid = gd.get("report_channel_id")
        if not cid:
            embed = discord.Embed(
                description="No report channel has been configured.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        channel = ctx.guild.get_channel(cid)
        if not isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                description="The configured report channel is unavailable.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        confession = next((c for c in gd["confessions"] if c["number"] == number), None)
        if not confession:
            embed = discord.Embed(
                description="No confession found with that number.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        embed = discord.Embed(
            title="Confession reported",
            color=0xE74C3C,
        )
        embed.add_field(name="Confession #", value=str(number), inline=False)
        embed.add_field(
            name="Content",
            value=confession["content"][:1024],
            inline=False,
        )
        embed.add_field(
            name="Reported by",
            value=f"{ctx.author} (`{ctx.author.id}`)",
            inline=False,
        )
        if confession.get("message_id") and gd.get("confession_channel_id"):
            jump = (
                f"https://discord.com/channels/{ctx.guild.id}"
                f"/{gd['confession_channel_id']}/{confession['message_id']}"
            )
            embed.add_field(name="Jump to original", value=f"[Link]({jump})", inline=False)

        await channel.send(embed=embed)

        confirm = discord.Embed(
            description="Confession reported to moderators.",
            color=self.color,
        )
        await ctx.reply(embed=confirm)

    # ------------------------------------------------------------------
    # ,confessions disable
    # ------------------------------------------------------------------
    @confessions_group.command(name="disable")
    @commands.has_guild_permissions(manage_guild=True)
    async def disable(self, ctx: Context) -> None:
        gd = self._guild(ctx.guild.id)
        gd["disabled"] = not gd.get("disabled", False)
        self._save()

        state = "disabled" if gd["disabled"] else "enabled"
        embed = discord.Embed(
            description=f"Confessions have been **{state}**.",
            color=self.color,
        )
        await ctx.reply(embed=embed)

    # ------------------------------------------------------------------
    # ,confessions name
    # ------------------------------------------------------------------
    @confessions_group.command(name="name")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_name(self, ctx: Context, *, webhook_name: str) -> None:
        gd = self._guild(ctx.guild.id)
        gd["webhook_name"] = webhook_name
        self._save()
        embed = discord.Embed(
            description=f"Webhook name set to: **{webhook_name}**",
            color=self.color,
        )
        await ctx.reply(embed=embed)

    # ------------------------------------------------------------------
    # ,confessions avatar
    # ------------------------------------------------------------------
    @confessions_group.command(name="avatar")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_avatar(self, ctx: Context, *, url: Optional[str] = None) -> None:
        gd = self._guild(ctx.guild.id)
        if url and url.lower() == "clear":
            gd["webhook_avatar_url"] = None
            self._save()
            embed = discord.Embed(
                description="Webhook avatar has been cleared.",
                color=self.color,
            )
            await ctx.reply(embed=embed)
            return

        if not url:
            embed = discord.Embed(
                description="Please provide a URL or use `clear`.",
                color=0xE74C3C,
            )
            await ctx.reply(embed=embed)
            return

        gd["webhook_avatar_url"] = url
        self._save()
        embed = discord.Embed(
            description=f"Webhook avatar URL set to: {url}",
            color=self.color,
        )
        await ctx.reply(embed=embed)

    # ------------------------------------------------------------------
    # ,confessions config
    # ------------------------------------------------------------------
    @confessions_group.command(name="config")
    @commands.has_guild_permissions(manage_guild=True)
    async def config(self, ctx: Context) -> None:
        gd = self._guild(ctx.guild.id)

        confess_ch = (
            ctx.guild.get_channel(gd["confession_channel_id"])
            if gd.get("confession_channel_id")
            else None
        )
        report_ch = (
            ctx.guild.get_channel(gd["report_channel_id"])
            if gd.get("report_channel_id")
            else None
        )

        embed = discord.Embed(
            title="Confessions Configuration",
            color=self.color,
        )
        embed.add_field(
            name="Confession Channel",
            value=confess_ch.mention if confess_ch else "not set",
            inline=False,
        )
        embed.add_field(
            name="Report Channel",
            value=report_ch.mention if report_ch else "not set",
            inline=False,
        )
        embed.add_field(
            name="Disabled",
            value="Yes" if gd.get("disabled") else "No",
            inline=False,
        )
        embed.add_field(
            name="Webhook Name",
            value=gd.get("webhook_name", "Confessions"),
            inline=False,
        )
        embed.add_field(
            name="Webhook Avatar URL",
            value=gd.get("webhook_avatar_url") or "not set",
            inline=False,
        )
        embed.add_field(
            name="Total Confessions",
            value=str(len(gd.get("confessions", []))),
            inline=False,
        )
        embed.add_field(
            name="Muted Users",
            value=str(len(gd.get("muted_users", []))),
            inline=False,
        )
        embed.add_field(
            name="Blacklisted Phrases",
            value=str(len(gd.get("blacklist", []))),
            inline=False,
        )
        await ctx.reply(embed=embed)

    # ------------------------------------------------------------------
    # ,confessions blacklist subgroup
    # ------------------------------------------------------------------
    @confessions_group.group(name="blacklist", invoke_without_command=True)
    async def blacklist_group(self, ctx: Context) -> None:
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Blacklist Subcommands",
                description="Manage blacklisted phrases for confessions.",
                color=self.color,
            )
            embed.add_field(
                name=",confessions blacklist add <phrase>",
                value="Add a phrase to the blacklist",
                inline=False,
            )
            embed.add_field(
                name=",confessions blacklist remove <phrase>",
                value="Remove a phrase from the blacklist",
                inline=False,
            )
            embed.add_field(
                name=",confessions blacklist list",
                value="List all blacklisted phrases",
                inline=False,
            )
            embed.add_field(
                name=",confessions blacklist clear",
                value="Clear all blacklisted phrases",
                inline=False,
            )
            await ctx.reply(embed=embed)

    @blacklist_group.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    async def blacklist_add(self, ctx: Context, *, phrase: str) -> None:
        gd = self._guild(ctx.guild.id)
        bl = gd.setdefault("blacklist", [])
        if phrase.lower() not in (p.lower() for p in bl):
            bl.append(phrase)
            self._save()
            embed = discord.Embed(
                description=f"Added phrase to blacklist: **{phrase}**",
                color=self.color,
            )
        else:
            embed = discord.Embed(
                description="That phrase is already blacklisted.",
                color=0xE74C3C,
            )
        await ctx.reply(embed=embed)

    @blacklist_group.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def blacklist_remove(self, ctx: Context, *, phrase: str) -> None:
        gd = self._guild(ctx.guild.id)
        bl = gd.get("blacklist", [])
        for i, p in enumerate(bl):
            if p.lower() == phrase.lower():
                bl.pop(i)
                self._save()
                embed = discord.Embed(
                    description=f"Removed phrase from blacklist: **{phrase}**",
                    color=self.color,
                )
                await ctx.reply(embed=embed)
                return
        embed = discord.Embed(
            description=f"Phrase not found in blacklist: **{phrase}**",
            color=0xE74C3C,
        )
        await ctx.reply(embed=embed)

    @blacklist_group.command(name="list")
    @commands.has_guild_permissions(manage_guild=True)
    async def blacklist_list(self, ctx: Context) -> None:
        gd = self._guild(ctx.guild.id)
        bl = gd.get("blacklist", [])

        if not bl:
            embed = discord.Embed(
                description="No phrases are blacklisted.",
                color=self.color,
            )
            await ctx.reply(embed=embed)
            return

        per_page = 10
        pages = [bl[i : i + per_page] for i in range(0, len(bl), per_page)]
        view = PaginationView(ctx, pages, self.color, title="Blacklisted Phrases")
        await ctx.reply(embed=view.get_embed(), view=view)

    @blacklist_group.command(name="clear")
    @commands.has_guild_permissions(manage_guild=True)
    async def blacklist_clear(self, ctx: Context) -> None:
        gd = self._guild(ctx.guild.id)
        if not gd.get("blacklist"):
            embed = discord.Embed(
                description="The blacklist is already empty.",
                color=self.color,
            )
            await ctx.reply(embed=embed)
            return

        embed = discord.Embed(
            description=f"Are you sure you want to clear all {len(gd['blacklist'])} blacklisted phrases?",
            color=self.color,
        )
        view = ConfirmView(ctx, self.color)
        msg = await ctx.reply(embed=embed, view=view)
        await view.wait()

        if view.result is True:
            gd["blacklist"] = []
            self._save()
            embed = discord.Embed(
                description="Blacklist has been cleared.",
                color=self.color,
            )
        else:
            embed = discord.Embed(
                description="Blacklist clear cancelled.",
                color=self.color,
            )
        for item in view.children:
            item.disabled = True
        await msg.edit(embed=embed, view=view)


# ------------------------------------------------------------------
# Generic pagination view (prev / next, 10 per page, 60s timeout)
# ------------------------------------------------------------------
class PaginationView(View):
    def __init__(
        self,
        ctx: Context,
        pages: list[list[str]],
        color: int,
        title: str = "",
        timeout: float = 60.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.pages = pages
        self.color = color
        self.title = title
        self.current = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current == len(self.pages) - 1

    def get_embed(self) -> discord.Embed:
        content = "\n".join(self.pages[self.current])
        embed = discord.Embed(
            title=self.title,
            description=content,
            color=self.color,
        )
        embed.set_footer(text=f"Page {self.current + 1} / {len(self.pages)}")
        return embed

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.message = interaction.message
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "You cannot control this menu.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.blurple)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current -= 1
        if self.current < 0:
            self.current = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.blurple)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current += 1
        if self.current >= len(self.pages):
            self.current = len(self.pages) - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


# ------------------------------------------------------------------
# Simple confirm / cancel view (30s timeout)
# ------------------------------------------------------------------
class ConfirmView(View):
    def __init__(self, ctx: Context, color: int, timeout: float = 30.0) -> None:
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.color = color
        self.result: Optional[bool] = None
        self.message: Optional[discord.Message] = None

    async def on_timeout(self) -> None:
        self.result = False
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.message = interaction.message
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "Only the command invoker can confirm.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.result = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.result = False
        self.stop()
        await interaction.response.defer()


# ------------------------------------------------------------------
# Setup function
# ------------------------------------------------------------------
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConfessionsCog(bot))
