import discord
import json
import traceback
from discord.ext import commands
from typing import Union, Optional
from core import Astroz, Cog, Context
from utils.Tools import getIgnore
from utils.constants import lnl_error

class Errors(Cog):
    def __init__(self, client: Astroz):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        # Handle errors that occur during command execution
        
        # 1. Ignore Command Not Found
        if isinstance(error, commands.CommandNotFound):
            return

        if getattr(ctx, "_honeypot_error_handled", False) or (ctx.command is not None and ctx.command.qualified_name.startswith("antiscam")):
            return

        # 2. Blacklist and Ignore Checks
        try:
            with open('data/blacklist.json', 'r') as f:
                blacklist_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            blacklist_data = {"ids": []}

        if str(ctx.author.id) in blacklist_data.get("ids", []):
            return

        # 3. Handle specific error types
        if isinstance(error, commands.MissingRequiredArgument):
            try:
                help_cog = ctx.bot.get_cog("Help")
                if help_cog:
                    ctx.command.reset_cooldown(ctx)
                    return await help_cog.help_command.send_missing_argument_help(ctx.command, error.param.name)
            except Exception:
                pass
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)
            return

        if isinstance(error, commands.CheckFailure):
            data1 = getIgnore(ctx.guild.id)
            ignored_channels = data1.get("channel", [])
            ignored_users = data1.get("user", [])
            
            if str(ctx.channel.id) in ignored_channels:
                embed = discord.Embed(description="This Channel is in the ignored channel list. Try my commands in another channel.", color=0x2f3136)
                return await ctx.reply(embed=embed, delete_after=8)
                
            if str(ctx.author.id) in ignored_users:
                ign = discord.Embed(description=f"You are set as an ignored user for {ctx.guild.name}. Try my commands in another guild.", color=0x2f3136)
                return await ctx.reply(embed=ign, delete_after=8)
            return

        if isinstance(error, commands.NoPrivateMessage):
            embed = discord.Embed(color=0x2f3136, description="You can't use my commands in DMs.")
            icon = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            embed.set_author(name=ctx.author, icon_url=icon)
            embed.set_thumbnail(url=icon)
            return await ctx.reply(embed=embed, delete_after=20)

        if isinstance(error, commands.TooManyArguments):
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)
            return

        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(color=0x2f3136, description=f"{lnl_error} | {ctx.author.name} is on cooldown. Retry after {error.retry_after:.2f} second(s).")
            icon = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            embed.set_author(name=str(ctx.author), icon_url=icon)
            embed.set_thumbnail(url=icon)
            return await ctx.reply(embed=embed, delete_after=10)

        if isinstance(error, commands.MaxConcurrencyReached):
            embed = discord.Embed(color=0x2f3136, description=f"{lnl_error} | This command is already running. Let it finish and retry.")
            icon = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            embed.set_author(name=ctx.author, icon_url=icon)
            embed.set_thumbnail(url=icon)
            ctx.command.reset_cooldown(ctx)
            return await ctx.reply(embed=embed, delete_after=10)

        if isinstance(error, commands.MissingPermissions):
            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_permissions]
            fmt = "{}, and {}".format(", ".join(missing[:-1]), missing[-1]) if len(missing) > 2 else " and ".join(missing)
            embed = discord.Embed(color=0x2f3136, description=f"{lnl_error} | You lack `{fmt}` permission(s) to run the `{ctx.command.name}` command!")
            icon = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            embed.set_author(name=ctx.author, icon_url=icon)
            embed.set_thumbnail(url=icon)
            ctx.command.reset_cooldown(ctx)
            return await ctx.reply(embed=embed, delete_after=6)

        if isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(error.missing_perms)
            return await ctx.send(f'| I need the **{missing}** permissions to run the **{ctx.command.name}** command!', delete_after=10)

        if isinstance(error, commands.BadArgument):
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)
            return

        # 4. Final Fallbacks and Logging
        if isinstance(error, discord.HTTPException):
            return
            
        if isinstance(error, commands.CommandInvokeError):
            print(f"CommandInvokeError in {ctx.command}: {error.original}")
            traceback.print_exception(type(error), error, error.__traceback__)
            return

        # Unhandled errors
        print(f"Unhandled error in {ctx.command}: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

async def setup(client: Astroz):
    await client.add_cog(Errors(client))