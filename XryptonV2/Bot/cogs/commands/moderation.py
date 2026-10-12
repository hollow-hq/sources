import discord
import json
import asyncio
import datetime
import re
from collections import Counter
from io import BytesIO
from typing import Union, Optional

import aiohttp
import requests
from discord.ext import commands
from discord.ui import Button, View

from core import Cog, Astroz, Context
from utils.Tools import *
from utils import Paginator, DescriptionEmbedPaginator
from utils.constants import GreenTick, GreenTick2, error, lnl_error

# ── Constants ─────────────────────────────────────────────────────────────────

MOD_ARROW = "<:mod_arrow:1074674871759540345>"
MOD_TICK = "<:mod_tick:1074674827610308688>"
MOD_UNTICK = "<:mod_untick:1074674904219258950>"
WARNING = "<:warning:1499683278695698432>"
NO_PERM_ICON = "<:new_no:1499682864134885436>"

time_regex = re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}

def get_bot_name():
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
            return data["bot"]["bot_name"]
    except Exception:
        return "Bot"

# ── Helpers ───────────────────────────────────────────────────────────────────

def convert_time(argument: str) -> int:
    """Parse a duration string like '10m', '2h' into total seconds."""
    matches = re.findall(time_regex, argument.lower())
    total = 0
    for key, value in matches:
        try:
            total += time_dict[value] * float(key)
        except KeyError:
            raise commands.BadArgument(f"`{value}` is an invalid time unit. Use h, m, s, or d.")
        except ValueError:
            raise commands.BadArgument(f"`{key}` is not a valid number.")
    return round(total)


def convert_simple(time: str) -> int:
    """Simple duration converter returning seconds, or -1/-2 on error."""
    unit = time[-1]
    if unit not in time_dict:
        return -1
    try:
        return int(time[:-1]) * time_dict[unit]
    except ValueError:
        return -2


def _icon(ctx: commands.Context) -> str:
    return ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url


def _has_role_authority(ctx: commands.Context) -> bool:
    return (
        ctx.author == ctx.guild.owner
        or ctx.author.top_role.position > ctx.guild.me.top_role.position
    )


def _is_extra_owner(ctx: commands.Context) -> bool:
    data = getExtra(ctx.guild.id)
    return ctx.author == ctx.guild.owner or str(ctx.author.id) in data["owners"]


def _perm_embed(ctx: commands.Context, owner_only: bool = False) -> discord.Embed:
    if owner_only:
        desc = f"{NO_PERM_ICON} | Only the server owner can run this command."
    else:
        desc = "```yaml\n - You must have Administrator permission.\n - Your top role must be above my top role.```"
    embed = discord.Embed(description=desc, color=0x4862DE)
    embed.set_author(name=ctx.author.name, icon_url=_icon(ctx))
    return embed


def _no_bot_perm_embed(color: int) -> discord.Embed:
    return discord.Embed(
        description="I'm missing a required permission. Please grant it and try again.",
        color=color,
    )


def _mod_no_perm_embed(bot_name: str, command: str, color: int) -> discord.Embed:
    embed = discord.Embed(
        color=color,
        description=(
            f"{MOD_UNTICK} You need certain **{bot_name}** permissions to use this command!\n"
            f"   {MOD_ARROW} Required permission: `{command}`"
        ),
    )
    embed.set_author(name="You can't use this command!")
    return embed


async def do_removal(ctx, limit, predicate, *, before=None, after=None):
    if limit > 2000:
        return await ctx.send(f"Too many messages to search ({limit}/2000).")
    before = ctx.message if before is None else discord.Object(id=before)
    after = discord.Object(id=after) if after is not None else None
    try:
        deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
    except discord.Forbidden:
        return await ctx.send("I don't have permission to delete messages.")
    except discord.HTTPException as e:
        return await ctx.send(f"Error: {e} (try a smaller search?)")

    spammers = Counter(m.author.display_name for m in deleted)
    count = len(deleted)
    lines = [f"{GreenTick2} | {count} message{'s were' if count != 1 else ' was'} removed."]
    if count:
        lines.append("")
        lines.extend(f"**{n}**: {c}" for n, c in sorted(spammers.items(), key=lambda t: t[1], reverse=True))

    summary = "\n".join(lines)
    if len(summary) > 2000:
        await ctx.send(f"{GreenTick2} | Successfully removed {count} messages.", delete_after=10)
    else:
        await ctx.send(summary, delete_after=10)


# ── Confirm View ──────────────────────────────────────────────────────────────

class ConfirmView(View):
    """Generic Yes/No confirmation view tied to a ctx author."""

    def __init__(self, ctx: commands.Context, timeout: int = 20):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.value: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, emoji=GreenTick)
    async def yes(self, interaction: discord.Interaction, button: Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, emoji=error)
    async def no(self, interaction: discord.Interaction, button: Button):
        self.value = False
        await interaction.response.defer()
        self.stop()


async def _confirm(ctx: commands.Context, description: str, color: int) -> Optional[discord.Message]:
    """
    Send a confirmation prompt. Returns the prompt message so the caller can edit it,
    or None if the user said No / timed out.
    """
    view = ConfirmView(ctx)
    embed = discord.Embed(description=description, color=color)
    embed.set_footer(text="Click Yes or No. You have 20 seconds.")
    msg = await ctx.reply(embed=embed, view=view, mention_author=False, delete_after=20)
    await view.wait()
    return msg if view.value else None


# ── Bulk-role helper ──────────────────────────────────────────────────────────

async def _bulk_role_action(
    ctx: commands.Context,
    role: discord.Role,
    color: int,
    *,
    action: str,          # "add" or "remove"
    target: str,          # "humans", "bots", "unverified", "all"
):
    """Shared logic for role {humans,bots,unverified,all} commands."""
    if not _has_role_authority(ctx):
        return await ctx.send(embed=_perm_embed(ctx))

    def _matches(member: discord.Member) -> bool:
        has_role = role in member.roles
        if target == "humans":
            return not member.bot and (not has_role if action == "add" else has_role)
        if target == "bots":
            return member.bot and (not has_role if action == "add" else has_role)
        if target == "unverified":
            return member.avatar is None and (not has_role if action == "add" else has_role)
        return not has_role if action == "add" else has_role  # "all"

    affected = [m for m in ctx.guild.members if _matches(m)]
    if not affected:
        noun = "have" if action == "add" else "already lack"
        return await ctx.reply(
            embed=discord.Embed(
                description=f"{role.mention} is already {'given to' if action == 'add' else 'removed from'} all {target} in this server.",
                color=color,
            )
        )

    verb = "give" if action == "add" else "remove"
    direction = "to" if action == "add" else "from"
    msg = await _confirm(
        ctx,
        f"**Are you sure you want to {verb} {role.mention} {direction} {len(affected)} {target}?**",
        color,
    )
    if msg is None:
        return

    await msg.edit(
        embed=discord.Embed(
            description=f"{'Adding' if action == 'add' else 'Removing'} {role.mention} {'to' if action == 'add' else 'from'} {len(affected)} {target}...",
            color=color,
        ),
        view=None,
    )

    count = 0
    for member in affected:
        try:
            if action == "add":
                await member.add_roles(role, reason=f"Requested by {ctx.author}")
            else:
                await member.remove_roles(role, reason=f"Requested by {ctx.author}")
            count += 1
        except Exception:
            pass

    past = "Added" if action == "add" else "Removed"
    await ctx.channel.send(
        f"{GreenTick} | Successfully {past} {role.mention} {'to' if action == 'add' else 'from'} {count} {target}."
    )


# ── Channel-wide lock/unlock/hide/unhide helper ───────────────────────────────

async def _all_channel_action(
    ctx: commands.Context,
    color: int,
    *,
    action: str,   # "lock", "unlock", "hide", "unhide"
):
    if not _has_role_authority(ctx):
        return await ctx.send(embed=_perm_embed(ctx))

    label_map = {
        "lock": ("Locking", "Locked", discord.PermissionOverwrite(send_messages=False, read_messages=True)),
        "unlock": ("Unlocking", "Unlocked", discord.PermissionOverwrite(send_messages=True, read_messages=True)),
        "hide": ("Hiding", "Hidden", discord.PermissionOverwrite(view_channel=False)),
        "unhide": ("Unhiding", "Unhidden", discord.PermissionOverwrite(view_channel=True)),
    }
    gerund, past, overwrite = label_map[action]

    msg = await _confirm(ctx, f"**Are you sure you want to {action} all channels in {ctx.guild.name}?**", color)
    if msg is None:
        return

    if not ctx.guild.me.guild_permissions.administrator:
        return await msg.edit(embed=_no_bot_perm_embed(color), view=None)

    await msg.edit(
        embed=discord.Embed(description=f"{gerund} all channels in {ctx.guild.name}...", color=color),
        view=None,
    )

    count = 0
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrite,
                reason=f"{action.title()}all by {ctx.author}",
            )
            count += 1
        except Exception:
            pass

    await ctx.channel.send(f"{GreenTick} | Successfully {past} {count} channel(s).")


# ── Single-channel lock/unlock/hide/unhide helper ─────────────────────────────

async def _single_channel_action(
    ctx: commands.Context,
    channel: discord.TextChannel,
    color: int,
    *,
    action: str,
):
    if not _has_role_authority(ctx):
        return await ctx.send(embed=_perm_embed(ctx))

    label_map = {
        "lock":   ("Locking", "Locked",   discord.PermissionOverwrite(send_messages=False)),
        "unlock": ("Unlocking", "Unlocked", discord.PermissionOverwrite(send_messages=True)),
        "hide":   ("Hiding", "Hidden",   None),   # uses existing overwrite
        "unhide": ("Unhiding", "Unhidden", None),
    }
    gerund, past, static_overwrite = label_map[action]

    if static_overwrite is None:
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = action == "unhide"
    else:
        overwrite = static_overwrite

    msg = await _confirm(ctx, f"**Are you sure you want to {action} {channel.mention}?**", color)
    if msg is None:
        return

    if not ctx.guild.me.guild_permissions.administrator:
        return await msg.edit(embed=_no_bot_perm_embed(color), view=None)

    await msg.edit(
        embed=discord.Embed(description=f"{gerund} {channel.mention}...", color=color),
        view=None,
    )
    try:
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"Channel {action} by {ctx.author}",
        )
    except Exception:
        pass

    await ctx.channel.send(f"{GreenTick} | Successfully {past} {channel.mention}.")


# ── Cog ───────────────────────────────────────────────────────────────────────

class Moderation(Cog, name='ModCommands'):
    def __init__(self, bot: Astroz):
        self.bot = bot
        self.color = 0x4862DE
        self.bot.sniped_messages = {}

    # ── enlarge ───────────────────────────────────────────────────────────────

    @commands.command()
    async def enlarge(self, ctx: Context, emoji: Union[discord.Emoji, discord.PartialEmoji, str]):
        """Enlarge any emoji."""
        await ctx.send(emoji.url)

    # ── lock / unlock / hide / unhide (single channel) ────────────────────────

    @commands.hybrid_command(name="lock", aliases=["lockdown"], help="Lock a channel.", usage="lock [channel] [reason]")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _lock(self, ctx: Context, channel: discord.TextChannel = None, *, reason=None):
        await _single_channel_action(ctx, channel or ctx.channel, self.color, action="lock")

    @commands.hybrid_command(name="unlock", aliases=["unlockdown"], help="Unlock a channel.", usage="unlock [channel] [reason]")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _unlock(self, ctx: Context, channel: discord.TextChannel = None, *, reason=None):
        await _single_channel_action(ctx, channel or ctx.channel, self.color, action="unlock")

    @commands.hybrid_command(name="hide", help="Hide a channel.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _hide(self, ctx: Context, channel: discord.TextChannel = None):
        await _single_channel_action(ctx, channel or ctx.channel, self.color, action="hide")

    @commands.hybrid_command(name="unhide", help="Unhide a channel.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _unhide(self, ctx: Context, channel: discord.TextChannel = None):
        await _single_channel_action(ctx, channel or ctx.channel, self.color, action="unhide")

    # ── lockall / unlockall / hideall / unhideall ─────────────────────────────

    @commands.hybrid_command(name="lockall", help="Lock all channels.", usage="lockall")
    @blacklist_check()
    @ignore_check()
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def lockall(self, ctx: Context):
        await _all_channel_action(ctx, self.color, action="lock")

    @commands.hybrid_command(name="unlockall", help="Unlock all channels.", usage="unlockall")
    @blacklist_check()
    @ignore_check()
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def unlockall(self, ctx: Context):
        await _all_channel_action(ctx, self.color, action="unlock")

    @commands.hybrid_command(name="hideall", help="Hide all channels.", usage="hideall")
    @blacklist_check()
    @ignore_check()
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def hideall(self, ctx: Context):
        await _all_channel_action(ctx, self.color, action="hide")

    @commands.hybrid_command(name="unhideall", help="Unhide all channels.", usage="unhideall")
    @blacklist_check()
    @ignore_check()
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def unhideall(self, ctx: Context):
        await _all_channel_action(ctx, self.color, action="unhide")

    # ── prefix ────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="prefix", aliases=["setprefix", "prefixset"], help="Change the bot prefix for this server.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def _prefix(self, ctx: Context, prefix: str):
        if not _has_role_authority(ctx):
            return await ctx.send(embed=_perm_embed(ctx))
        data = getConfig(ctx.guild.id)
        data["prefix"] = prefix
        updateConfig(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=(
                f"{GreenTick} | Prefix for **{ctx.guild.name}** changed to `{prefix}`.\n"
                f"Use `{prefix}help` for more info."
            ),
            color=self.color,
        ))

    # ── mute ──────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="mute", aliases=["timeout", "stfu"], description="Timeout a member for a given duration.", usage="mute <member> <duration>")
    @commands.cooldown(1, 20, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @blacklist_check()
    @ignore_check()
    async def _mute(self, ctx: Context, member: discord.Member, duration: str):
        data = getConfig(ctx.guild.id)
        data2 = getExtra(ctx.guild.id)
        adminrole = ctx.guild.get_role(data["adminrole"])
        modsrole = ctx.guild.get_role(data2["modrole"])

        authorized = (
            ctx.author == ctx.guild.owner
            or str(ctx.author.id) in data["admins"]
            or adminrole in ctx.author.roles
            or str(ctx.author.id) in data2["mods"]
            or modsrole in ctx.author.roles
        )
        if not authorized:
            return await ctx.send(embed=_mod_no_perm_embed(get_bot_name(), "Timeout Command", self.color))

        seconds = convert_simple(duration)
        if seconds == -1:
            return await ctx.reply(embed=discord.Embed(
                color=self.color,
                description=f"{error} | Invalid time unit. Examples: `10m`, `2h`, `1d`",
            ), mention_author=False)
        if seconds == -2:
            return await ctx.reply(embed=discord.Embed(
                color=self.color,
                description=f"{error} | Time value must be a whole number.",
            ), mention_author=False)

        if member.guild_permissions.administrator:
            return await ctx.reply(embed=discord.Embed(
                color=self.color,
                description=f"{WARNING} | I can't mute administrators.",
            ))

        unit_labels = {"s": "Second(s)", "m": "Minute(s)", "h": "Hour(s)", "d": "Day(s)"}
        unit = duration[-1].lower()
        amount = duration[:-1]
        label = unit_labels.get(unit, "Second(s)")

        embed = discord.Embed(
            color=self.color,
            description=f"**Moderator:** {ctx.author.mention}\n**Details:**\n   {MOD_ARROW} Duration: {amount} {label}",
        )
        embed.set_author(name="Timeout Result:", icon_url=_icon(ctx))
        embed.add_field(name=f"{MOD_TICK} Successful Timeouts", value=f"{MOD_ARROW} `{member}`", inline=False)
        embed.add_field(name=f"{MOD_UNTICK} Unsuccessful Operations", value="All users were timed out!", inline=False)

        try:
            await member.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=seconds), reason=f"Requested by {ctx.author}")
            await ctx.send(embed=embed)
        except Exception:
            pass

    # ── unmute ────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="unmute", description="Remove a timeout from a member.", usage="unmute <member>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 20, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def untimeout(self, ctx: Context, member: discord.Member):
        data = getConfig(ctx.guild.id)
        data2 = getExtra(ctx.guild.id)
        adminrole = ctx.guild.get_role(data["adminrole"])
        modsrole = ctx.guild.get_role(data2["modrole"])

        authorized = (
            ctx.author == ctx.guild.owner
            or str(ctx.author.id) in data["admins"]
            or adminrole in ctx.author.roles
            or str(ctx.author.id) in data2["mods"]
            or modsrole in ctx.author.roles
        )
        if not authorized:
            return await ctx.send(embed=_mod_no_perm_embed(get_bot_name(), "Unmute Command", self.color))

        if not member.is_timed_out():
            return await ctx.send(embed=discord.Embed(
                color=self.color,
                description=f"{WARNING} | {member.mention} is not muted.",
                timestamp=ctx.message.created_at,
            ))

        try:
            await member.edit(timed_out_until=None)
            embed = discord.Embed(
                color=self.color,
                description=f"**Moderator:** {ctx.author.mention}",
            )
            embed.set_author(name="Unmute Result:", icon_url=_icon(ctx))
            embed.add_field(name=f"{MOD_TICK} Successful Unmutes", value=f"{MOD_ARROW} `{member}`", inline=False)
            await ctx.reply(embed=embed)
            try:
                await member.send(f"{lnl_error} | You have been unmuted in **{ctx.guild.name}** by {ctx.author} (ID: {ctx.author.id}).")
            except discord.Forbidden:
                pass
        except Exception:
            await ctx.send(embed=discord.Embed(
                color=self.color,
                description=f"{WARNING} | Failed to remove timeout from {member}.",
            ))

    # ── kick ──────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="kick", help="Kick a member from the server.", usage="kick <member> [reason]")
    @commands.cooldown(1, 20, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @blacklist_check()
    @ignore_check()
    async def _kick(self, ctx: Context, member: discord.Member, *, reason: str = "No reason provided"):
        data = getConfig(ctx.guild.id)
        adminrole = ctx.guild.get_role(data["adminrole"])
        authorized = (
            ctx.author == ctx.guild.owner
            or str(ctx.author.id) in data["admins"]
            or adminrole in ctx.author.roles
        )
        if not authorized:
            return await ctx.send(embed=_mod_no_perm_embed(get_bot_name(), "Kick Command", self.color))

        view = ConfirmView(ctx)
        embed = discord.Embed(color=self.color, description=f"{MOD_ARROW} **Target:** {member}")
        embed.set_author(name="Proceed with kick?", icon_url=_icon(ctx))
        embed.set_footer(text="You have 20 seconds.")
        msg = await ctx.reply(embed=embed, view=view, mention_author=False, delete_after=20)
        await view.wait()

        if not view.value:
            return

        if not ctx.guild.me.guild_permissions.kick_members:
            return await msg.edit(embed=_no_bot_perm_embed(self.color), view=None)

        mem = await self.bot.fetch_user(member.id)
        await ctx.guild.kick(mem, reason=f"{reason} | by {ctx.author}")

        result = discord.Embed(
            color=self.color,
            description=f"**Moderator:** {ctx.author.mention}\n**Details:**\n   {MOD_ARROW} Reason: {reason}",
        )
        result.set_author(name="Kick Result:", icon_url=_icon(ctx))
        result.add_field(name=f"{MOD_TICK} Successful Kicks", value=f"{MOD_ARROW} `{mem}`", inline=False)
        await msg.edit(embed=result, view=None)
        try:
            await mem.send(f"{lnl_error} | You were kicked from **{ctx.guild.name}** for: {reason} by {ctx.author} (ID: {ctx.author.id}).")
        except discord.Forbidden:
            pass

    # ── ban ───────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="ban", aliases=["hackban"], help="Ban a member from the server.", usage="ban <member> [reason]")
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @blacklist_check()
    @ignore_check()
    async def _ban(self, ctx: Context, member: Optional[Union[discord.Member, discord.User]] = None, *, reason: str = "No reason provided"):
        data = getConfig(ctx.guild.id)
        adminrole = ctx.guild.get_role(data["adminrole"])
        authorized = (
            ctx.author == ctx.guild.owner
            or str(ctx.author.id) in data["admins"]
            or adminrole in ctx.author.roles
        )
        if not authorized:
            return await ctx.send(embed=_mod_no_perm_embed(get_bot_name(), "Ban Command", self.color))

        if member is None:
            return await ctx.send_help(ctx.command)

        view = ConfirmView(ctx)
        mem = await self.bot.fetch_user(member.id)
        embed = discord.Embed(color=self.color, description=f"{MOD_ARROW} **Target:** {mem}")
        embed.set_author(name="Proceed with ban?", icon_url=_icon(ctx))
        embed.set_footer(text="You have 20 seconds.")
        msg = await ctx.reply(embed=embed, view=view, mention_author=False, delete_after=20)
        await view.wait()

        if not view.value:
            return

        if not ctx.guild.me.guild_permissions.ban_members:
            return await msg.edit(embed=_no_bot_perm_embed(self.color), view=None)

        await ctx.guild.ban(mem, reason=f"{reason} | by {ctx.author}")

        result = discord.Embed(
            color=self.color,
            description=f"**Moderator:** {ctx.author.mention}\n**Details:**\n   {MOD_ARROW} Reason: {reason}",
        )
        result.set_author(name="Ban Result:", icon_url=_icon(ctx))
        result.add_field(name=f"{MOD_TICK} Successful Bans", value=f"{MOD_ARROW} `{mem}`", inline=False)
        await msg.edit(embed=result, view=None)
        try:
            await mem.send(f"{lnl_error} | You were banned from **{ctx.guild.name}** for: {reason} by {ctx.author} (ID: {ctx.author.id}).")
        except discord.Forbidden:
            pass

    # ── unban ─────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="unban", help="Unban a user by ID.", usage="unban <user_id>")
    @blacklist_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.has_permissions(ban_members=True)
    async def _unban(self, ctx: Context, user_id: int):
        data = getConfig(ctx.guild.id)
        adminrole = ctx.guild.get_role(data["adminrole"])
        authorized = (
            ctx.author == ctx.guild.owner
            or str(ctx.author.id) in data["admins"]
            or adminrole in ctx.author.roles
        )
        if not authorized:
            return await ctx.send(embed=_mod_no_perm_embed(get_bot_name(), "Unban Command", self.color))

        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        embed = discord.Embed(color=self.color, description=f"**Moderator:** {ctx.author.mention}")
        embed.set_author(name="Unban Result:", icon_url=_icon(ctx))
        embed.add_field(name=f"{MOD_TICK} Successful Unbans", value=f"{MOD_ARROW} `{user}`", inline=False)
        await ctx.send(embed=embed)

    # ── warn ──────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="warn", help="Warn a member.", usage="warn <member> [reason]")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def _warn(self, ctx: Context, member: discord.Member, *, reason: str = "No reason provided"):
        data = getConfig(ctx.guild.id)
        data2 = getExtra(ctx.guild.id)
        adminrole = ctx.guild.get_role(data["adminrole"])
        modsrole = ctx.guild.get_role(data2["modrole"])
        authorized = (
            ctx.author == ctx.guild.owner
            or str(ctx.author.id) in data["admins"]
            or adminrole in ctx.author.roles
            or str(ctx.author.id) in data2["mods"]
            or modsrole in ctx.author.roles
        )
        if not authorized:
            return await ctx.send(embed=_mod_no_perm_embed(get_bot_name(), "Warn Command", self.color))

        embed = discord.Embed(
            color=self.color,
            description=f"**Moderator:** {ctx.author.mention}\n**Details:**\n   {MOD_TICK} Reason: {reason}",
        )
        embed.set_author(name="Warn Result:", icon_url=_icon(ctx))
        embed.add_field(name=f"{MOD_TICK} Successful Warns", value=f"{MOD_ARROW} `{member}`", inline=False)
        await ctx.send(embed=embed)
        try:
            dm = discord.Embed(
                color=self.color,
                description=f"{lnl_error} | You were warned in **{ctx.guild.name}** for: {reason} by [{ctx.author}](https://discord.com/users/{ctx.author.id}).",
            )
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

    # ── nick ──────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="nick", aliases=["setnick"], help="Change a member's nickname.", usage="nick <member> [name]")
    @blacklist_check()
    @ignore_check()
    async def changenickname(self, ctx: Context, member: discord.Member, *, name: str = None):
        data = getConfig(ctx.guild.id)
        data2 = getExtra(ctx.guild.id)
        adminrole = ctx.guild.get_role(data["adminrole"])
        modsrole = ctx.guild.get_role(data2["modrole"])
        authorized = (
            ctx.author == ctx.guild.owner
            or str(ctx.author.id) in data["admins"]
            or adminrole in ctx.author.roles
            or str(ctx.author.id) in data2["mods"]
            or modsrole in ctx.author.roles
        )
        if not authorized:
            return await ctx.send(embed=_mod_no_perm_embed(get_bot_name(), "Nick Command", self.color))

        try:
            await member.edit(nick=name)
            desc = (
                f"{GreenTick2} | Nickname of {member} changed to **{name}**."
                if name else
                f"{GreenTick2} | Nickname of {member} cleared."
            )
            await ctx.send(embed=discord.Embed(description=desc, color=self.color))
        except Exception as e:
            print(e)

    # ── clone ─────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="clone", help="Clone a channel.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_channels=True)
    async def clone(self, ctx: Context, channel: discord.TextChannel):
        await channel.clone()
        embed = discord.Embed(
            color=self.color,
            description=f"{GreenTick2} | **{channel.name}** has been cloned.",
        )
        embed.set_author(name=ctx.author.name, icon_url=_icon(ctx))
        await ctx.send(embed=embed)

    # ── nuke ──────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="nuke", help="Nuke a channel.", usage="nuke")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_channels=True)
    async def _nuke(self, ctx: Context):
        view = ConfirmView(ctx)
        embed = discord.Embed(color=self.color, description="**Are you sure you want to nuke this channel?**")
        embed.set_footer(text="You have 20 seconds.")
        msg = await ctx.reply(embed=embed, view=view, mention_author=False, delete_after=20)
        await view.wait()

        if not view.value:
            return

        if not ctx.guild.me.guild_permissions.manage_channels:
            return await msg.edit(embed=_no_bot_perm_embed(self.color), view=None)

        channel = ctx.channel
        new_channel = await channel.clone()
        await new_channel.edit(position=channel.position)
        await channel.delete()

        nuke_embed = discord.Embed(
            title="Nuke",
            description=f"Channel nuked by **`{ctx.author}`**",
            color=self.color,
        )
        nuke_embed.set_image(url="https://media2.giphy.com/media/HhTXt43pk1I1W/giphy.gif")
        await new_channel.send(embed=nuke_embed)

    # ── slowmode / unslowmode ─────────────────────────────────────────────────

    @commands.hybrid_command(name="slowmode", aliases=["slow"], help="Set channel slowmode.", usage="slowmode [seconds]")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 2, commands.BucketType.user)
    @commands.has_permissions(manage_messages=True)
    async def _slowmode(self, ctx: Context, seconds: int = 0):
        if seconds > 120:
            return await ctx.send(embed=discord.Embed(
                title="Slowmode", description="Slowmode cannot exceed 2 minutes (120 seconds).", color=self.color
            ))
        await ctx.channel.edit(slowmode_delay=seconds)
        desc = "Slowmode disabled." if seconds == 0 else f"Slowmode set to **`{seconds}s`**."
        await ctx.send(embed=discord.Embed(title="Slowmode", description=desc, color=self.color))

    @commands.hybrid_command(name="unslowmode", aliases=["unslow"], help="Disable slowmode.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 2, commands.BucketType.user)
    @commands.has_permissions(manage_messages=True)
    async def _unslowmode(self, ctx: Context):
        await ctx.channel.edit(slowmode_delay=0)
        await ctx.send(embed=discord.Embed(title="Unslowmode", description="Slowmode disabled.", color=self.color))

    # ── give / role (toggle) ──────────────────────────────────────────────────

    async def _toggle_role(self, ctx: Context, member: discord.Member, role: discord.Role):
        """Add role if member doesn't have it, remove if they do."""
        data = getConfig(ctx.guild.id)
        adminrole = ctx.guild.get_role(data["adminrole"])
        authorized = (
            ctx.author == ctx.guild.owner
            or str(ctx.author.id) in data["admins"]
            or adminrole in ctx.author.roles
        )
        if not authorized:
            return await ctx.send(embed=_mod_no_perm_embed(get_bot_name(), "Role Command", self.color))

        if role not in member.roles:
            await member.add_roles(role, reason=f"{ctx.author} (ID: {ctx.author.id})")
            desc = f"{GreenTick} | Changed roles for **{member.name}**, +{role.name}"
        else:
            await member.remove_roles(role, reason=f"{ctx.author} (ID: {ctx.author.id})")
            desc = f"{GreenTick} | Changed roles for **{member.name}**, -{role.name}"

        await ctx.send(embed=discord.Embed(description=desc, color=self.color))

    @commands.hybrid_command(name="give", aliases=["addrole"], help="Toggle a role on a member.", usage="give <member> <role>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def give(self, ctx: Context, member: discord.Member, *, role: discord.Role):
        await self._toggle_role(ctx, member, role)

    @commands.group(name="role", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    async def role(self, ctx: Context, member: discord.Member, *, role: discord.Role):
        await self._toggle_role(ctx, member, role)

    @role.command(name="temp", help="Temporarily give a role to a member.")
    @commands.bot_has_permissions(manage_roles=True)
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def temp(self, ctx: Context, role: discord.Role, time: str, *, user: discord.Member):
        if role == ctx.author.top_role:
            return await ctx.send(embed=discord.Embed(description=f"{error} | {role} has the same position as your top role.", color=self.color))
        if role.position >= ctx.guild.me.top_role.position:
            return await ctx.send(embed=discord.Embed(description=f"{error} | {role} is higher than my role. Move my role above it.", color=self.color))
        seconds = convert_time(time)
        await user.add_roles(role)
        await ctx.send(embed=discord.Embed(description=f"{GreenTick} | Added {role.mention} to {user.mention}.", color=self.color))
        await asyncio.sleep(seconds)
        await user.remove_roles(role)

    @role.command(name="delete", help="Delete a role from the server.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def delete(self, ctx: Context, *, role: discord.Role):
        if role == ctx.author.top_role:
            return await ctx.send(embed=discord.Embed(description=f"{error} | {role} has the same position as your top role.", color=self.color))
        if role.position >= ctx.guild.me.top_role.position:
            return await ctx.send(embed=discord.Embed(description=f"{error} | {role} is higher than my role.", color=self.color))
        await role.delete()
        await ctx.send(embed=discord.Embed(description=f"{GreenTick} | Successfully deleted {role.name}.", color=self.color))

    @role.command(name="create", help="Create a role in the server.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def create(self, ctx: Context, *, name: str):
        if not _has_role_authority(ctx):
            return await ctx.send(embed=_perm_embed(ctx))
        await ctx.guild.create_role(name=name, color=discord.Color.default())
        await ctx.send(embed=discord.Embed(description=f"{GreenTick} | Created role **{name}**.", color=self.color))

    @role.command(name="rename", help="Rename a role.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def rename(self, ctx: Context, role: discord.Role, *, newname: str):
        if not _has_role_authority(ctx):
            return await ctx.send(embed=_perm_embed(ctx))
        old = role.name
        await role.edit(name=newname)
        await ctx.send(f"{GreenTick} | **{old}** renamed to **{newname}**.")

    @role.command(name="humans", help="Give a role to all humans in the server.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def role_humans(self, ctx: Context, *, role: discord.Role):
        await _bulk_role_action(ctx, role, self.color, action="add", target="humans")

    @role.command(name="bots", help="Give a role to all bots in the server.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def role_bots(self, ctx: Context, *, role: discord.Role):
        await _bulk_role_action(ctx, role, self.color, action="add", target="bots")

    @role.command(name="unverified", help="Give a role to all unverified members.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def role_unverified(self, ctx: Context, *, role: discord.Role):
        await _bulk_role_action(ctx, role, self.color, action="add", target="unverified")

    @role.command(name="all", help="Give a role to all members.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def role_all(self, ctx: Context, *, role: discord.Role):
        await _bulk_role_action(ctx, role, self.color, action="add", target="all")

    # ── removerole group ──────────────────────────────────────────────────────

    @commands.group(name="removerole", aliases=["rrole"], invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def rrole(self, ctx: Context):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @rrole.command(name="humans", help="Remove a role from all humans.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def rrole_humans(self, ctx: Context, *, role: discord.Role):
        await _bulk_role_action(ctx, role, self.color, action="remove", target="humans")

    @rrole.command(name="bots", help="Remove a role from all bots.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def rrole_bots(self, ctx: Context, *, role: discord.Role):
        await _bulk_role_action(ctx, role, self.color, action="remove", target="bots")

    @rrole.command(name="unverified", help="Remove a role from all unverified members.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def rrole_unverified(self, ctx: Context, *, role: discord.Role):
        await _bulk_role_action(ctx, role, self.color, action="remove", target="unverified")

    @rrole.command(name="all", help="Remove a role from all members.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.has_permissions(administrator=True)
    async def rrole_all(self, ctx: Context, *, role: discord.Role):
        await _bulk_role_action(ctx, role, self.color, action="remove", target="all")

    # ── admin group ───────────────────────────────────────────────────────────

    @commands.hybrid_group(name="admin", invoke_without_command=True, usage="admin add/remove/show/reset/role")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _admin(self, ctx: Context):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @_admin.command(name="add", help="Add a user to the admin list.", usage="admin add <user>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_add(self, ctx: Context, user: discord.User):
        if ctx.author != ctx.guild.owner:
            return await ctx.reply(embed=_perm_embed(ctx, owner_only=True), mention_author=False)
        data = getConfig(ctx.guild.id)
        wled = data["admins"]
        if len(wled) >= 100:
            return await ctx.reply(embed=discord.Embed(
                description=f"{error} | Admin list is full (100). Remove one to add another.",
                color=self.color,
            ), mention_author=False)
        if str(user.id) in wled:
            return await ctx.reply(embed=discord.Embed(
                description=f"{error} | {user} is already in the admin list.",
                color=self.color,
            ), mention_author=False)
        wled.append(str(user.id))
        updateConfig(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=f"{GreenTick2} | {user.mention} added to the admin list.",
            color=self.color,
        ), mention_author=False)

    @_admin.command(name="remove", help="Remove a user from the admin list.", usage="admin remove <user>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_remove(self, ctx: Context, user: discord.User):
        if ctx.author != ctx.guild.owner:
            return await ctx.reply(embed=_perm_embed(ctx, owner_only=True), mention_author=False)
        data = getConfig(ctx.guild.id)
        wled = data["admins"]
        if str(user.id) not in wled:
            return await ctx.reply(embed=discord.Embed(
                description=f"{error} | {user} is not in the admin list.",
                color=self.color,
            ), mention_author=False)
        wled.remove(str(user.id))
        updateConfig(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=f"{GreenTick2} | {user.mention} removed from the admin list.",
            color=self.color,
        ), mention_author=False)

    @_admin.command(name="show", help="Show the admin list.", usage="admin show")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_show(self, ctx: Context):
        data = getConfig(ctx.guild.id)
        wled = data["admins"]
        if not wled:
            return await ctx.reply(embed=discord.Embed(
                description=f"{error} | No admins have been added for this server.",
                color=self.color,
            ), mention_author=False)
        entries = [f"`{i}` | <@!{uid}> | ID: [{uid}](https://discord.com/users/{uid})" for i, uid in enumerate(wled, 1)]
        await Paginator(source=DescriptionEmbedPaginator(entries=entries, title=f"Admins — {ctx.guild.name} ({len(wled)})", description="", color=self.color), ctx=ctx).paginate()

    @_admin.command(name="reset", aliases=["clear"], help="Clear the admin list.", usage="admin reset")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_reset(self, ctx: Context):
        if not _has_role_authority(ctx):
            return await ctx.reply(embed=_perm_embed(ctx), mention_author=False)
        data = getConfig(ctx.guild.id)
        data["admins"] = []
        updateConfig(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=f"{GreenTick2} | Admin list cleared for **{ctx.guild.name}**.",
            color=self.color,
        ), mention_author=False)

    @_admin.command(name="admin_role", help="Set the admin role.", usage="admin role <role>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_role(self, ctx: Context, *, role: discord.Role):
        if not _has_role_authority(ctx):
            return await ctx.reply(embed=_perm_embed(ctx), mention_author=False)
        data = getConfig(ctx.guild.id)
        data["adminrole"] = role.id
        updateConfig(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=f"{GreenTick2} | {role.mention} set as the admin role for {ctx.guild.name}.",
            color=self.color,
        ), mention_author=False)

    # ── mod group ─────────────────────────────────────────────────────────────

    @commands.hybrid_group(name="mod", invoke_without_command=True, usage="mod add/remove/show/reset/role")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _mod(self, ctx: Context):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @_mod.command(name="add", help="Add a user to the mod list.", usage="mod add <user>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def mod_add(self, ctx: Context, user: discord.User):
        if not _has_role_authority(ctx):
            return await ctx.reply(embed=_perm_embed(ctx), mention_author=False)
        data = getExtra(ctx.guild.id)
        wled = data["mods"]
        if len(wled) >= 100:
            return await ctx.reply(embed=discord.Embed(
                description=f"{error} | Mod list is full (100). Remove one to add another.",
                color=self.color,
            ), mention_author=False)
        if str(user.id) in wled:
            return await ctx.reply(embed=discord.Embed(
                description=f"{error} | {user} is already in the mod list.",
                color=self.color,
            ), mention_author=False)
        wled.append(str(user.id))
        updateExtra(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=f"{GreenTick2} | {user.mention} added to the mod list.",
            color=self.color,
        ), mention_author=False)

    @_mod.command(name="remove", help="Remove a user from the mod list.", usage="mod remove <user>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def mod_remove(self, ctx: Context, user: discord.User):
        if not _has_role_authority(ctx):
            return await ctx.reply(embed=_perm_embed(ctx), mention_author=False)
        data = getExtra(ctx.guild.id)
        wled = data["mods"]
        if str(user.id) not in wled:
            return await ctx.reply(embed=discord.Embed(
                description=f"{error} | {user} is not in the mod list.",
                color=self.color,
            ), mention_author=False)
        wled.remove(str(user.id))
        updateExtra(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=f"{GreenTick2} | {user.mention} removed from the mod list.",
            color=self.color,
        ), mention_author=False)

    @_mod.command(name="show", help="Show the mod list.", usage="mod show")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def mod_show(self, ctx: Context):
        data = getExtra(ctx.guild.id)
        wled = data["mods"]
        if not wled:
            return await ctx.reply(embed=discord.Embed(
                description=f"{error} | No mods have been added for this server.",
                color=self.color,
            ), mention_author=False)
        entries = [f"`{i}` | <@!{uid}> | ID: [{uid}](https://discord.com/users/{uid})" for i, uid in enumerate(wled, 1)]
        await Paginator(source=DescriptionEmbedPaginator(entries=entries, title=f"Mods — {ctx.guild.name} ({len(wled)})", description="", color=self.color), ctx=ctx).paginate()

    @_mod.command(name="reset", aliases=["clear"], help="Clear the mod list.", usage="mod reset")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def mod_reset(self, ctx: Context):
        if not _has_role_authority(ctx):
            return await ctx.reply(embed=_perm_embed(ctx), mention_author=False)
        data = getExtra(ctx.guild.id)
        data["mods"] = []
        updateExtra(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=f"{GreenTick2} | Mod list cleared for **{ctx.guild.name}**.",
            color=self.color,
        ), mention_author=False)

    @_mod.command(name="role", help="Set the mod role.", usage="mod role <role>")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def mod_role(self, ctx: Context, *, role: discord.Role):
        if not _has_role_authority(ctx):
            return await ctx.reply(embed=_perm_embed(ctx), mention_author=False)
        data = getExtra(ctx.guild.id)
        data["modrole"] = role.id
        updateExtra(ctx.guild.id, data)
        await ctx.reply(embed=discord.Embed(
            description=f"{GreenTick2} | {role.mention} set as the mod role for {ctx.guild.name}.",
            color=self.color,
        ), mention_author=False)

    # ── sticker commands ──────────────────────────────────────────────────────

    @commands.hybrid_command(aliases=["as", "stealsticker"], description="Add a sticker to the server.")
    @commands.has_permissions(manage_emojis=True)
    async def addsticker(self, ctx: Context, *, name: str = None):
        if ctx.message.reference is None:
            return await ctx.reply("Reply to a message containing a sticker.")
        msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if not msg.stickers:
            return await ctx.reply("No sticker found in that message.")
        sticker = msg.stickers[0]
        if name is None:
            name = sticker.name
        try:
            response = requests.get(sticker.url)
            fname = "Sticker.gif" if sticker.url.endswith("gif") else "Sticker.png"
            file = discord.File(BytesIO(response.content), fname)
            s = await ctx.guild.create_sticker(name=name, description=f"Added by {self.bot.user}", emoji="❤️", file=file)
            await ctx.reply(f"{GreenTick2} | Sticker `{name}` created successfully.", stickers=[s])
        except Exception:
            await ctx.reply("Failed to create the sticker.")

    @commands.hybrid_command(aliases=["deletesticker", "removesticker"], description="Delete a sticker from the server.")
    @commands.has_permissions(manage_emojis=True)
    async def delsticker(self, ctx: Context):
        if ctx.message.reference is None:
            return await ctx.reply("Reply to a message containing a sticker.")
        msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if not msg.stickers:
            return await ctx.reply("No sticker found in that message.")
        try:
            name = ""
            for sticker in msg.stickers:
                name = sticker.name
                await ctx.guild.delete_sticker(sticker)
            await ctx.reply(f"{GreenTick2} | Sticker `{name}` deleted successfully.")
        except Exception:
            await ctx.reply("Failed to delete the sticker.")

    # ── emoji commands ────────────────────────────────────────────────────────

    @commands.hybrid_command(aliases=["deleteemoji", "removeemoji"], description="Delete emoji(s) from the server.")
    @commands.has_permissions(manage_emojis=True)
    async def delemoji(self, ctx: Context, emoji=None):
        init = await ctx.reply("Processing...", mention_author=False)
        con = ctx.message.content
        if ctx.message.reference is not None:
            ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            con = ref.content

        matches = re.findall(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>", con)
        if not matches:
            await init.delete()
            return await ctx.reply("No custom emoji found.")
        if len(matches) >= 20:
            await init.delete()
            return await ctx.reply("Maximum of 20 emojis can be deleted at once.")

        count = 0
        for eid in matches:
            try:
                emo = await ctx.guild.fetch_emoji(int(eid))
                await emo.delete()
                count += 1
            except Exception:
                pass
        await init.delete()
        await ctx.reply(f"{GreenTick2} | Deleted {count}/{len(matches)} emoji(s).")

    @commands.command(aliases=["steal", "ae"], description="Add emoji(s) to the server.")
    @commands.has_permissions(manage_emojis=True)
    async def addemoji(self, ctx: Context, emoji: Union[discord.Emoji, discord.PartialEmoji, str] = None, *, name: str = None):
        init = await ctx.reply("Processing...", mention_author=False)
        con = ctx.message.content
        if ctx.message.reference is not None:
            ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            con = ref.content

        matches = re.findall(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>", con)

        # Multi-emoji from message
        if len(matches) > 1:
            if len(matches) >= 20:
                await init.delete()
                return await ctx.reply("Maximum of 20 emojis can be added at once.")
            count = 0
            for eid in matches:
                emo = discord.PartialEmoji.from_str(eid)
                url = f"https://cdn.discordapp.com/emojis/{emo.id}.{'gif' if emo.animated else 'png'}"
                try:
                    async with aiohttp.request("GET", url) as r:
                        img = await r.read()
                    await ctx.guild.create_custom_emoji(name=emo.name, image=img)
                    count += 1
                except Exception:
                    pass
            await init.delete()
            return await ctx.reply(embed=discord.Embed(description=f"{GreenTick2} | Created {count}/{len(matches)} emoji(s).", color=self.color))

        # Single emoji object
        if isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
            if name is None:
                name = emoji.name
            url = f"https://cdn.discordapp.com/emojis/{emoji.id}.{'gif' if emoji.animated else 'png'}"
            try:
                async with aiohttp.request("GET", url) as r:
                    img = await r.read()
                emo = await ctx.guild.create_custom_emoji(name=name, image=img)
                await init.delete()
                return await ctx.reply(f"{GreenTick2} | Created {emo}.")
            except Exception:
                await init.delete()
                return await ctx.reply("Failed to create emoji. Emoji slots might be full.")

        # URL string
        if isinstance(emoji, str):
            if not emoji.startswith("https://"):
                await init.delete()
                return await ctx.reply("Provide a valid image URL.")
            if name is None:
                await init.delete()
                return await ctx.reply("Please provide a name for the emoji.")
            try:
                async with aiohttp.request("GET", emoji) as r:
                    img = await r.read()
                emo = await ctx.guild.create_custom_emoji(name=name, image=img)
                await init.delete()
                return await ctx.reply(f"{GreenTick2} | Created {emo}.")
            except Exception:
                await init.delete()
                return await ctx.reply("Failed to create emoji. Emoji slots might be full.")

        await init.delete()
        await ctx.reply("No emoji found.")

    # ── roleicon ──────────────────────────────────────────────────────────────

    @commands.command(description="Change the icon for a role.")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def roleicon(self, ctx: Context, role: discord.Role, *, icon: Union[discord.Emoji, discord.PartialEmoji, str] = None):
        if role.position >= ctx.guild.me.top_role.position:
            return await ctx.send(embed=discord.Embed(description=f"{error} | {role.mention} is higher than my role. Move it below me.", color=self.color))
        if ctx.author.top_role.position <= role.position:
            return await ctx.send(embed=discord.Embed(description=f"{error} | {role.mention} is at or above your top role.", color=self.color), delete_after=15)

        async def _set_icon(url_or_bytes):
            if isinstance(url_or_bytes, bytes):
                await role.edit(display_icon=url_or_bytes)
            else:
                async with aiohttp.request("GET", url_or_bytes) as r:
                    await role.edit(display_icon=await r.read())

        try:
            if icon is None:
                if ctx.message.attachments:
                    async with aiohttp.request("GET", ctx.message.attachments[0].url) as r:
                        img = await r.read()
                    await role.edit(display_icon=img)
                    em = discord.Embed(description=f"{GreenTick2} | Icon of {role.mention} updated.", color=self.color)
                else:
                    await role.edit(display_icon=None)
                    em = discord.Embed(description=f"{GreenTick2} | Icon removed from {role.mention}.", color=self.color)
            elif isinstance(icon, (discord.Emoji, discord.PartialEmoji)):
                async with aiohttp.request("GET", f"https://cdn.discordapp.com/emojis/{icon.id}.png") as r:
                    img = await r.read()
                await role.edit(display_icon=img)
                em = discord.Embed(description=f"{GreenTick2} | Icon of {role.mention} set to {icon}.", color=self.color)
            else:
                if not icon.startswith("https://"):
                    return await ctx.reply("Provide a valid URL.")
                async with aiohttp.request("GET", icon) as r:
                    img = await r.read()
                await role.edit(display_icon=img)
                em = discord.Embed(description=f"{GreenTick2} | Icon of {role.mention} updated.", color=self.color)
            await ctx.reply(embed=em, mention_author=False)
        except Exception:
            await ctx.reply("Failed to change the role icon.")

    # ── clear / purge group ───────────────────────────────────────────────────

    @commands.group(name="clear", aliases=["purge"], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: Context, choice: Union[discord.Member, int], amount: int = None):
        """Clear messages. Pass a member or a number."""
        await ctx.message.delete()
        if isinstance(choice, discord.Member):
            return await do_removal(ctx, amount or 5, lambda m: m.author == choice)
        await do_removal(ctx, choice, lambda m: True)

    @clear.command(name="embeds")
    @commands.has_permissions(manage_messages=True)
    async def clear_embeds(self, ctx: Context, search: int = 100):
        await ctx.message.delete()
        await do_removal(ctx, search, lambda m: len(m.embeds))

    @clear.command(name="files")
    @commands.has_permissions(manage_messages=True)
    async def clear_files(self, ctx: Context, search: int = 100):
        await ctx.message.delete()
        await do_removal(ctx, search, lambda m: len(m.attachments))

    @clear.command(name="images")
    @commands.has_permissions(manage_messages=True)
    async def clear_images(self, ctx: Context, search: int = 100):
        await ctx.message.delete()
        await do_removal(ctx, search, lambda m: len(m.embeds) or len(m.attachments))

    @clear.command(name="all")
    @commands.has_permissions(manage_messages=True)
    async def clear_all(self, ctx: Context, search: int = 100):
        await ctx.message.delete()
        await do_removal(ctx, search, lambda m: True)

    @clear.command(name="user")
    @commands.has_permissions(manage_messages=True)
    async def clear_user(self, ctx: Context, member: discord.Member, search: int = 100):
        await ctx.message.delete()
        await do_removal(ctx, search, lambda m: m.author == member)

    @clear.command(name="contains")
    @commands.has_permissions(manage_messages=True)
    async def clear_contains(self, ctx: Context, *, string: str):
        await ctx.message.delete()
        if len(string) < 3:
            return await ctx.send("The search string must be at least 3 characters long.")
        await do_removal(ctx, 100, lambda m: string in m.content)

    @clear.command(name="bot", aliases=["bots", "b"])
    @commands.has_permissions(manage_messages=True)
    async def clear_bot(self, ctx: Context, prefix: str = None, search: int = 100):
        await ctx.message.delete()
        await do_removal(ctx, search, lambda m: (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix)))

    @clear.command(name="emoji", aliases=["emojis"])
    @commands.has_permissions(manage_messages=True)
    async def clear_emoji(self, ctx: Context, search: int = 100):
        await ctx.message.delete()
        pattern = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")
        await do_removal(ctx, search, lambda m: pattern.search(m.content))

    @clear.command(name="reactions")
    @commands.has_permissions(manage_messages=True)
    async def clear_reactions(self, ctx: Context, search: int = 100):
        await ctx.message.delete()
        if search > 2000:
            return await ctx.send(f"Too many messages to search ({search}/2000).")
        total = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if message.reactions:
                total += sum(r.count for r in message.reactions)
                await message.clear_reactions()
        await ctx.send(f"{GreenTick2} | Removed {total} reaction(s).")

    # ── snipe ─────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if not message.guild.me.guild_permissions.view_audit_log:
            return

        url = message.attachments[0].url if message.attachments else None
        content = message.content or "***Content Unavailable***"
        moderator = None

        async for entry in message.guild.audit_logs(
            limit=1,
            after=datetime.datetime.now() - datetime.timedelta(minutes=1),
            action=discord.AuditLogAction.message_delete,
        ):
            if entry.target == message.author:
                moderator = entry.user

        self.bot.sniped_messages[message.guild.id] = (
            content, url, message.author, message.channel, moderator, message.created_at
        )
    
    @commands.command(description="Snipe the most recently deleted message in a channel.")
    async def snipe(self, ctx: Context, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            content, url, author, ch, mod, timestamp = self.bot.sniped_messages[ctx.guild.id]
        except KeyError:
            return await ctx.send("No recently deleted message found.")

        if ch != channel:
            return await ctx.send("No recently deleted message found in that channel.")

        embed = discord.Embed(
            description=f":wastebasket: Message by {author.mention} deleted in {ch.mention}",
            color=self.color,
            timestamp=timestamp,
        )
        embed.add_field(name="Content", value=content, inline=False)
        if mod:
            embed.add_field(name="Deleted By", value=f"{mod.mention} (ID: {mod.id})")
        if url and url.startswith("https://"):
            embed.set_image(url=url)
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)


# ── Setup ─────────────────────────────────────────────────────────────────────

async def setup(bot: Astroz):
    await bot.add_cog(Moderation(bot))