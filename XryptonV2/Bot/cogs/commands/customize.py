import discord
import json
import os
import re
import base64
import aiohttp
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union
from utils.Tools import blacklist_check, ignore_check
from utils.constants import GreenTick2, error

class Customize(commands.Cog):
    """Commands to personalize the AI agent's appearance and personality per server."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/guild_config.json"
        self.color = 0x4862DE  # signature blue
        
        # Ensure the data directory and JSON file exist
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                json.dump({}, f)

    def _get_config(self) -> dict:
        """Helper to load the JSON configuration file."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self, data: dict):
        """Helper to save data back to the JSON configuration file."""
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=4)

    async def _get_image_bytes(self, url: str) -> Optional[bytes]:
        """Helper to fetch image bytes from a URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.read()
            return None
        except Exception:
            return None

    def _init_guild(self, config: dict, guild_id: str):
        """Initialize a guild entry with default values if it doesn't exist."""
        if guild_id not in config:
            config[guild_id] = {
                "name": None,
                "pfp": None,
                "banner": None,
                "description": None
            }

    @commands.hybrid_group(name="customize", description="Customize the bot's profile for this server.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def customize(self, ctx: commands.Context):
        """Base command group for customization."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @customize.command(name="name", description="Change the BOT's name for this server.")
    @app_commands.describe(name="The new name for the AI")
    async def customize_name(self, ctx: commands.Context, *, name: str):
        config = self._get_config()
        gid = str(ctx.guild.id)
        self._init_guild(config, gid)
        
        config[gid]["name"] = name
        self._save_config(config)
        
        # Update the bot's nickname in the guild
        try:
            await ctx.guild.me.edit(nick=name, reason=f"Customization by {ctx.author}")
            msg = f"Successfully updated AI name to **{name}**."
        except discord.Forbidden:
            msg = f"Saved **{name}** to database, but I lack `Manage Nicknames` permission to update instantly."
            
        embed = discord.Embed(description=f"{GreenTick2} | {msg}", color=self.color)
        await ctx.send(embed=embed)

    @customize.command(name="pfp", description="Change the BOT's profile picture URL.")
    @app_commands.describe(attachment="Upload an image", url="Or provide a direct image URL")
    async def customize_pfp(self, ctx: commands.Context, attachment: Optional[discord.Attachment] = None, url: Optional[str] = None):
        image_url = attachment.url if attachment else url
        
        if not image_url:
            embed = discord.Embed(description=f"{error} | Please provide an attachment or a valid URL.", color=discord.Color.red())
            return await ctx.send(embed=embed)
            
        # Simple regex validation for URLs
        if not re.match(r'^https?://.*\.(?:png|jpg|jpeg|gif|webp)', image_url, re.IGNORECASE):
            embed = discord.Embed(description=f"{error} | Invalid image URL provided.", color=discord.Color.red())
            return await ctx.send(embed=embed)

        config = self._get_config()
        gid = str(ctx.guild.id)
        self._init_guild(config, gid)
        
        config[gid]["pfp"] = image_url
        self._save_config(config)
        
        # Apply to server profile
        img_bytes = await self._get_image_bytes(image_url)
        if img_bytes:
            try:
                await ctx.guild.me.edit(avatar=img_bytes)
                msg = "Successfully updated per-guild profile picture."
            except Exception as e:
                msg = f"Saved to database, but failed to update profile: {e}"
        
        embed = discord.Embed(description=f"{GreenTick2} | {msg}", color=self.color)
        embed.set_thumbnail(url=image_url)
        await ctx.send(embed=embed)

    @customize.command(name="banner", description="Change the BOT's banner URL for this server.")
    @app_commands.describe(attachment="Upload an image", url="Or provide a direct image URL")
    async def customize_banner(self, ctx: commands.Context, attachment: Optional[discord.Attachment] = None, url: Optional[str] = None):
        image_url = attachment.url if attachment else url
        
        if not image_url:
            embed = discord.Embed(description=f"{error} | Please provide an attachment or a valid URL.", color=discord.Color.red())
            return await ctx.send(embed=embed)

        config = self._get_config()
        gid = str(ctx.guild.id)
        self._init_guild(config, gid)
        
        config[gid]["banner"] = image_url
        self._save_config(config)

        # Use raw API to update server profile banner
        img_bytes = await self._get_image_bytes(image_url)
        if img_bytes:
            data_uri = f"data:image/png;base64,{base64.b64encode(img_bytes).decode()}"
            try:
                route = discord.http.Route('PATCH', '/guilds/{guild_id}/members/@me', guild_id=ctx.guild.id)
                await self.bot.http.request(route, json={'banner': data_uri})
                msg = "Successfully updated per-guild banner."
            except Exception as e:
                msg = f"Saved to database, but failed to update banner API: {e}"
        
        embed = discord.Embed(description=f"{GreenTick2} | {msg}", color=self.color)
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

    @customize.command(name="description", description="Change the BOT's personality description.")
    @app_commands.describe(text="The new system description/prompt")
    async def customize_description(self, ctx: commands.Context, *, text: str):
        config = self._get_config()
        gid = str(ctx.guild.id)
        self._init_guild(config, gid)
        
        config[gid]["description"] = text
        self._save_config(config)
        
        # Update server profile bio (raw API)
        try:
            route = discord.http.Route('PATCH', '/guilds/{guild_id}/members/@me', guild_id=ctx.guild.id)
            await self.bot.http.request(route, json={'bio': text})
            msg = "The AI description/bio has been updated."
        except Exception as e:
            msg = f"Saved to database, but failed to update bio API: {e}"

        embed = discord.Embed(
            title="Description Updated",
            description=f"{GreenTick2} | {msg}\n```\n{text}\n```",
            color=self.color
        )
        await ctx.send(embed=embed)

    @customize.command(name="reset", description="Reset all customizations for this server.")
    async def customize_reset(self, ctx: commands.Context):
        config = self._get_config()
        gid = str(ctx.guild.id)
        
        if gid in config:
            del config[gid]
            self._save_config(config)
            
        # Reset nickname
        try:
            await ctx.guild.me.edit(nick=None, avatar=None, reason="Customization Reset")
            # Reset Bio and Banner via API
            route = discord.http.Route('PATCH', '/guilds/{guild_id}/members/@me', guild_id=ctx.guild.id)
            await self.bot.http.request(route, json={'banner': None, 'bio': None})
            nick_status = "and nickname reset."
        except discord.Forbidden:
            nick_status = "but failed to reset nickname (Missing Permissions)."
            
        embed = discord.Embed(description=f"{GreenTick2} | Customizations cleared {nick_status}", color=self.color)
        await ctx.send(embed=embed)

    @customize.command(name="show", description="Show current customizations for this server.")
    async def customize_show(self, ctx: commands.Context):
        config = self._get_config()
        gid = str(ctx.guild.id)
        
        if gid not in config:
            embed = discord.Embed(description="No customizations set for this server.", color=self.color)
            return await ctx.send(embed=embed)
            
        data = config[gid]
        embed = discord.Embed(title=f"Customization Settings: {ctx.guild.name}", color=self.color)
        embed.add_field(name="Name", value=data.get("name") or "Default", inline=True)
        embed.add_field(name="Description", value=data.get("description") or "Default", inline=False)
        
        if data.get("pfp"):
            embed.set_thumbnail(url=data["pfp"])
        if data.get("banner"):
            embed.set_image(url=data["banner"])
            
        await ctx.send(embed=embed)

    @customize_name.error
    @customize_pfp.error
    @customize_banner.error
    async def customize_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description=f"{error} | You need `Administrator` permissions to use this command.", 
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Customize(bot))