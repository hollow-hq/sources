import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import time
import math
import asyncio
import io
from typing import Optional, Union, Dict
from PIL import Image, ImageDraw, ImageFont, ImageOps
from core import Cog, Astroz, Context
from utils.Tools import blacklist_check, ignore_check
from utils.constants import GreenTick2, error as error_emoji

# ─── Data Paths ───────────────────────────────────────────────────────────────
SETTINGS_PATH = "data/leveling_settings.json"
USERS_PATH = "data/leveling_users.json"
ROLES_PATH = "data/leveling_roles.json"

class Leveling(Cog):
    """Sleek XP and Leveling system."""

    def __init__(self, bot: Astroz):
        self.bot = bot
        self.color = 0x4862DE
        self._xp_cooldowns: Dict[tuple, float] = {}  # (guild_id, user_id): timestamp

        # Ensure data directory and files exist
        os.makedirs("data", exist_ok=True)
        for path in [SETTINGS_PATH, USERS_PATH, ROLES_PATH]:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump({}, f)

    # ─── Helper Methods ────────────────────────────────────────────────────────

    def _get_data(self, path: str) -> dict:
        with open(path, "r") as f:
            return json.load(f)

    def _save_data(self, path: str, data: dict):
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    def xp_needed(self, level: int) -> int:
        """Formula: 100 * L^1.5 + 100"""
        if level < 0: return 100
        return int(100 * (level ** 1.5) + 100)

    def _get_user_rank(self, guild_id: int, user_id: int) -> int:
        users = self._get_data(USERS_PATH).get(str(guild_id), {})
        # Sort users by XP descending
        sorted_users = sorted(users.items(), key=lambda x: x[1]['xp'], reverse=True)
        for rank, (uid, _) in enumerate(sorted_users, 1):
            if int(uid) == user_id:
                return rank
        return 0

    # ─── Image Generation (PIL) ───────────────────────────────────────────────

    def _generate_card(self, user_name: str, avatar_bytes: bytes, level: int, rank: int, current_xp: int, next_xp: int) -> io.BytesIO:
        # Create canvas
        width, height = 800, 250
        card = Image.new("RGBA", (width, height), (20, 20, 20, 255))
        draw = ImageDraw.Draw(card)

        # Background accents (using bot's name for sidebar description)
        draw.rectangle([0, 0, 15, height], fill=(72, 98, 222)) # {self.bot.user.name} Blue Sidebar

        # Process Avatar
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((160, 160))
        mask = Image.new("L", (160, 160), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 160, 160), fill=255)
        avatar.putalpha(mask)
        card.paste(avatar, (50, 45), avatar)

        # Text Elements (Try loading fonts, fallback to default)
        try:
            font_large = ImageFont.truetype("arial.ttf", 40)
            font_mid = ImageFont.truetype("arial.ttf", 30)
            font_small = ImageFont.truetype("arial.ttf", 22)
        except:
            font_large = font_mid = font_small = ImageFont.load_default()

        # Username and Progress
        draw.text((240, 50), user_name[:18], fill="white", font=font_large)
        draw.text((240, 105), f"Level: {level}   |   Rank: #{rank}", fill=(200, 200, 200), font=font_mid)
        
        # XP Progress Text
        xp_text = f"{current_xp:,} / {next_xp} XP"
        draw.text((width - 50 - draw.textlength(xp_text, font_small), 165), xp_text, fill="white", font=font_small)

        # Progress Bar
        bar_x, bar_y = 240, 195
        bar_w, bar_h = 510, 25
        progress_pct = min(current_xp / next_xp, 1.0)
        
        # Draw Bar Background
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=12, fill=(50, 50, 50))
        # Draw Progress
        if progress_pct > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + (bar_w * progress_pct), bar_y + bar_h], radius=12, fill=(72, 98, 222))

        buffer = io.BytesIO()
        card.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    # ─── Events ────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        gid = str(message.guild.id)
        settings = self._get_data(SETTINGS_PATH).get(gid)
        
        if not settings or not settings.get("enabled"):
            return

        # Cooldown check
        user_key = (message.guild.id, message.author.id)
        last_gain = self._xp_cooldowns.get(user_key, 0)
        cooldown = settings.get("cooldown_seconds", 60)
        
        if time.time() - last_gain < cooldown:
            return

        # Award XP
        users = self._get_data(USERS_PATH)
        guild_users = users.setdefault(gid, {})
        user_id = str(message.author.id)
        user_data = guild_users.setdefault(user_id, {"xp": 0, "level": 0})

        xp_gain = settings.get("xp_per_message", 15)
        user_data["xp"] += xp_gain
        self._xp_cooldowns[user_key] = time.time()

        # Level Up Logic
        current_lvl = user_data["level"]
        xp_needed = self.xp_needed(current_lvl)

        if user_data["xp"] >= xp_needed:
            user_data["level"] += 1
            user_data["xp"] = 0 # Reset XP for new level
            self._save_data(USERS_PATH, users)
            
            # Level up notification
            embed = discord.Embed(
                description=f"🎊 {message.author.mention}, you just leveled up to **Level {user_data['level']}**!",
                color=self.color
            )
            await message.channel.send(embed=embed, delete_after=10)

            # Role Rewards
            roles_data = self._get_data(ROLES_PATH).get(gid, {})
            reward_role_id = roles_data.get(str(user_data["level"]))
            if reward_role_id:
                role = message.guild.get_role(int(reward_role_id))
                if role:
                    try:
                        await message.author.add_roles(role, reason="Level Up Reward")
                    except discord.Forbidden:
                        pass
        else:
            self._save_data(USERS_PATH, users)

    # ─── Commands ──────────────────────────────────────────────────────────────

    @commands.hybrid_group(name="level", invoke_without_command=True, aliases=["lvl", "rank"])
    @blacklist_check()
    @ignore_check()
    async def _level(self, ctx: Context, member: Optional[discord.Member] = None):
        """View your leveling progress with a custom card image."""
        member = member or ctx.author
        await ctx.typing()
        
        gid, uid = str(ctx.guild.id), str(member.id)
        user_data = self._get_data(USERS_PATH).get(gid, {}).get(uid, {"xp": 0, "level": 0})
        
        try:
            avatar_bytes = await member.display_avatar.read()
        except discord.NotFound:
            avatar_bytes = await member.default_avatar.read()
            
        rank = self._get_user_rank(ctx.guild.id, member.id)
        
        # Run image gen in thread to avoid blocking
        buffer = await asyncio.to_thread(
            self._generate_card, 
            str(member), 
            avatar_bytes, 
            user_data["level"], 
            rank, 
            user_data["xp"], 
            self.xp_needed(user_data["level"])
        )
        
        filename = f"level_card_{member.id}.png"
        file = discord.File(fp=buffer, filename=filename)
        
        embed = discord.Embed(color=self.color)
        embed.set_author(name=f"Leveling Progress — {member.display_name}", icon_url=member.display_avatar.url)
        embed.set_image(url=f"attachment://{filename}")
        
        await ctx.send(embed=embed, file=file)

    @_level.command(name="toggle", description="Enable or disable the leveling system.")
    @commands.has_permissions(manage_guild=True)
    async def _toggle(self, ctx: Context):
        settings = self._get_data(SETTINGS_PATH)
        gid = str(ctx.guild.id)
        
        guild_conf = settings.setdefault(gid, {"enabled": False, "xp_per_message": 15, "cooldown_seconds": 60})
        guild_conf["enabled"] = not guild_conf["enabled"]
        
        self._save_data(SETTINGS_PATH, settings)
        status = "enabled" if guild_conf["enabled"] else "disabled"
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | Leveling has been **{status}**.", color=self.color))

    @_level.command(name="leaderboard", aliases=["lb"])
    @blacklist_check()
    @ignore_check()
    async def _lb(self, ctx: Context):
        """See the top 10 most active members."""
        users = self._get_data(USERS_PATH).get(str(ctx.guild.id), {})
        if not users:
            return await ctx.send("No one has earned XP yet!")

        sorted_users = sorted(users.items(), key=lambda x: (x[1]['level'], x[1]['xp']), reverse=True)[:10]
        
        description = ""
        for i, (uid, data) in enumerate(sorted_users, 1):
            description += f"`{i}.` <@{uid}> — **Level {data['level']}** ({data['xp']:,} XP)\n"

        embed = discord.Embed(title=f"Leaderboard — {ctx.guild.name}", description=description, color=self.color)
        await ctx.send(embed=embed)

    @_level.command(name="threshold", description="Set XP earned per message.")
    @commands.has_permissions(manage_guild=True)
    async def _threshold(self, ctx: Context, xp: int):
        if xp < 1 or xp > 1000:
            return await ctx.send(f"{error_emoji} | XP must be between 1 and 1000.")
            
        settings = self._get_data(SETTINGS_PATH)
        settings.setdefault(str(ctx.guild.id), {})["xp_per_message"] = xp
        self._save_data(SETTINGS_PATH, settings)
        
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | XP per message set to `{xp}`.", color=self.color))

    # ─── Role Rewards Sub-group ───────────────────────────────────────────────

    @_level.group(name="role", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def _role(self, ctx: Context):
        """Manage level-up role rewards."""
        await ctx.send_help(ctx.command)

    @_role.command(name="add")
    async def _role_add(self, ctx: Context, level: int, role: discord.Role):
        """Assign a role when a user reaches a level."""
        roles = self._get_data(ROLES_PATH)
        gid = str(ctx.guild.id)
        
        roles.setdefault(gid, {})[str(level)] = role.id
        self._save_data(ROLES_PATH, roles)
        
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | Reaching Level **{level}** will now grant {role.mention}.", color=self.color))

    @_role.command(name="remove")
    async def _role_remove(self, ctx: Context, level: int):
        """Remove a role reward for a level."""
        roles = self._get_data(ROLES_PATH)
        gid = str(ctx.guild.id)
        
        if gid in roles and str(level) in roles[gid]:
            del roles[gid][str(level)]
            self._save_data(ROLES_PATH, roles)
            await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | Removed role reward for Level **{level}**.", color=self.color))
        else:
            await ctx.send(f"{error_emoji} | No role reward found for that level.")

    @_role.command(name="list")
    async def _role_list(self, ctx: Context):
        """List all configured role rewards."""
        roles = self._get_data(ROLES_PATH).get(str(ctx.guild.id), {})
        if not roles:
            return await ctx.send("No role rewards configured.")

        # Sort by level
        sorted_roles = sorted(roles.items(), key=lambda x: int(x[0]))
        desc = "\n".join([f"Level **{lvl}** — <@&{rid}>" for lvl, rid in sorted_roles])
        
        embed = discord.Embed(title="Role Rewards", description=desc, color=self.color)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))