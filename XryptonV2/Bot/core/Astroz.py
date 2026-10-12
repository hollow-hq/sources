from __future__ import annotations

import asyncio
import itertools
import json
import logging
import typing

import discord
from discord.ext import commands

from .Context import Context
from utils.config import OWNER_IDS

log = logging.getLogger(__name__)


class Astroz(commands.AutoShardedBot):
    """Main bot class with custom functionality."""

    def __init__(self) -> None:
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=self.get_prefix,
            case_insensitive=True,
            intents=intents,
            status=discord.Status.dnd,
            strip_after_prefix=True,
            owner_ids=OWNER_IDS,
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                replied_user=False,
                roles=False,
                users=False,
            ),
            sync_commands=True,
            sync_commands_debug=False,
            shard_count=1,
        )

        # Cache premium users to avoid disk I/O
        self._premium_cache: set[str] = set()
        self._load_premium()

    def _load_premium(self) -> None:
        """Load premium user IDs from disk into memory."""
        try:
            with open("data/premium.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self._premium_cache = set(map(str, data))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.warning("Failed loading premium.json: %s", e)
            self._premium_cache = set()

    async def on_connect(self) -> None:
        """Start presence rotation when bot connects."""
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.streaming,
                url="https://www.twitch.tv/voby7",
                name=".help & .invite",
            ),
        )
        if hasattr(self, "user") and self.user:
            self._status_task = self.loop.create_task(self._cycle_presence())

    async def _cycle_presence(self) -> None:
        """Cycle through different presence statuses every 60 seconds."""
        statuses = itertools.cycle(
            [
                discord.ActivityType.streaming,
                discord.ActivityType.playing,
                discord.ActivityType.watching,
                discord.ActivityType.streaming,
            ]
        )
        activity_names = itertools.cycle(
            [
                ".help & .invite",
                "{guild_count} Servers • {user_count:,} Users",
                "Watching for rulebreakers",
                "{guild_count} Servers trust me!!",
            ]
        )
        status_objs = itertools.cycle(
            [
                discord.Status.online,
                discord.Status.dnd,
                discord.Status.online,
                discord.ActivityType.streaming,
            ]
        )
        urls = itertools.cycle(
            [
                "https://www.twitch.tv/voby7",
                "https://www.discord.gg/FtgCrfxXbG",
                "",
                "https://www.twitch.tv/voby7",
            ]
        )

        await asyncio.sleep(60)

        while True:
            activity_type = next(statuses)
            name = next(activity_names)
            status = next(status_objs)
            url = next(urls)

            guild_count = len(self.guilds)
            user_count = sum(g.member_count for g in self.guilds)
            name = name.format(guild_count=guild_count, user_count=user_count)

            activity_kwargs: dict = {"type": activity_type, "name": name}
            if url:
                activity_kwargs["url"] = url

            await self.change_presence(status=status, activity=discord.Activity(**activity_kwargs))
            await asyncio.sleep(60)

    async def send_raw(self, channel_id: int, content: str, **kwargs: typing.Any) -> None:
        """Send a message to a channel by ID without needing the channel object."""
        await self.http.send_message(channel_id, content, **kwargs)

    async def invoke_help_command(self, ctx: Context) -> None:
        """Invoke the help command for the given context."""
        await ctx.send_help(ctx.command)

    async def fetch_message_by_channel(
        self,
        channel: discord.TextChannel,
        message_id: int,
    ) -> typing.Optional[discord.Message]:
        """Fetch a message from a channel by ID using history search."""
        async for msg in channel.history(
            limit=1,
            before=discord.Object(id=message_id + 1),
            after=discord.Object(id=message_id - 1),
        ):
            return msg
        return None

    async def get_prefix(self, message: discord.Message) -> typing.Union[str, typing.List[str]]:
        """Get the command prefix for a message, with premium support."""
        # Premium users get minimal prefix set
        if str(message.author.id) in self._premium_cache:
            return commands.when_mentioned_or(".", "")(self, message)

        try:
            if message.guild:
                from utils.config import getConfig  # Avoid circular import
                config = getConfig(message.guild.id)
                prefix = config.get("prefix", ".")
            else:
                prefix = "."
            return commands.when_mentioned_or(prefix)(self, message)
        except Exception as e:
            log.warning(f"Failed to get prefix for guild {message.guild.id if message.guild else 'DM'}: {e}")
            return commands.when_mentioned_or(".")(self, message)

    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        """Handle message edits by re-invoking commands."""
        if before.content == after.content:
            return

        if after.guild is None or after.author.bot:
            return

        if isinstance(after.channel, discord.Thread):
            return

        ctx: Context = await self.get_context(after, cls=Context)

        if ctx.command is None:
            return

        await self.invoke(ctx)
