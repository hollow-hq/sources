from __future__ import annotations

import asyncio
import json
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.Tools import blacklist_check, ignore_check
from utils.config import get_bot_name
from utils.constants import GreenTick2, error


VANITY_FILE = "data/vanity.json"
DEFAULT_MESSAGE = "Thanks for supporting us, {user.mention}!"


class VanityStatus(commands.Cog):
    """Reward members for featuring the configured vanity keyword in their custom status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.color = 0x5865F2
        self._notified: dict[str, set[str]] = {}

    async def cog_load(self):
        await self._ensure_file()

    async def _read_data(self) -> dict:
        def load() -> dict:
            if not os.path.exists(VANITY_FILE):
                return {}
            with open(VANITY_FILE, "r", encoding="utf-8") as file:
                return json.load(file)

        return await asyncio.to_thread(load)

    async def _write_data(self, data: dict):
        def save() -> None:
            temp_path = f"{VANITY_FILE}.tmp"
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            os.replace(temp_path, VANITY_FILE)

        await asyncio.to_thread(save)

    async def _ensure_file(self):
        data = await self._read_data()
        if not data:
            await self._write_data({})

    def _default_config(self) -> dict:
        return {
            "keyword": "",
            "reward_roles": [],
            "channels": [],
            "message": DEFAULT_MESSAGE,
            "blacklist": {
                "users": [],
                "roles": [],
                "text": [],
            },
            "notified_users": [],
        }

    def _normalize_config(self, config: dict) -> dict:
        default = self._default_config()
        for key, value in default.items():
            if key not in config:
                config[key] = value
            elif isinstance(value, dict):
                for child_key, child_value in value.items():
                    config[key].setdefault(child_key, child_value)
        if not isinstance(config["blacklist"], dict):
            config["blacklist"] = default["blacklist"].copy()
        if not isinstance(config["reward_roles"], list):
            config["reward_roles"] = []
        if not isinstance(config["channels"], list):
            config["channels"] = []
        if not isinstance(config["notified_users"], list):
            config["notified_users"] = []
        return config

    async def _get_guild_config(self, guild_id: int) -> dict:
        data = await self._read_data()
        guild_id_string = str(guild_id)
        if guild_id_string not in data:
            data[guild_id_string] = self._default_config()
            await self._write_data(data)
        config = self._normalize_config(data[guild_id_string])
        data[guild_id_string] = config
        await self._write_data(data)
        return config

    async def _save_guild_config(self, guild_id: int, config: dict):
        data = await self._read_data()
        data[str(guild_id)] = self._normalize_config(config)
        await self._write_data(data)

    def _get_custom_status(self, member: discord.Member) -> str:
        for activity in member.activities:
            if activity.type is discord.ActivityType.custom:
                return getattr(activity, "state", None) or getattr(activity, "name", None) or ""
        return ""

    def _is_blacklisted(self, member: discord.Member, status: str, config: dict) -> tuple[bool, str]:
        blacklist = config.get("blacklist", {})
        blacklisted_users = {str(user_id) for user_id in blacklist.get("users", [])}
        blacklisted_roles = {str(role_id) for role_id in blacklist.get("roles", [])}
        blacklisted_text = [str(text).lower() for text in blacklist.get("text", []) if str(text).strip()]

        if str(member.id) in blacklisted_users:
            return True, "user"
        if blacklisted_roles.intersection(str(role.id) for role in member.roles):
            return True, "role"
        if any(text and text in status.lower() for text in blacklisted_text):
            return True, "text"
        return False, ""

    def _format_message(self, template: str, member: discord.Member, status: str, config: dict) -> str:
        keyword = config.get("keyword", "")
        replacements = {
            "{user.mention}": member.mention,
            "{user.name}": member.name,
            "{user.id}": str(member.id),
            "{guild.name}": member.guild.name,
            "{guild.id}": str(member.guild.id),
            "{keyword}": keyword,
            "{status}": status,
        }
        message = template or DEFAULT_MESSAGE
        for key, value in replacements.items():
            message = message.replace(key, value)
        return message

    async def _award_roles(self, member: discord.Member, role_ids: list[int]) -> list[discord.Role]:
        added: list[discord.Role] = []
        roles = [role for role_id in role_ids if (role := member.guild.get_role(role_id))]
        missing = [role for role in roles if role not in member.roles]
        if not missing:
            return added
        if not member.guild.me.guild_permissions.manage_roles:
            return added
        try:
            await member.add_roles(*missing, reason="VanityStatus keyword reward")
        except discord.Forbidden:
            return added
        except discord.HTTPException:
            return added
        return missing

    async def _remove_roles(self, member: discord.Member, role_ids: list[int]) -> list[discord.Role]:
        removed: list[discord.Role] = []
        roles = [role for role_id in role_ids if (role := member.guild.get_role(role_id))]
        present = [role for role in roles if role in member.roles]
        if not present:
            return removed
        if not member.guild.me.guild_permissions.manage_roles:
            return removed
        try:
            await member.remove_roles(*present, reason="VanityStatus keyword removed")
        except discord.Forbidden:
            return removed
        except discord.HTTPException:
            return removed
        return removed

    async def _send_milestone_notification(self, member: discord.Member, status: str, config: dict) -> None:
        channel_ids = [int(channel_id) for channel_id in config.get("channels", [])]
        if not channel_ids:
            return
        message = self._format_message(config.get("message", DEFAULT_MESSAGE), member, status, config)
        for channel_id in channel_ids:
            channel = self.bot.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.abc.Messageable):
                continue
            try:
                await channel.send(content=message)
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                continue

    async def _mark_notified(self, guild_id: int, member_id: int, config: dict) -> None:
        notified = config.setdefault("notified_users", [])
        member_id_string = str(member_id)
        if member_id_string not in notified:
            notified.append(member_id_string)
        self._notified.setdefault(str(guild_id), set(notified)).add(member_id_string)
        await self._save_guild_config(guild_id, config)

    def _already_notified(self, guild_id: int, member_id: int, config: dict) -> bool:
        guild_notified = self._notified.setdefault(str(guild_id), set(config.get("notified_users", [])))
        return str(member_id) in guild_notified

    async def _handle_member(self, member: discord.Member) -> None:
        if member.bot or not member.guild:
            return
        config = await self._get_guild_config(member.guild.id)
        keyword = str(config.get("keyword", "")).strip()
        if not keyword:
            return

        status = self._get_custom_status(member)
        if keyword.lower() in status.lower():
            blacklisted, _ = self._is_blacklisted(member, status, config)
            if blacklisted:
                await self._remove_roles(member, [int(role_id) for role_id in config.get("reward_roles", [])])
                return
            added_roles = await self._award_roles(member, [int(role_id) for role_id in config.get("reward_roles", [])])
            if added_roles and not self._already_notified(member.guild.id, member.id, config):
                await self._send_milestone_notification(member, status, config)
                await self._mark_notified(member.guild.id, member.id, config)
            return

        await self._remove_roles(member, [int(role_id) for role_id in config.get("reward_roles", [])])

    async def _check_member_now(self, member: discord.Member) -> None:
        config = await self._get_guild_config(member.guild.id)
        if str(member.id) in {str(user_id) for user_id in config.get("notified_users", [])}:
            config["notified_users"].remove(str(member.id))
            await self._save_guild_config(member.guild.id, config)
            self._notified.setdefault(str(member.guild.id), set()).discard(str(member.id))
        await self._handle_member(member)

    @commands.hybrid_group(name="vanitystatus", aliases=["vanity"], invoke_without_command=True, description=f"Configure {get_bot_name()} vanity status rewards.")
    async def vanitystatus(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            prefix = ctx.prefix if ctx.prefix and ctx.prefix != f"<@!{self.bot.user.id}>" else f"@{self.bot.user.name} "
            embed = discord.Embed(
                title="VanityStatus",
                description=(
                    "Reward members with roles when they feature the configured keyword in their custom Discord status.\n\n"
                    f"`{prefix}vanitystatus keyword <text>`\n"
                    f"`{prefix}vanitystatus addrole <role>`\n"
                    f"`{prefix}vanitystatus removerole <role>`\n"
                    f"`{prefix}vanitystatus addchannel <channel>`\n"
                    f"`{prefix}vanitystatus removerole <channel>`\n"
                    f"`{prefix}vanitystatus message [text]`\n"
                    f"`{prefix}vanitystatus check [member]`"
                ),
                color=self.color,
            )
            await ctx.send(embed=embed)

    @vanitystatus.command(name="keyword", description="Set the keyword members must feature in their custom status.")
    @app_commands.describe(keyword="Required custom status keyword")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_keyword(self, ctx: commands.Context, *, keyword: str):
        keyword = keyword.strip()
        if not keyword:
            embed = discord.Embed(description=f"{error} | Keyword cannot be empty.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        config = await self._get_guild_config(ctx.guild.id)
        config["keyword"] = keyword
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | Vanity keyword set to `{keyword}`.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="addrole", aliases=["roleadd"], description="Add a reward role for matching vanity statuses.")
    @app_commands.describe(role="Role to award")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_addrole(self, ctx: commands.Context, role: discord.Role):
        config = await self._get_guild_config(ctx.guild.id)
        role_ids = [int(role_id) for role_id in config.get("reward_roles", [])]
        if role.id in role_ids:
            embed = discord.Embed(description=f"{error} | {role.mention} is already a vanity reward role.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        role_ids.append(role.id)
        config["reward_roles"] = role_ids
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | {role.mention} is now a vanity reward role.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="removerole", aliases=["roleremove"], description="Remove a vanity reward role.")
    @app_commands.describe(role="Role to remove")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_removerole(self, ctx: commands.Context, role: discord.Role):
        config = await self._get_guild_config(ctx.guild.id)
        role_ids = [int(role_id) for role_id in config.get("reward_roles", [])]
        if role.id not in role_ids:
            embed = discord.Embed(description=f"{error} | {role.mention} is not a vanity reward role.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        role_ids.remove(role.id)
        config["reward_roles"] = role_ids
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | {role.mention} was removed from vanity rewards.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="addchannel", aliases=["channeladd"], description="Add a channel for vanity milestone notifications.")
    @app_commands.describe(channel="Notification channel")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_addchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        config = await self._get_guild_config(ctx.guild.id)
        channel_ids = [int(channel_id) for channel_id in config.get("channels", [])]
        if channel.id in channel_ids:
            embed = discord.Embed(description=f"{error} | {channel.mention} is already a vanity notification channel.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        channel_ids.append(channel.id)
        config["channels"] = channel_ids
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | {channel.mention} will receive vanity milestone notifications.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="removechannel", aliases=["channelremove"], description="Remove a vanity milestone notification channel.")
    @app_commands.describe(channel="Channel to remove")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_removechannel(self, ctx: commands.Context, channel: discord.TextChannel):
        config = await self._get_guild_config(ctx.guild.id)
        channel_ids = [int(channel_id) for channel_id in config.get("channels", [])]
        if channel.id not in channel_ids:
            embed = discord.Embed(description=f"{error} | {channel.mention} is not a vanity notification channel.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        channel_ids.remove(channel.id)
        config["channels"] = channel_ids
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | {channel.mention} was removed from vanity notifications.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="message", description="Set the vanity milestone notification message.")
    @app_commands.describe(message="Message template")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_message(self, ctx: commands.Context, *, message: Optional[str] = None):
        config = await self._get_guild_config(ctx.guild.id)
        config["message"] = message.strip() if message and message.strip() else DEFAULT_MESSAGE
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | Vanity milestone message updated.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="blacklist-user-add", aliases=["blacklistuseradd"], description="Blacklist a user from vanity rewards.")
    @app_commands.describe(user="User to blacklist")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_blacklist_user_add(self, ctx: commands.Context, user: discord.Member):
        config = await self._get_guild_config(ctx.guild.id)
        users = [int(user_id) for user_id in config["blacklist"].get("users", [])]
        if user.id in users:
            embed = discord.Embed(description=f"{error} | {user.mention} is already blacklisted.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        users.append(user.id)
        config["blacklist"]["users"] = users
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | {user.mention} was added to the vanity blacklist.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="blacklist-user-remove", aliases=["blacklistuserremove"], description="Remove a user from the vanity blacklist.")
    @app_commands.describe(user="User to unblacklist")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_blacklist_user_remove(self, ctx: commands.Context, user: discord.Member):
        config = await self._get_guild_config(ctx.guild.id)
        users = [int(user_id) for user_id in config["blacklist"].get("users", [])]
        if user.id not in users:
            embed = discord.Embed(description=f"{error} | {user.mention} is not blacklisted.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        users.remove(user.id)
        config["blacklist"]["users"] = users
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | {user.mention} was removed from the vanity blacklist.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="blacklist-role-add", aliases=["blacklistroleadd"], description="Blacklist a role from vanity rewards.")
    @app_commands.describe(role="Role to blacklist")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_blacklist_role_add(self, ctx: commands.Context, role: discord.Role):
        config = await self._get_guild_config(ctx.guild.id)
        roles = [int(role_id) for role_id in config["blacklist"].get("roles", [])]
        if role.id in roles:
            embed = discord.Embed(description=f"{error} | {role.mention} is already blacklisted.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        roles.append(role.id)
        config["blacklist"]["roles"] = roles
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | {role.mention} was added to the vanity blacklist.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="blacklist-role-remove", aliases=["blacklistroleremove"], description="Remove a role from the vanity blacklist.")
    @app_commands.describe(role="Role to unblacklist")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_blacklist_role_remove(self, ctx: commands.Context, role: discord.Role):
        config = await self._get_guild_config(ctx.guild.id)
        roles = [int(role_id) for role_id in config["blacklist"].get("roles", [])]
        if role.id not in roles:
            embed = discord.Embed(description=f"{error} | {role.mention} is not blacklisted.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        roles.remove(role.id)
        config["blacklist"]["roles"] = roles
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | {role.mention} was removed from the vanity blacklist.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="blacklist-text-add", aliases=["blacklisttextadd"], description="Blacklist a status text substring.")
    @app_commands.describe(text="Text substring to blacklist")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_blacklist_text_add(self, ctx: commands.Context, *, text: str):
        text = text.strip()
        if not text:
            embed = discord.Embed(description=f"{error} | Blacklisted text cannot be empty.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        config = await self._get_guild_config(ctx.guild.id)
        texts = config["blacklist"].setdefault("text", [])
        if text.lower() in {str(item).lower() for item in texts}:
            embed = discord.Embed(description=f"{error} | `{text}` is already blacklisted.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        texts.append(text)
        await self._save_guild_config(ctx.guild.id, config)
        embed = discord.Embed(description=f"{GreenTick2} | `{text}` was added to the vanity text blacklist.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="blacklist-text-remove", aliases=["blacklisttextremove"], description="Remove a blacklisted status text substring.")
    @app_commands.describe(text="Text substring to unblacklist")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_blacklist_text_remove(self, ctx: commands.Context, *, text: str):
        text = text.strip()
        if not text:
            embed = discord.Embed(description=f"{error} | Blacklisted text cannot be empty.", color=discord.Color.red())
            return await ctx.reply(embed=embed, ephemeral=True)
        config = await self._get_guild_config(ctx.guild.id)
        texts = config["blacklist"].setdefault("text", [])
        lowered = text.lower()
        for item in texts:
            if str(item).lower() == lowered:
                texts.remove(item)
                await self._save_guild_config(ctx.guild.id, config)
                embed = discord.Embed(description=f"{GreenTick2} | `{text}` was removed from the vanity text blacklist.", color=self.color)
                return await ctx.reply(embed=embed)
        embed = discord.Embed(description=f"{error} | `{text}` is not blacklisted.", color=discord.Color.red())
        await ctx.reply(embed=embed, ephemeral=True)

    @vanitystatus.command(name="reset", description="Reset all vanity status configuration for this server.")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_reset(self, ctx: commands.Context):
        await self._save_guild_config(ctx.guild.id, self._default_config())
        self._notified.pop(str(ctx.guild.id), None)
        embed = discord.Embed(description=f"{GreenTick2} | VanityStatus configuration was reset.", color=self.color)
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="status", description="Show the current vanity status configuration.")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_guild=True)
    async def vanitystatus_status(self, ctx: commands.Context):
        config = await self._get_guild_config(ctx.guild.id)
        role_ids = [int(role_id) for role_id in config.get("reward_roles", [])]
        channel_ids = [int(channel_id) for channel_id in config.get("channels", [])]
        blacklist = config.get("blacklist", {})

        def format_roles(role_ids: list[int]) -> str:
            if not role_ids:
                return "None"
            return "\n".join((ctx.guild.get_role(role_id) or f"<@&{role_id}>").mention for role_id in role_ids)

        def format_channels(channel_ids: list[int]) -> str:
            if not channel_ids:
                return "None"
            return "\n".join(self.bot.get_channel(channel_id).mention if self.bot.get_channel(channel_id) else f"<#{channel_id}>" for channel_id in channel_ids)

        embed = discord.Embed(title="VanityStatus Configuration", color=self.color)
        embed.add_field(name="Keyword", value=f"`{config.get('keyword', '')}`", inline=False)
        embed.add_field(name="Reward Roles", value=format_roles(role_ids), inline=False)
        embed.add_field(name="Notification Channels", value=format_channels(channel_ids), inline=False)
        embed.add_field(name="Message", value=config.get("message", DEFAULT_MESSAGE), inline=False)
        embed.add_field(
            name="Blacklist",
            value=(
                f"Users: {len(blacklist.get('users', []))}\n"
                f"Roles: {len(blacklist.get('roles', []))}\n"
                f"Text: {len(blacklist.get('text', []))}"
            ),
            inline=False,
        )
        await ctx.reply(embed=embed)

    @vanitystatus.command(name="check", description="Manually check and apply vanity status rewards for a member.")
    @app_commands.describe(member="Member to check")
    @blacklist_check()
    @ignore_check()
    @commands.has_guild_permissions(manage_roles=True)
    async def vanitystatus_check(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        member = member or ctx.author
        await self._check_member_now(member)
        embed = discord.Embed(description=f"{GreenTick2} | Checked vanity status for {member.mention}.", color=self.color)
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_status = self._get_custom_status(before)
        after_status = self._get_custom_status(after)
        if before_status == after_status:
            return
        await self._handle_member(after)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._handle_member(member)


async def setup(bot: commands.Bot):
    await bot.add_cog(VanityStatus(bot))
