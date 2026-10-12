import json
import os
import time
import asyncio
from typing import Optional

import discord
from discord.ext import commands, tasks
from discord import app_commands


DISBOARD_BOT_ID = 302050872383242240
BUMP_INTERVAL = 7200
CLEAN_DELAY = 5
CHECK_INTERVAL = 15


def get_json_path() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "data/bumpreminder.json")


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


async def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        content = await asyncio.to_thread(_read_file, path)
        return json.loads(content)
    except (json.JSONDecodeError, Exception):
        return {}


async def save_json(path: str, data: dict) -> None:
    content = json.dumps(data, indent=2)
    await asyncio.to_thread(_write_file, path, content)


class BumpReminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.json_path = get_json_path()
        self._lock = asyncio.Lock()

    async def cog_load(self) -> None:
        await self.init_json()
        self._reminder_loop.start()

    async def cog_unload(self) -> None:
        self._reminder_loop.cancel()

    async def init_json(self) -> None:
        if not os.path.exists(self.json_path):
            await save_json(self.json_path, {})

    async def _data_get(self) -> dict:
        async with self._lock:
            return await load_json(self.json_path)

    async def _data_save(self, data: dict) -> None:
        async with self._lock:
            await save_json(self.json_path, data)

    def _default_config(self) -> dict:
        return {
            "reminder_channel_id": None,
            "thankyou_script": "Thanks for bumping our server, {user}! Keep it up!",
            "reminder_script": "Hey @everyone! It's time to bump our server using `/bump`! 🎉",
            "autoclean": False,
            "autolock": False,
            "next_bump_time": 0,
            "reminder_sent": True,
        }

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def _reminder_loop(self) -> None:
        try:
            data = await self._data_get()
            if not data:
                return
            now = time.time()
            updated = False
            for guild_id, config in data.items():
                if not config.get("reminder_sent", True):
                    next_time = config.get("next_bump_time", 0)
                    if now >= next_time:
                        await self._fire_reminder(str(guild_id), config)
                        config["reminder_sent"] = True
                        updated = True
            if updated:
                await self._data_save(data)
        except Exception:
            pass

    @_reminder_loop.before_loop
    async def _before_reminder_loop(self) -> None:
        await self.bot.wait_until_ready()
        await self.init_json()

    async def _fire_reminder(self, guild_id_str: str, config: dict) -> None:
        channel_id = config.get("reminder_channel_id")
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            script = config.get("reminder_script", "")
            await channel.send(script)
        except (discord.Forbidden, discord.HTTPException):
            return

        autolock = config.get("autolock", False)
        if autolock:
            try:
                if channel.guild:
                    everyone_role = channel.guild.default_role
                    if everyone_role.position < channel.guild.me.top_role.position:
                        overwrites = channel.overwrites_for(everyone_role)
                        overwrites.send_messages = True
                        await channel.set_permissions(everyone_role, overwrite=overwrites)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if message.author.id != DISBOARD_BOT_ID:
            return
        if not message.embeds:
            return

        success = False
        for embed in message.embeds:
            title = embed.title or ""
            description = embed.description or ""
            combined = (title + description).lower()
            if any(marker in combined for marker in ("bump done!", "page public")):
                success = True
                break

        if not success:
            return

        guild_id_str = str(message.guild.id)
        data = await self._data_get()
        config = data.setdefault(guild_id_str, self._default_config())

        config["next_bump_time"] = int(time.time()) + BUMP_INTERVAL
        config["reminder_sent"] = False
        await self._data_save(data)

        channel = message.channel
        script = config.get("thankyou_script", "")
        user_mention = ""
        if message.interaction and getattr(message.interaction, "user", None):
            user_mention = message.interaction.user.mention
        script = script.replace("{user}", user_mention)
        try:
            await channel.send(script)
        except discord.Forbidden:
            return

        if config.get("autoclean", False):
            await asyncio.sleep(CLEAN_DELAY)
            try:
                await message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

        if config.get("autolock", False):
            try:
                if channel.guild:
                    everyone_role = channel.guild.default_role
                    if everyone_role.position < channel.guild.me.top_role.position:
                        overwrites = channel.overwrites_for(everyone_role)
                        overwrites.send_messages = False
                        await channel.set_permissions(everyone_role, overwrite=overwrites)
            except discord.Forbidden:
                pass

    @commands.hybrid_group(
        name="bumpreminder",
        description="Manage Disboard bump reminders",
        invoke_without_command=True,
    )
    async def bumpreminder(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Xrypton Bump Reminder",
            description="Automate Disboard bump tracking, thank-yous, and channel locks.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="`channel`", value="Set the monitoring/reminder channel.", inline=False)
        embed.add_field(name="`message`", value="Set the reminder script sent after 2 hours.", inline=False)
        embed.add_field(name="`thankyou`", value="Set the thank-you script after a bump.", inline=False)
        embed.add_field(name="`autoclean`", value="Toggle auto-deletion of Disboard bump messages.", inline=False)
        embed.add_field(name="`autolock`", value="Toggle auto-locking after a bump.", inline=False)
        embed.add_field(name="`config`", value="View current configuration dashboard.", inline=False)
        embed.add_field(name="`test`", value="Run a mock bump routine.", inline=False)
        await ctx.send(embed=embed)

    @bumpreminder.command(name="channel", description="Set the target channel for bump tracking")
    @commands.has_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
        guild_id_str = str(ctx.guild.id)
        data = await self._data_get()
        config = data.setdefault(guild_id_str, self._default_config())
        target = channel or getattr(ctx, "channel", None)
        if not isinstance(target, discord.TextChannel):
            await ctx.reply("Provide a valid text channel or run this command in a text channel.", ephemeral=True)
            return
        config["reminder_channel_id"] = target.id
        await self._data_save(data)
        await ctx.reply(f"Bump reminder channel set to {target.mention}.", ephemeral=True)

    @bumpreminder.command(name="message", description="Configure the reminder script sent after 2 hours")
    @commands.has_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_message(self, ctx: commands.Context, *, text: str) -> None:
        guild_id_str = str(ctx.guild.id)
        data = await self._data_get()
        config = data.setdefault(guild_id_str, self._default_config())
        config["reminder_script"] = text
        await self._data_save(data)
        await ctx.reply("Reminder script updated.", ephemeral=True)

    @bumpreminder.command(name="thankyou", description="Configure the thank-you script sent after a bump")
    @commands.has_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_thankyou(self, ctx: commands.Context, *, text: str) -> None:
        guild_id_str = str(ctx.guild.id)
        data = await self._data_get()
        config = data.setdefault(guild_id_str, self._default_config())
        config["thankyou_script"] = text
        await self._data_save(data)
        await ctx.reply("Thank-you script updated.", ephemeral=True)

    @bumpreminder.command(name="autoclean", description="Toggle auto-deletion of Disboard bump messages")
    @commands.has_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle_autoclean(self, ctx: commands.Context) -> None:
        guild_id_str = str(ctx.guild.id)
        data = await self._data_get()
        config = data.setdefault(guild_id_str, self._default_config())
        config["autoclean"] = not config.get("autoclean", False)
        await self._data_save(data)
        state = "ON" if config["autoclean"] else "OFF"
        await ctx.reply(f"Autoclean is now {state}.", ephemeral=True)

    @bumpreminder.command(name="autolock", description="Toggle auto-locking the channel after a bump")
    @commands.has_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle_autolock(self, ctx: commands.Context) -> None:
        guild_id_str = str(ctx.guild.id)
        data = await self._data_get()
        config = data.setdefault(guild_id_str, self._default_config())
        config["autolock"] = not config.get("autolock", False)
        await self._data_save(data)
        state = "ON" if config["autolock"] else "OFF"
        await ctx.reply(f"Autolock is now {state}.", ephemeral=True)

    @bumpreminder.command(name="config", description="View current bump reminder settings")
    @commands.has_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_config(self, ctx: commands.Context) -> None:
        guild_id_str = str(ctx.guild.id)
        data = await self._data_get()
        if guild_id_str not in data:
            await ctx.reply("No configuration found. Use `.bumpreminder channel` to set up.", ephemeral=True)
            return
        config = data[guild_id_str]
        channel = self.bot.get_channel(config.get("reminder_channel_id"))
        channel_mention = channel.mention if isinstance(channel, discord.TextChannel) else "Not set"
        next_time = config.get("next_bump_time", 0)
        countdown = max(0, next_time - time.time())
        hours, remainder = divmod(int(countdown), 3600)
        minutes, seconds = divmod(remainder, 60)
        countdown_str = f"{hours}h {minutes}m {seconds}s" if next_time else "N/A"
        reminder_sent = config.get("reminder_sent", True)

        embed = discord.Embed(
            title="Bump Reminder Configuration",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Reminder Channel", value=channel_mention, inline=False)
        embed.add_field(name="Thank-You Script", value=config.get("thankyou_script", "") or "*empty*", inline=False)
        embed.add_field(name="Reminder Script", value=config.get("reminder_script", "") or "*empty*", inline=False)
        embed.add_field(name="Autoclean", value="ON" if config.get("autoclean", False) else "OFF", inline=True)
        embed.add_field(name="Autolock", value="ON" if config.get("autolock", False) else "OFF", inline=True)
        embed.add_field(name="Next Bump Time", value=countdown_str, inline=True)
        embed.add_field(name="Reminder Sent", value="Yes" if reminder_sent else "No", inline=True)
        await ctx.send(embed=embed)

    @bumpreminder.command(name="test", description="Run a mock bump routine to test settings")
    @commands.has_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_bump(self, ctx: commands.Context) -> None:
        guild_id_str = str(ctx.guild.id)
        data = await self._data_get()
        if guild_id_str not in data:
            await ctx.reply("No configuration found. Set up a channel first.", ephemeral=True)
            return
        config = data[guild_id_str]
        channel_id = config.get("reminder_channel_id")
        if not channel_id:
            await ctx.reply("No reminder channel configured.", ephemeral=True)
            return
        target_channel = self.bot.get_channel(channel_id)
        if not isinstance(target_channel, discord.TextChannel):
            await ctx.reply("Reminder channel is invalid or inaccessible.", ephemeral=True)
            return

        script = config.get("thankyou_script", "")
        script = script.replace("{user}", ctx.author.mention)
        sent_msg = await target_channel.send(script)

        autoclean = config.get("autoclean", False)
        autolock = config.get("autolock", False)

        if autoclean:
            await asyncio.sleep(CLEAN_DELAY)
            try:
                await sent_msg.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

        if autolock:
            try:
                everyone_role = target_channel.guild.default_role
                if everyone_role.position < target_channel.guild.me.top_role.position:
                    overwrites = target_channel.overwrites_for(everyone_role)
                    overwrites.send_messages = False
                    await target_channel.set_permissions(everyone_role, overwrite=overwrites)
            except discord.Forbidden:
                pass
            await asyncio.sleep(10)
            try:
                everyone_role = target_channel.guild.default_role
                overwrites = target_channel.overwrites_for(everyone_role)
                overwrites.send_messages = True
                await target_channel.set_permissions(everyone_role, overwrite=overwrites)
            except discord.Forbidden:
                pass

        await ctx.reply("Mock bump routine completed. Check the configured channel for results.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BumpReminder(bot))
