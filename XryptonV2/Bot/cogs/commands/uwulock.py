import discord
import json
import os
import re
from discord.ext import commands
from discord import app_commands
from typing import Union, Optional, List
from uwuipy import uwuipy
from utils.Tools import blacklist_check, ignore_check
from utils.constants import GreenTick2, error

CONFIG_PATH = "data/uwulock_config.json"

class UwuLock(commands.Cog, name="UwuLock"):
    """🐱 Forced text translation and filtering for specific targets."""

    def __init__(self, bot):
        self.bot = bot
        self.uwu = uwuipy(None)
        self.color = 0x4862DE
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "w") as f:
                json.dump({}, f)

    def _load_config(self) -> dict:
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self, config: dict):
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
    def _get_guild_config(self, guild_id: str) -> dict:
        config = self._load_config()
        if guild_id not in config:
            config[guild_id] = {
                "enabled": False,
                "locked_targets": [],
                "whitelist": [],
                "block_links": False,
                "links_whitelist": [],
                "block_invites": False,
                "invites_whitelist": []
            }
            self._save_config(config)
        return config[guild_id]

    def _update_guild_config(self, guild_id: str, data: dict):
        config = self._load_config()
        config[guild_id] = data
        self._save_config(config)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.webhook_id or not message.guild:
            return

        gid = str(message.guild.id)
        config = self._get_guild_config(gid)
        
        if not config["enabled"]:
            return

        author = message.author
        locked_targets = config["locked_targets"]
        whitelist = config["whitelist"]

        # Check if user or any of their roles are targets
        is_locked = author.id in locked_targets or any(r.id in locked_targets for r in author.roles)
        # Check if user or any of their roles are whitelisted
        is_whitelisted = author.id in whitelist or any(r.id in whitelist for r in author.roles)

        if not is_locked or is_whitelisted:
            return

        # Filtering Logic
        content = message.content
        
        # Link Filtering
        if config["block_links"]:
            if re.search(r'https?://\S+', content):
                lwl = config["links_whitelist"]
                if not (author.id in lwl or any(r.id in lwl for r in author.roles)):
                    try:
                        await message.delete()
                        return await message.channel.send(f"{author.mention}, you aren't allowed to send links while UwuLocked.", delete_after=3)
                    except: pass

        # Invite Filtering
        if config["block_invites"]:
            if re.search(r'(discord\.gg/|discord\.com/invite/)\S+', content):
                iwl = config["invites_whitelist"]
                if not (author.id in iwl or any(r.id in iwl for r in author.roles)):
                    try:
                        await message.delete()
                        return await message.channel.send(f"{author.mention}, you aren't allowed to send invites while UwuLocked.", delete_after=3)
                    except: pass

        # Webhook Mirroring Logic
        try:
            # Prepare translation
            translated = self.uwu.uwuify(content) if content else ""
            
            # Fetch/Create Webhook
            webhooks = await message.channel.webhooks()
            webhook = discord.utils.get(webhooks, name=f"{self.bot.user.name}-UwuLock")
            if not webhook:
                webhook = await message.channel.create_webhook(name=f"{self.bot.user.name}-UwuLock", reason=f"{self.bot.user.name} UwuLock mirroring")

            # Handle Attachments
            files = []
            for attachment in message.attachments:
                files.append(await attachment.to_file())

            # Delete original first to prevent double message appearance
            try: await message.delete()
            except: pass

            await webhook.send(
                content=translated,
                username=author.display_name,
                avatar_url=author.display_avatar.url,
                files=files
            )
        except Exception as e:
            print(f"UwuLock Webhook Error: {e}")

    @commands.hybrid_group(name="uwulock", description="UwuLock specific users or roles.", invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    @blacklist_check()
    @ignore_check()
    async def uwulock_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @uwulock_group.command(name="config", description="View the current UwuLock setup.")
    async def uwulock_config(self, ctx: commands.Context):
        config = self._get_guild_config(str(ctx.guild.id))
        embed = discord.Embed(title=f"UwuLock Config — {ctx.guild.name}", color=self.color)
        embed.add_field(name="System Status", value="✅ Enabled" if config["enabled"] else "❌ Disabled", inline=False)
        embed.add_field(name="Link Blocking", value="🚫 Active" if config["block_links"] else "🔓 Inactive", inline=True)
        embed.add_field(name="Invite Blocking", value="🚫 Active" if config["block_invites"] else "🔓 Inactive", inline=True)
        embed.add_field(name="Statistics", value=f"Targets: `{len(config['locked_targets'])}` | Whitelist: `{len(config['whitelist'])}`", inline=False)
        await ctx.send(embed=embed)

    @uwulock_group.command(name="enable", description="Globally turn on the UwuLock system.")
    async def uwulock_enable(self, ctx: commands.Context):
        config = self._get_guild_config(str(ctx.guild.id))
        config["enabled"] = True
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | UwuLock has been enabled.", color=self.color))

    @uwulock_group.command(name="disable", description="Globally turn off the UwuLock system.")
    async def uwulock_disable(self, ctx: commands.Context):
        config = self._get_guild_config(str(ctx.guild.id))
        config["enabled"] = False
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | UwuLock has been disabled.", color=self.color))

    @uwulock_group.command(name="add", description="Add a user or role to locked targets.")
    @app_commands.describe(target="The user or role to lock")
    async def uwulock_add(self, ctx: commands.Context, target: Union[discord.Member, discord.Role]):
        config = self._get_guild_config(str(ctx.guild.id))
        if target.id in config["locked_targets"]:
            return await ctx.send(embed=discord.Embed(description=f"{error} | That target is already locked.", color=discord.Color.red()))
        config["locked_targets"].append(target.id)
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | Successfully locked {target.mention}.", color=self.color))

    @uwulock_group.command(name="remove", description="Remove a user or role from targets.")
    async def uwulock_remove(self, ctx: commands.Context, target: Union[discord.Member, discord.Role]):
        config = self._get_guild_config(str(ctx.guild.id))
        if target.id not in config["locked_targets"]:
            return await ctx.send(embed=discord.Embed(description=f"{error} | That target is not locked.", color=discord.Color.red()))
        config["locked_targets"].remove(target.id)
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | Successfully unlocked {target.mention}.", color=self.color))

    @uwulock_group.command(name="list_locked", description="List all currently locked targets.")
    async def uwulock_list(self, ctx: commands.Context):
        config = self._get_guild_config(str(ctx.guild.id))
        targets = [f"<@{t}>" if ctx.guild.get_member(t) else f"<@&{t}>" for t in config["locked_targets"]]
        desc = "\n".join(targets) if targets else "No targets currently locked."
        embed = discord.Embed(title="Locked Targets", description=desc, color=self.color)
        await ctx.send(embed=embed)

    # Sub-group: Whitelist
    @uwulock_group.group(name="whitelist", description="Manage global UwuLock bypasses.", invoke_without_command=True)
    async def whitelist_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @whitelist_group.command(name="add", description="Whitelisted targets will never be uwu-translated.")
    async def wl_add(self, ctx: commands.Context, target: Union[discord.Member, discord.Role]):
        config = self._get_guild_config(str(ctx.guild.id))
        if target.id in config["whitelist"]: return await ctx.send("Already whitelisted.")
        config["whitelist"].append(target.id)
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send(f"Whitelisted {target.name}.")

    @whitelist_group.command(name="remove", description="Remove from global whitelist.")
    async def wl_remove(self, ctx: commands.Context, target: Union[discord.Member, discord.Role]):
        config = self._get_guild_config(str(ctx.guild.id))
        if target.id in config["whitelist"]:
            config["whitelist"].remove(target.id)
            self._update_guild_config(str(ctx.guild.id), config)
            await ctx.send(f"Removed {target.name} from whitelist.")

    @whitelist_group.command(name="list_whitelisted", description="List all whitelisted targets.")
    async def wl_list(self, ctx: commands.Context):
        config = self._get_guild_config(str(ctx.guild.id))
        data = "\n".join([f"<@{i}>" for i in config["whitelist"]]) or "None"
        await ctx.send(embed=discord.Embed(title="Global Whitelist", description=data, color=self.color))

    # Sub-group: Links
    @uwulock_group.group(name="links", description="Manage link blocking for locked targets.", invoke_without_command=True)
    async def links_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @links_group.command(name="enable")
    async def ln_enable(self, ctx):
        config = self._get_guild_config(str(ctx.guild.id))
        config["block_links"] = True
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send("Link blocking enabled for locked targets.")

    @links_group.command(name="disable")
    async def ln_disable(self, ctx):
        config = self._get_guild_config(str(ctx.guild.id))
        config["block_links"] = False
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send("Link blocking disabled.")

    @links_group.command(name="whitelist")
    async def ln_wl(self, ctx, target: Union[discord.Member, discord.Role]):
        config = self._get_guild_config(str(ctx.guild.id))
        config["links_whitelist"].append(target.id)
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send(f"{target.name} can now send links.")

    # Sub-group: Invites
    @uwulock_group.group(name="invites", description="Manage invite blocking for locked targets.", invoke_without_command=True)
    async def invites_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @invites_group.command(name="enable")
    async def inv_enable(self, ctx):
        config = self._get_guild_config(str(ctx.guild.id))
        config["block_invites"] = True
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send("Invite blocking enabled.")

    @invites_group.command(name="disable")
    async def inv_disable(self, ctx):
        config = self._get_guild_config(str(ctx.guild.id))
        config["block_invites"] = False
        self._update_guild_config(str(ctx.guild.id), config)
        await ctx.send("Invite blocking disabled.")

async def setup(bot):
    await bot.add_cog(UwuLock(bot))
