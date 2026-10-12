from __future__ import annotations

from discord.ext import commands

__all__ = ("Cog",)


class Cog(commands.Cog):
    """Base Cog class with common functionality."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"