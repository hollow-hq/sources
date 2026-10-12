import discord
from discord.ext import commands
from core import Context
from datetime import datetime
from typing import Dict, List
from utils.config import OWNER_IDS
import json
import os
from utils.Tools import Config

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
ANTI_PATH = os.path.join(DATA_DIR, "anti.json")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def _get_guild_anti_data(guild_id):
    data = _read_json(ANTI_PATH)
    gid = str(guild_id)
    if gid not in data.get("guilds", {}):
        data.setdefault("guilds", {})[gid] = {"enabled": False, "modules": {}, "log_channel": None}
        _write_json(ANTI_PATH, data)
    return data

def _save_guild_anti_data(data):
    _write_json(ANTI_PATH, data)

def _get_guild_config_data(guild_id):
    data = _read_json(CONFIG_PATH)
    gid = str(guild_id)
    if gid not in data.get("guilds", {}):
        data.setdefault("guilds", {})[gid] = {"whitelisted": [], "admins": []}
        _write_json(CONFIG_PATH, data)
    return data

def _save_guild_config_data(data):
    _write_json(CONFIG_PATH, data)

class AntiNukeModule:
    def __init__(self, module: str, punishment: str, threshold: int, toggled: bool):
        self.module = module
        self.punishment = punishment
        self.threshold = threshold
        self.toggled = toggled

    @classmethod
    async def from_json(cls, guild_id: int, module: str):
        data = _get_guild_anti_data(guild_id)
        modules = data["guilds"][str(guild_id)].get("modules", {})
        mod = modules.get(module)
        if not mod:
            return None
        return cls(mod["module"], mod["punishment"], mod["threshold"], mod["toggled"])

    async def update(self, guild_id: int):
        data = _get_guild_anti_data(guild_id)
        data["guilds"][str(guild_id)]["modules"][self.module] = {
            "module": self.module,
            "punishment": self.punishment,
            "threshold": self.threshold,
            "toggled": self.toggled
        }
        _save_guild_anti_data(data)

class AntiNukeUser:
    def __init__(self, module: str, user_id: int, last_action: datetime, amount: int):
        self.module = module
        self.user_id = user_id
        self.last_action = last_action
        self.amount = amount

class AntiNukeEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.actions: Dict[int, List[AntiNukeUser]] = {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.bot:
            return

        data = _get_guild_anti_data(member.guild.id)
        if not data["guilds"][str(member.guild.id)].get("enabled"):
            return

        module = await AntiNukeModule.from_json(member.guild.id, "Bot")
        if not module or not module.toggled:
            return

        cfg = _get_guild_config_data(member.guild.id)
        admins = cfg["guilds"][str(member.guild.id)].get("admins", [])
        whitelisted = cfg["guilds"][str(member.guild.id)].get("whitelisted", [])

        if member.id in whitelisted or member.id in admins:
            return

        await member.ban(reason=f"{self.bot.user.name} Anti-Nuke: Protection (Anti-Bot)")

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        if entry.user is None or entry.user.id == entry.guild.me.id:
            return

        data = _get_guild_anti_data(entry.guild.id)
        if not data["guilds"][str(entry.guild.id)].get("enabled"):
            return

        if entry.action in [discord.AuditLogAction.ban, discord.AuditLogAction.unban]:
            module = await AntiNukeModule.from_json(entry.guild.id, "Ban")
            if module and module.toggled:
                await self.take_action(entry.guild.id, entry.user.id, entry.guild.owner.id, module)

        elif entry.action == discord.AuditLogAction.kick:
            module = await AntiNukeModule.from_json(entry.guild.id, "Kick")
            if module and module.toggled:
                await self.take_action(entry.guild.id, entry.user.id, entry.guild.owner.id, module)

        elif entry.action in [discord.AuditLogAction.channel_delete, discord.AuditLogAction.channel_update, discord.AuditLogAction.channel_create]:
            module = await AntiNukeModule.from_json(entry.guild.id, "Channels")
            if module and module.toggled:
                await self.take_action(entry.guild.id, entry.user.id, entry.guild.owner.id, module)

        elif entry.action in [discord.AuditLogAction.role_delete, discord.AuditLogAction.role_create]:
            module = await AntiNukeModule.from_json(entry.guild.id, "Roles")
            if module and module.toggled:
                await self.take_action(entry.guild.id, entry.user.id, entry.guild.owner.id, module)

        elif entry.action == discord.AuditLogAction.member_role_update:
            module = await AntiNukeModule.from_json(entry.guild.id, "Permissions")
            if not module or not module.toggled:
                return

            cfg = _get_guild_config_data(entry.guild.id)
            admins = cfg["guilds"][str(entry.guild.id)].get("admins", [])
            whitelisted = cfg["guilds"][str(entry.guild.id)].get("whitelisted", [])

            if entry.user.id in admins or entry.user.id in whitelisted or entry.user.id == entry.guild.owner.id:
                return

            for role in entry.after.roles:
                if role not in entry.before.roles and role.permissions.administrator:
                    await self.take_action(entry.guild.id, entry.user.id, entry.guild.owner.id, module)
                    await entry.target.remove_roles(role)
                    return

        elif entry.action in [discord.AuditLogAction.webhook_create, discord.AuditLogAction.webhook_delete]:
            module = await AntiNukeModule.from_json(entry.guild.id, "Webhook")
            if module and module.toggled:
                await self.take_action(entry.guild.id, entry.user.id, entry.guild.owner.id, module)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if before.vanity_url_code != after.vanity_url_code:
            data = _get_guild_anti_data(after.id)
            if not data["guilds"][str(after.id)].get("enabled"):
                return

            user = None
            async for entry in before.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
                user = entry.user

            if user:
                module = await AntiNukeModule.from_json(after.id, "Vanity")
                if module and module.toggled:
                    await self.take_action(after.id, user.id, after.owner.id, module)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        if message.mention_everyone:
            data = _get_guild_anti_data(message.guild.id)
            if not data["guilds"][str(message.guild.id)].get("enabled"):
                return

            module = await AntiNukeModule.from_json(message.guild.id, "Massmention")
            if module and module.toggled:
                cfg = _get_guild_config_data(message.guild.id)
                admins = cfg["guilds"][str(message.guild.id)].get("admins", [])
                whitelisted = cfg["guilds"][str(message.guild.id)].get("whitelisted", [])

                if message.author.id not in admins and message.author.id not in whitelisted and message.author.id != message.guild.owner.id:
                    await self.take_action(message.guild.id, message.author.id, message.guild.owner.id, module)
                    try:
                        await message.delete()
                    except:
                        pass

    async def take_action(self, guild_id: int, user_id: int, owner_id: int, module: AntiNukeModule):
        cfg = _get_guild_config_data(guild_id)
        admins = cfg["guilds"][str(guild_id)].get("admins", [])
        whitelisted = cfg["guilds"][str(guild_id)].get("whitelisted", [])

        if user_id in whitelisted or user_id in admins or user_id == self.bot.user.id or user_id == owner_id:
            return

        if guild_id not in self.actions:
            self.actions[guild_id] = [AntiNukeUser(module.module, user_id, datetime.now(), 1)]
            return

        found = False
        for action in self.actions[guild_id]:
            if action.user_id == user_id and action.module == module.module:
                found = True
                if (datetime.now() - action.last_action).total_seconds() > 60:
                    self.remove_action(guild_id, user_id, module.module)
                    action.amount = 1
                    self.actions[guild_id].append(AntiNukeUser(module.module, user_id, datetime.now(), 1))
                    return

                if action.amount >= module.threshold:
                    self.remove_action(guild_id, user_id, module.module)
                    await self.send_action(guild_id, user_id, module)
                    return

                action.amount += 1
                self.remove_action(guild_id, user_id, module.module)
                self.actions[guild_id].append(AntiNukeUser(module.module, user_id, datetime.now(), action.amount))
                return

        if not found:
            self.actions[guild_id].append(AntiNukeUser(module.module, user_id, datetime.now(), 1))

    async def send_action(self, guild_id: int, user_id: int, module: AntiNukeModule):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        user = await self.bot.fetch_user(user_id)
        if not user:
            return

        reason = f"{self.bot.user.name} Anti-Nuke: Protection {module.module} (Anti-{module.module})"

        if module.punishment.lower() == "ban":
            await guild.ban(user=user, reason=reason)
        elif module.punishment.lower() == "kick":
            await guild.kick(user=user, reason=reason)
        elif module.punishment.lower() == "warn":
            try:
                await user.send(f"{self.bot.user.name} Anti-Nuke: Protection {module.module} (Anti-{module.module})\n**You have been warned**, further actions will result in a punishment decided by relevant staff.")
            except:
                pass
        elif module.punishment.lower() == "strip":
            member = guild.get_member(user_id)
            if member:
                dangerous_roles = [
                    role for role in member.roles
                    if any([
                        role.permissions.administrator,
                        role.permissions.manage_channels,
                        role.permissions.manage_roles,
                        role.permissions.manage_webhooks,
                        role.permissions.mention_everyone,
                        role.permissions.manage_expressions,
                        role.permissions.moderate_members,
                        role.permissions.manage_messages,
                        role.permissions.manage_guild,
                        role.permissions.ban_members,
                        role.permissions.kick_members,
                        role.permissions.mute_members
                    ])
                ]
                if dangerous_roles:
                    await member.remove_roles(*dangerous_roles, reason=reason)

        log_embed = discord.Embed(
            title=f"Anti-Nuke: {module.module}",
            description=f"Action taken by {self.bot.user.name}",
            color=0xd3d6f1,
            timestamp=datetime.now()
        )
        log_embed.add_field(name="User", value=f"<@{user_id}>", inline=True)
        log_embed.add_field(name="Action", value=module.punishment, inline=True)
        log_embed.set_footer(text=f"{self.bot.user.name} Anti-Nuke", icon_url=self.bot.user.avatar.url)

        data = _get_guild_anti_data(guild_id)
        log_channel_id = data["guilds"][str(guild_id)].get("log_channel")

        if log_channel_id:
            channel = self.bot.get_channel(log_channel_id)
            if channel:
                try:
                    await channel.send(embed=log_embed)
                except:
                    pass

    def remove_action(self, guild_id: int, user_id: int, module: str):
        if guild_id not in self.actions:
            return

        for pos, action in enumerate(self.actions[guild_id]):
            if action.user_id == user_id and action.module == module:
                del self.actions[guild_id][pos]
                return

async def has_admin(ctx: Context) -> bool:
    if ctx.author.id in OWNER_IDS or ctx.author.id == ctx.guild.owner.id:
        return True
    cfg = _get_guild_config_data(ctx.guild.id)
    admins = cfg["guilds"][str(ctx.guild.id)].get("admins", [])
    if ctx.author.id not in admins:
        await ctx.send("You do not have **anti-nuke admin**")
        return False
    return True

async def is_enabled(ctx: Context) -> bool:
    data = _get_guild_anti_data(ctx.guild.id)
    if not data["guilds"][str(ctx.guild.id)].get("enabled"):
        await ctx.send("AntiNuke is not **enabled** in this server. Use `antinuke enable` to **enable** it.")
        return False
    return True

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.modules = ["Ban", "Kick", "Bot", "Roles", "Vanity", "Webhook", "Channels", "Permissions", "Massmention"]
        self.actions: Dict[int, List[AntiNukeUser]] = {}

    @commands.group(invoke_without_command=True, aliases=["an"])
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx: Context):
        if not await has_admin(ctx):
            return
        await ctx.send_help(ctx.command)

    @antinuke.command(aliases=["config"])
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx: Context):
        if not await has_admin(ctx) or not await is_enabled(ctx):
            return

        embed = discord.Embed(
            title=f"Anti-Nuke Settings - {ctx.guild.name}",
            color=Config.COLORS.DEFAULT
        )

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        for name in self.modules:
            module = await AntiNukeModule.from_json(ctx.guild.id, name)
            status = ctx.config.emojis.context.approve if module and module.toggled else ctx.config.emojis.context.deny
            embed.add_field(
                name=f"{name}: {status}",
                value=f"Action: `{module.punishment if module else 'None'}`\nThreshold: `{module.threshold if module else 'None'}`",
                inline=True
            )

        await ctx.send(embed=embed)

    @antinuke.command(aliases=["wl"])
    @commands.has_permissions(administrator=True)
    async def whitelist(self, ctx: Context, user: discord.User):
        if not await has_admin(ctx) or not await is_enabled(ctx):
            return

        cfg = _get_guild_config_data(ctx.guild.id)
        whitelisted = cfg["guilds"][str(ctx.guild.id)].get("whitelisted", [])

        if user.id in whitelisted:
            whitelisted.remove(user.id)
            cfg["guilds"][str(ctx.guild.id)]["whitelisted"] = whitelisted
            _save_guild_config_data(cfg)
            await ctx.send(f"**{user.name}** has been **unwhitelisted** in this server.")
        else:
            whitelisted.append(user.id)
            cfg["guilds"][str(ctx.guild.id)]["whitelisted"] = whitelisted
            _save_guild_config_data(cfg)
            await ctx.send(f"**{user.name}** has been **whitelisted** in this server.")

    @antinuke.command()
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx: Context, user: discord.User):
        if not await has_admin(ctx) or not await is_enabled(ctx):
            return

        cfg = _get_guild_config_data(ctx.guild.id)
        admins = cfg["guilds"][str(ctx.guild.id)].get("admins", [])

        if user.id in admins:
            admins.remove(user.id)
            cfg["guilds"][str(ctx.guild.id)]["admins"] = admins
            _save_guild_config_data(cfg)
            await ctx.send(f"**{user.name}** has been **removed** from the **Anti-Nuke Admin** list in this server.")
        else:
            admins.append(user.id)
            cfg["guilds"][str(ctx.guild.id)]["admins"] = admins
            _save_guild_config_data(cfg)
            await ctx.send(f"**{user.name}** has been **added** to the **Anti-Nuke Admin** list in this server.")

    @antinuke.command()
    @commands.has_permissions(administrator=True)
    async def whitelisted(self, ctx: Context):
        if not await has_admin(ctx):
            return

        cfg = _get_guild_config_data(ctx.guild.id)
        whitelisted = cfg["guilds"][str(ctx.guild.id)].get("whitelisted", [])

        if not whitelisted:
            return await ctx.send("No users are **whitelisted** in this server.")

        embed = discord.Embed(
            title=f"Anti-Nuke Whitelisted Members - {ctx.guild.name}",
            color=Config.COLORS.DEFAULT
        )

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        embed.description = "\n".join([
            f"{ctx.guild.get_member(user).name if ctx.guild.get_member(user) else 'Unknown'} ({user})"
            for user in whitelisted
        ])

        await ctx.send(embed=embed)

    @antinuke.command()
    @commands.has_permissions(administrator=True)
    async def admins(self, ctx: Context):
        if not await has_admin(ctx):
            return

        cfg = _get_guild_config_data(ctx.guild.id)
        admins = cfg["guilds"][str(ctx.guild.id)].get("admins", [])

        if not admins:
            return await ctx.send("No users are **Anti-Nuke Admins** in this server.")

        embed = discord.Embed(
            title=f"Anti-Nuke Admins - {ctx.guild.name}",
            color=Config.COLORS.DEFAULT
        )

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        embed.description = "\n".join([
            f"{ctx.guild.get_member(user).name if ctx.guild.get_member(user) else 'Unknown'} ({user})"
            for user in admins
        ])

        await ctx.send(embed=embed)

    @antinuke.command()
    @commands.has_permissions(administrator=True)
    async def enable(self, ctx: Context):
        if not await has_admin(ctx):
            return

        data = _get_guild_anti_data(ctx.guild.id)
        if data["guilds"][str(ctx.guild.id)].get("enabled"):
            return await ctx.send("AntiNuke is already **enabled** in this server.")

        data["guilds"][str(ctx.guild.id)]["enabled"] = True
        _save_guild_anti_data(data)

        modules = data["guilds"][str(ctx.guild.id)].get("modules", {})
        if not modules:
            for name in self.modules:
                modules[name] = {"module": name, "punishment": "ban", "threshold": 1, "toggled": False}
            data["guilds"][str(ctx.guild.id)]["modules"] = modules
            _save_guild_anti_data(data)

        await ctx.send("Anti-Nuke has been **enabled** in this server.")

    @antinuke.command()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx: Context):
        if not await has_admin(ctx) or not await is_enabled(ctx):
            return

        data = _get_guild_anti_data(ctx.guild.id)
        data["guilds"][str(ctx.guild.id)]["enabled"] = False
        _save_guild_anti_data(data)
        await ctx.send("Anti-Nuke has been **disabled** in this server.")

    @antinuke.command()
    @commands.has_permissions(administrator=True)
    async def toggle(self, ctx: Context, module: str):
        if not await has_admin(ctx) or not await is_enabled(ctx):
            return

        if module.capitalize() not in self.modules:
            return await ctx.send(f"The module `{module}` is not a valid **Anti-Nuke module**.")

        an_module = await AntiNukeModule.from_json(ctx.guild.id, module.capitalize())
        if not an_module:
            return await ctx.send("Module not found.")

        an_module.toggled = not an_module.toggled
        await an_module.update(ctx.guild.id)

        await ctx.send(f"Anti-Nuke module `{module}` has been **{'Enabled' if an_module.toggled else 'Disabled'}**.")

    @antinuke.command()
    @commands.has_permissions(administrator=True)
    async def threshold(self, ctx: Context, module: str, threshold: int):
        if not await has_admin(ctx) or not await is_enabled(ctx):
            return

        if module.capitalize() not in self.modules:
            return await ctx.send(f"The module `{module}` is not a valid **Anti-Nuke module**.")

        an_module = await AntiNukeModule.from_json(ctx.guild.id, module.capitalize())
        if not an_module:
            return await ctx.send("Module not found.")

        an_module.threshold = threshold
        await an_module.update(ctx.guild.id)

        await ctx.send(f"Anti-Nuke module `{module}` threshold has been set to `{threshold}`.")

    @antinuke.command(aliases=["punishment"])
    @commands.has_permissions(administrator=True)
    async def action(self, ctx: Context, module: str, action: str):
        if not await has_admin(ctx) or not await is_enabled(ctx):
            return

        if module.capitalize() not in self.modules:
            return await ctx.send(f"The module `{module}` is not a valid **Anti-Nuke module**.")

        if action.lower() not in ["ban", "warn", "kick", "strip"]:
            return await ctx.send(f"The action `{action}` is not a valid action. Use `ban`, `warn`, `kick` or `strip`.")

        an_module = await AntiNukeModule.from_json(ctx.guild.id, module.capitalize())
        if not an_module:
            return await ctx.send("Module not found.")

        an_module.punishment = action.lower()
        await an_module.update(ctx.guild.id)

        await ctx.send(f"Anti-Nuke module `{module}` action has been set to `{action}`.")

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
    await bot.add_cog(AntiNukeEvents(bot))
