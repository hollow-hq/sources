import discord
import json
import os
import asyncio
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict
from utils.Tools import blacklist_check, ignore_check
from utils.constants import GreenTick2, error
from utils import Paginator, DescriptionEmbedPaginator

STICKY_PATH = "data/sticky_messages.json"

class Sticky(commands.Cog):
    """📌 Manage sticky messages that stay at the bottom of the channel."""

    def __init__(self, bot):
        self.bot = bot
        self.color = 0x4862DE
        self._locks: Dict[int, asyncio.Lock] = {}
        
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(STICKY_PATH):
            with open(STICKY_PATH, "w") as f:
                json.dump({}, f)

    def _load_data(self) -> dict:
        try:
            with open(STICKY_PATH, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_data(self, data: dict):
        with open(STICKY_PATH, "w") as f:
            json.dump(data, f, indent=4)

    async def get_lock(self, channel_id: int) -> asyncio.Lock:
        if channel_id not in self._locks:
            self._locks[channel_id] = asyncio.Lock()
        return self._locks[channel_id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.webhook_id or not message.guild:
            return

        cid = str(message.channel.id)
        data = self._load_data()

        if cid not in data:
            return

        config = data[cid]
        lock = await self.get_lock(message.channel.id)

        async with lock:
            last_id = config.get("last_message_id")
            if last_id:
                try:
                    old_msg = await message.channel.fetch_message(last_id)
                    await old_msg.delete()
                except:
                    pass

            try:
                content = config["content"]
                new_sticky = await message.channel.send(content=content)
                
                data = self._load_data() 
                if cid in data:
                    data[cid]["last_message_id"] = new_sticky.id
                    self._save_data(data)
            except discord.Forbidden:
                pass

    @commands.hybrid_group(name="sticky", description="Manage sticky messages.", invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    @blacklist_check()
    @ignore_check()
    async def sticky_group(self, ctx: commands.Context):
      if ctx.invoked_subcommand is None:
        await ctx.send_help(ctx.command)

    @sticky_group.command(name="add")
    @commands.has_permissions(manage_messages=True)
    async def sticky_add(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, *, message: str):
        channel = channel or ctx.channel
        cid = str(channel.id)
        data = self._load_data()

        if cid in data:
            return await ctx.send(f"{error} | This channel already has a sticky.")

        try:
            initial_msg = await channel.send(message)
        except discord.Forbidden:
            return await ctx.send(f"{error} | I can't send messages in {channel.mention}.")

        data[cid] = {
            "guild_id": ctx.guild.id,
            "content": message,
            "last_message_id": initial_msg.id
        }
        self._save_data(data)
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | Sticky added to {channel.mention}.", color=self.color))

    @sticky_group.command(name="edit")
    @commands.has_permissions(manage_messages=True)
    async def sticky_edit(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, *, message: str):
        channel = channel or ctx.channel
        cid = str(channel.id)
        data = self._load_data()

        if cid not in data:
            return await ctx.send(f"{error} | No sticky found for {channel.mention}.")

        data[cid]["content"] = message
        self._save_data(data)
        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | Sticky updated for {channel.mention}.", color=self.color))

    @sticky_group.command(name="remove")
    @commands.has_permissions(manage_messages=True)
    async def sticky_remove(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        channel = channel or ctx.channel
        cid = str(channel.id)
        data = self._load_data()

        if cid not in data:
            return await ctx.send(f"{error} | No sticky found.")

        config = data.pop(cid)
        self._save_data(data)

        last_id = config.get("last_message_id")
        if last_id:
            try:
                old_msg = await channel.fetch_message(last_id)
                await old_msg.delete()
            except:
                pass

        await ctx.send(embed=discord.Embed(description=f"{GreenTick2} | Sticky removed from {channel.mention}.", color=self.color))

    @sticky_group.command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def sticky_list(self, ctx: commands.Context):
        data = self._load_data()
        entries = []
        count = 0

        for cid, config in data.items():
            if config["guild_id"] == ctx.guild.id:
                count += 1
                channel = self.bot.get_channel(int(cid))
                chan_name = channel.mention if channel else f"Deleted Channel (`{cid}`)"
                content_preview = (config["content"][:30] + '...') if len(config["content"]) > 30 else config["content"]
                entries.append(f"`{count}.` **Channel:** {chan_name}\n**Content:** {content_preview}")

        if not entries:
            return await ctx.send("No sticky messages are configured.")

        paginator = Paginator(
            source=DescriptionEmbedPaginator(
                entries=entries,
                title=f"Active Sticky Messages — {ctx.guild.name}",
                color=self.color,
                per_page=10
            ),
            ctx=ctx
        )
        await paginator.paginate()

async def setup(bot):
    await bot.add_cog(Sticky(bot))