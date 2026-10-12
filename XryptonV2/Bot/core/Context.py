from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from .Astroz import Astroz

__all__ = ("Context",)


class Context(commands.Context["Astroz"]):
    """Custom implementation of commands.Context with enhanced features."""

    def __repr__(self) -> str:
        return "<core.Context>"

    @property
    def session(self) -> Any:
        """Alias for bot.session."""
        return self.bot.session

    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.Message]:
        """Get the message that was replied to, if any."""
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    def typing_or_fallback(self, func):
        """Decorator that shows typing indicator, falls back on Forbidden."""
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            ctx = args[0] if isinstance(args[0], commands.Context) else args[1]
            try:
                async with ctx.typing():
                    return await func(*args, **kwargs)
            except discord.Forbidden:
                return await func(*args, **kwargs)
        return wrapped

    async def show_help(self, command: str = None) -> None:
        """Show help for a command or the current command."""
        cmd = self.bot.get_command("help")
        command = command or self.command.qualified_name
        await self.invoke(cmd, command=command)

    async def send(
        self,
        content: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        """Send a message, fallback to DM if lacking permissions."""
        if not self.channel.permissions_for(self.me).send_messages:
            try:
                await self.author.send("Bot doesn't have permissions to send messages in that channel.")
            except discord.Forbidden:
                pass
            return None
        return await super().send(content, **kwargs)

    async def reply(
        self,
        content: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        """Reply to a message, fallback to DM if lacking permissions."""
        if not self.channel.permissions_for(self.me).send_messages:
            try:
                await self.author.send("Bot doesn't have permissions to send messages in that channel.")
            except discord.Forbidden:
                pass
            return None
        return await super().reply(content, **kwargs)

    async def release(self, delay: float = 0) -> None:
        """Release resources after an optional delay."""
        if delay > 0:
            await asyncio.sleep(delay)
