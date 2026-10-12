from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
from typing import Optional

import aiohttp
import discord
import requests
from discord.ext import commands

from core import Context, Cog
from utils.Tools import blacklist_check, ignore_check, getConfig
from utils.constants import BOT_Loading


class General(Cog, name='GeneralCommands'):
    """General utility commands."""

    def __init__(self, bot: commands.Bot, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.color = 0x4862DE
        self._url_regex = (
            r"(?P<url><[^: >]+:\/\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,;\"'\]\s])"
        )

    async def _fetch_url(self, session: aiohttp.ClientSession, url: str) -> dict:
        """Fetch and parse JSON from a URL."""
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    # ─── User Commands ──────────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="avatar",
        aliases=["av"],
        usage="Avatar [member]",
        help="Get a user's avatar with download links.",
    )
    @blacklist_check()
    @ignore_check()
    async def avatar(
        self,
        ctx: Context,
        member: Optional[discord.Member | discord.User] = None,
    ) -> None:
        """Show avatar information for a user."""
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)

        formats = ["png", "jpg", "webp"]
        if user.avatar and user.avatar.is_animated():
            formats.append("gif")

        links = " | ".join(
            f"[{fmt.upper()}]({user.avatar.replace(format=fmt)})"
            for fmt in formats
        )

        embed = discord.Embed(
            description=f"{links}",
            color=self.color,
        )
        embed.set_author(
            name=str(member),
            icon_url=member.display_avatar.url,
        )
        embed.set_image(url=user.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="servericon",
        help="Show the server's icon.",
        usage="Servericon",
    )
    @blacklist_check()
    @ignore_check()
    async def servericon(self, ctx: Context) -> None:
        """Show the server icon with download links."""
        guild = ctx.guild
        if not guild.icon:
            return await ctx.send("This server has no icon.")

        formats = ["png", "jpg", "webp"]
        if guild.icon.is_animated():
            formats.append("gif")

        links = " | ".join(
            f"[{fmt.upper()}]({guild.icon.replace(format=fmt)})"
            for fmt in formats
        )

        embed = discord.Embed(
            title=f"{guild.name}'s Icon",
            description=links,
            color=self.color,
        )
        embed.set_image(url=guild.icon.url)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="membercount",
        aliases=["mc"],
        help="Get total member count of the server.",
        usage="membercount",
    )
    @blacklist_check()
    @ignore_check()
    async def membercount(self, ctx: Context) -> None:
        """Show member statistics for the server."""
        online = offline = dnd = idle = bots = 0

        for member in ctx.guild.members:
            if member.bot:
                bots += 1
            elif member.status is discord.Status.online:
                online += 1
            elif member.status is discord.Status.offline:
                offline += 1
            elif member.status is discord.Status.dnd:
                dnd += 1
            elif member.status is discord.Status.idle:
                idle += 1

        embed = discord.Embed(
            title=ctx.guild.name,
            description=f"Here is **{ctx.guild.name}**'s member information",
            color=self.color,
        )
        embed.add_field(name="*Online*", value=f"`{online}`", inline=False)
        embed.add_field(name="*Offline*", value=f"`{offline}`", inline=False)
        embed.add_field(name="*Idle*", value=f"`{idle}`", inline=False)
        embed.add_field(name="*Do Not Disturb*", value=f"`{dnd}`", inline=False)
        embed.add_field(name="*Bots*", value=f"`{bots}`", inline=False)
        embed.add_field(
            name="*Total*",
            value=f"`{len(ctx.guild.members)}`",
            inline=False,
        )
        await ctx.send(embed=embed)

    # ─── Utility Commands ───────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="poll",
        usage="Poll [message]",
        help="Create a simple poll with thumbs up/down reactions.",
    )
    @blacklist_check()
    @ignore_check()
    async def poll(self, ctx: Context, *, message: str) -> None:
        """Create a poll message."""
        embed = discord.Embed(
            title="**Poll!**",
            description=message,
            color=self.color,
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

    @commands.hybrid_command(
        name="hack",
        help="Fake hack command for fun.",
        usage="Hack <member>",
    )
    @blacklist_check()
    @ignore_check()
    async def hack(self, ctx: Context, member: discord.Member) -> None:
        """Fake hack someone (for fun)."""
        passwords = [
            "1838812`", "382131847", "231838924", "218318371", "3145413",
            "43791", "471747183813474", "123747019", "312312318",
        ]
        random_pass = random.choice(passwords)

        embed = discord.Embed(
            title="**Hacked!**",
            description=(
                f"Username - {member.display_name}\n"
                f"E-Mail - {member.display_name}@gmail.com\n"
                f"Password - {member.display_name}@{random_pass}"
            ),
            color=self.color,
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="token",
        usage="Token <member>",
        help="Generate a fake token for a user.",
    )
    @blacklist_check()
    @ignore_check()
    async def token(self, ctx: Context, user: discord.Member = None) -> None:
        """Generate a fake Discord token."""
        chars = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz0123456789"
        )
        token = "".join(random.choices(chars, k=59))

        target = user or ctx.author
        await ctx.send(f"{target.mention}'s token is `{token}`")

    @commands.hybrid_command(
        name="users",
        help="Check total users across all servers.",
        usage="users",
    )
    @blacklist_check()
    @ignore_check()
    async def users(self, ctx: Context) -> None:
        """Show total user count across all guilds."""
        total = sum(guild.member_count for guild in self.bot.guilds)
        embed = discord.Embed(
            title="**Users:**",
            description=f"**{total}** Users Of {self.bot.user.name}",
            color=self.color,
        )
        await ctx.send(embed=embed)

    # ─── Text Formatting ────────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="italicize",
        help="Italicize the given text.",
        usage="Italicize <message>",
    )
    @blacklist_check()
    @ignore_check()
    async def italicize(self, ctx: Context, *, message: str) -> None:
        """Format text as italic."""
        await ctx.message.delete()
        await ctx.send(f"*{message}*")

    @commands.hybrid_command(
        name="strike",
        help="Strike through the given text.",
        usage="Strike <message>",
    )
    @blacklist_check()
    @ignore_check()
    async def strike(self, ctx: Context, *, message: str) -> None:
        """Format text with strikethrough."""
        await ctx.message.delete()
        await ctx.send(f"~~{message}~~")

    @commands.hybrid_command(
        name="quote",
        help="Quote the given text.",
        usage="Quote <message>",
    )
    @blacklist_check()
    @ignore_check()
    async def quote(self, ctx: Context, *, message: str) -> None:
        """Format text as a quote."""
        await ctx.message.delete()
        await ctx.send(f"> {message}")

    @commands.hybrid_command(
        name="code",
        help="Format text as inline code.",
        usage="Code <message>",
    )
    @blacklist_check()
    @ignore_check()
    async def code(self, ctx: Context, *, message: str) -> None:
        """Format text as inline code."""
        await ctx.send(f"`{message}`")

    @commands.hybrid_command(
        name="bold",
        help="Bold the given text.",
        usage="Bold <message>",
    )
    @blacklist_check()
    @ignore_check()
    async def bold(self, ctx: Context, *, message: str) -> None:
        """Format text as bold."""
        await ctx.send(f"**{message}**")

    @commands.hybrid_command(
        name="censor",
        help="Censor the given text.",
        usage="Censor <message>",
    )
    @blacklist_check()
    @ignore_check()
    async def censor(self, ctx: Context, *, message: str) -> None:
        """Censor text with spoiler tags."""
        await ctx.send(f"||{message}||")

    @commands.hybrid_command(
        name="underline",
        help="Underline the given text.",
        usage="Underline <message>",
    )
    @blacklist_check()
    @ignore_check()
    async def underline(self, ctx: Context, *, message: str) -> None:
        """Format text with underline."""
        await ctx.send(f"__{message}__")

    # ─── Misc Fun Commands ─────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="gender",
        usage="Gender <member>",
        help="Check someone's gender (always None).",
    )
    @blacklist_check()
    @ignore_check()
    async def gender(self, ctx: Context, member: discord.Member) -> None:
        """Check someone's gender."""
        embed = discord.Embed(
            description=f"{member.mention}'s gender is None",
            color=discord.Colour.default(),
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="wizz",
        usage="Wizz",
        help="Simulate deleting and banning everything (joke command).",
    )
    @blacklist_check()
    @ignore_check()
    async def wizz(self, ctx: Context) -> None:
        """Joke command - simulate nuking the server."""
        messages = [
            f"`Wizzing {ctx.guild.name}, will take 22 seconds to complete`",
            f"`Deleting {len(ctx.guild.roles)} Roles...`",
            f"`Deleting {len(ctx.guild.channels)} Channels...`",
            "`Deleting Webhooks...`",
            "`Deleting emojis`",
            "`Installing Ban Wave..`",
        ]

        for msg_text in messages:
            msg = await ctx.send(msg_text)
            await asyncio.sleep(3.5)
            await msg.delete()

        embed = discord.Embed(
            title=f"{self.bot.user.name}",
            description=f"**Successfully Wizzed {ctx.guild.name}**",
            color=self.color,
            timestamp=ctx.message.created_at,
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        name="pikachu",
        help="Get a random Pikachu GIF.",
        usage="Pikachu",
    )
    @blacklist_check()
    @ignore_check()
    async def pikachu(self, ctx: Context) -> None:
        """Fetch a random Pikachu GIF."""
        try:
            response = requests.get(
                "https://some-random-api.ml/img/pikachu", timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return await ctx.send("Could not fetch Pikachu image.")

        embed = discord.Embed(
            title="Pikachu",
            description="Here is a gif of Pikachu.",
            color=self.color,
        )
        embed.set_image(url=data.get("link", ""))
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="shorten",
        help="Shorten a URL with multiple services.",
        usage="Shorten <url>",
    )
    @blacklist_check()
    @ignore_check()
    async def shorten(self, ctx: Context, *, url: str) -> None:
        """Shorten a URL using multiple shorteners."""
        async with ctx.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    tasks = [
                        self._fetch_url(
                            session,
                            f"https://api.shrtco.de/v2/shorten?url={url}",
                        ),
                        self._fetch_url(
                            session,
                            f"https://clck.ru/--?url={url}",
                        ),
                         self._fetch_url(
                             session,
                            f"http://tinyurl.com/api-create.php?url={url}",
                         ),
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                return await ctx.send("Failed to shorten URL.")

        embed = discord.Embed(title=f"URL Shortener ({url})")

        if not isinstance(results[0], Exception):
            embed.add_field(
                name="Shortened URL (9qr.de)",
                value=results[0].get("result", {}).get("full_short_link2", "N/A"),
                inline=False,
            )

        if not isinstance(results[1], Exception):
            embed.add_field(
                name="Shortened URL (clck.ru)",
                value=results[1] if isinstance(results[1], str) else "N/A",
                inline=False,
            )

        if not isinstance(results[2], Exception):
            embed.add_field(
                name="Shortened URL (tinyurl.com)",
                value=results[2] if isinstance(results[2], str) else "N/A",
                inline=False,
            )

        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(
        name="urban",
        description="Search for a phrase on Urban Dictionary.",
        help="Get Urban Dictionary definitions.",
        usage="Urban <phrase>",
    )
    @blacklist_check()
    @ignore_check()
    async def urban(self, ctx: Context, *, phrase: str) -> None:
        """Look up a phrase on Urban Dictionary."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://api.urbandictionary.com/v0/define?term={phrase}"
                ) as resp:
                    data = await resp.json()
        except Exception:
            return await ctx.send("Could not fetch definition.")

        try:
            entry = data["list"][0]
            embed = discord.Embed(
                title=f"Term - '{phrase}'",
                color=self.color,
            )
            embed.add_field(
                name="Definition",
                value=entry["definition"].replace("[", "").replace("]", "")[:1024],
                inline=False,
            )
            embed.add_field(
                name="Example",
                value=entry["example"].replace("[", "").replace("]", "")[:1024],
                inline=False,
            )

            msg = await ctx.reply(embed=embed, mention_author=True)
            await asyncio.sleep(15)
            await msg.delete()
            await ctx.message.delete()
        except (KeyError, IndexError):
            await ctx.send("No definition found.")

    @commands.hybrid_command(
        name="rickroll",
        help="Detect if a URL is a Rickroll.",
        usage="Rickroll <url>",
    )
    @blacklist_check()
    @ignore_check()
    async def rickroll(self, ctx: Context, *, url: str) -> None:
        """Check if a URL leads to a Rickroll."""
        if not re.match(self._url_regex, url):
            raise commands.BadArgument("Invalid URL")

        phrases = [
            "rickroll", "rick roll", "rick astley",
            "never gonna give you up",
        ]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, allow_redirects=True) as resp:
                    source = (await resp.content.read()).decode().lower()
        except Exception:
            return await ctx.send("Could not fetch URL.")

        is_rickroll = any(
            re.search(phrase, source, re.MULTILINE | re.IGNORECASE)
            for phrase in phrases
        )

        color = discord.Colour.red() if is_rickroll else discord.Colour.green()
        found_text = "was found" if is_rickroll else "was not found"

        await ctx.reply(
            embed=discord.Embed(
                title=f"Rick Roll {found_text} in webpage",
                color=color,
            ),
            mention_author=False,
        )

    @commands.hybrid_command(
        name="hash",
        help="Hash text with various algorithms.",
        usage="Hash <algorithm> <message>",
    )
    @blacklist_check()
    @ignore_check()
    async def hash(self, ctx: Context, algorithm: str, *, message: str) -> None:
        """Generate hash of a message using specified algorithm."""
        algos = {
            "md5": hashlib.md5(message.encode()).hexdigest(),
            "sha1": hashlib.sha1(message.encode()).hexdigest(),
            "sha224": hashlib.sha224(message.encode()).hexdigest(),
            "sha3_224": hashlib.sha3_224(message.encode()).hexdigest(),
            "sha256": hashlib.sha256(message.encode()).hexdigest(),
            "sha3_256": hashlib.sha3_256(message.encode()).hexdigest(),
            "sha384": hashlib.sha384(message.encode()).hexdigest(),
            "sha3_384": hashlib.sha3_384(message.encode()).hexdigest(),
            "sha512": hashlib.sha512(message.encode()).hexdigest(),
            "sha3_512": hashlib.sha3_512(message.encode()).hexdigest(),
            "blake2b": hashlib.blake2b(message.encode()).hexdigest(),
            "blake2s": hashlib.blake2s(message.encode()).hexdigest(),
        }

        embed = discord.Embed(
            title=f"Hashed '{message}'",
            color=discord.Colour.green(),
        )

        algo = algorithm.lower()
        if algo not in algos:
            for name, value in algos.items():
                embed.add_field(name=name, value=f"```{value}```", inline=False)
        else:
            embed.add_field(
                name=algo,
                value=f"```{algos[algo]}```",
                inline=False,
            )

        await ctx.reply(embed=embed, mention_author=False)

    # ─── Jail System ───────────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="jail",
        help="Jail a user (create jail role/channel).",
        usage="jail <user>",
    )
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def jail(self, ctx: Context, member: discord.Member) -> None:
        """Jail a user by restricting their permissions."""
        role = discord.utils.get(ctx.guild.roles, name="jailed")
        if not role:
            role = await ctx.guild.create_role(name="jailed")

        jail_channel = discord.utils.get(
            ctx.guild.text_channels, name="jail"
        )
        if not jail_channel:
            overwrites = {
                ctx.guild.default_role:
                    discord.PermissionOverwrite(
                        read_messages=False, send_messages=False
                    ),
                ctx.guild.me:
                    discord.PermissionOverwrite(read_messages=True),
            }
            try:
                jail_channel = await ctx.guild.create_text_channel(
                    "jail", overwrites=overwrites
                )
                await ctx.send(
                    embed=discord.Embed(
                        title="jail",
                        description=(
                            "Your server has no jail channel, "
                            f"I created one for you {jail_channel.mention}"
                        ),
                        color=self.color,
                    )
                )
            except discord.Forbidden:
                return await ctx.send(
                    embed=discord.Embed(
                        title="jail",
                        help="Please give me permissions, "
                        "I am unable to create the jailed channel",
                        color=self.color,
                    )
                )

        for channel in ctx.guild.channels:
            if channel.name == "jail":
                perms = channel.overwrites_for(member)
                perms.send_messages = True
                perms.read_messages = True
                await channel.set_permissions(member, overwrite=perms)
            else:
                perms = channel.overwrites_for(member)
                perms.send_messages = False
                perms.read_messages = False
                perms.view_channel = False
                await channel.set_permissions(member, overwrite=perms)

        await member.add_roles(role)

        await jail_channel.send(
            content=member.mention,
            embed=discord.Embed(
                title="jail",
                description=(
                    "Please live out your jail sentence until "
                    "the court lets you free."
                ),
                color=self.color,
            ),
        )
        await ctx.send(
            embed=discord.Embed(
                title="jail",
                description=f"Successfully jailed **`{member.name}**`",
                color=self.color,
            )
        )
        await member.send(
            embed=discord.Embed(
                title="jail",
                description=(
                    f"You have been jailed in **`{ctx.guild.name}`** "
                    f"by **`{ctx.author.name}`**"
                ),
                color=self.color,
            )
        )

    @commands.hybrid_command(
        name="unjail",
        help="Unjail a user.",
        usage="unjail <user>",
        aliases=["free"],
    )
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def unjail(self, ctx: Context, member: discord.Member) -> None:
        """Release a user from jail."""
        role = discord.utils.get(ctx.guild.roles, name="jailed")
        if not role:
            return await ctx.send("No jailed role found.")

        for channel in ctx.guild.channels:
            perms = channel.overwrites_for(member)
            perms.send_messages = None
            perms.read_messages = None
            perms.view_channel = None
            await channel.set_permissions(member, overwrite=perms)

        await member.remove_roles(role)

        await ctx.send(
            embed=discord.Embed(
                title="unjail",
                description=f"Successfully unjailed **`{member.name}`**",
                color=self.color,
            )
        )
        await member.send(
            embed=discord.Embed(
                title="unjail",
                description=(
                    f"you have been unjailed in **`{ctx.guild.name}`** "
                    f"by **`{ctx.author.name}`**"
                ),
                color=self.color,
            )
        )

    # ─── Media Only Channels ───────────────────────────────────────────────────

    @commands.hybrid_group(
        name="media",
        invoke_without_command=True,
        help="Manage media-only channels.",
    )
    @blacklist_check()
    @ignore_check()
    async def med(self, ctx: Context) -> None:
        """Media command group."""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @med.command(
        name="setup",
        help="Set up media-only channels for the server.",
    )
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def setup(self, ctx: Context, *, channel: discord.TextChannel) -> None:
        """Add a channel to media-only list."""
        perm_check = (
            ctx.author == ctx.guild.owner
            or ctx.author.top_role.position > ctx.guild.me.top_role.position
        )
        if not perm_check:
            embed = discord.Embed(
                description=(
                    "```yaml\n"
                    " - You must have Administrator permission.\n"
                    " - Your top role should be above my top role.```"
                ),
                color=self.color,
            )
            embed.set_author(
                name=ctx.author,
                icon_url=ctx.author.display_avatar.url,
            )
            return await ctx.send(embed=embed)

        try:
            with open("data/media.json", "r", encoding="utf-8") as f:
                media = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            media = {}

        guild_id = str(ctx.guild.id)
        if guild_id not in media:
            media[guild_id] = {"channel": []}

        media[guild_id]["channel"].append(channel.id)

        with open("data/media.json", "w", encoding="utf-8") as f:
            json.dump(media, f, indent=4)

        await ctx.send(
            embed=discord.Embed(
                description=(
                    f"Successfully added {channel.mention} "
                    "in media only channels."
                ),
                color=self.color,
            ),
            mention_author=False,
        )

    @med.command(
        name="remove",
        help="Remove a channel from media-only list.",
    )
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def remove(self, ctx: Context, *, channel: discord.TextChannel) -> None:
        """Remove a channel from media-only list."""
        perm_check = (
            ctx.author == ctx.guild.owner
            or ctx.author.top_role.position > ctx.guild.me.top_role.position
        )
        if not perm_check:
            embed = discord.Embed(
                description=(
                    "```yaml\n"
                    " - You must have Administrator permission.\n"
                    " - Your top role should be above my top role.```"
                ),
                color=self.color,
            )
            embed.set_author(
                name=ctx.author,
                icon_url=ctx.author.display_avatar.url,
            )
            return await ctx.send(embed=embed)

        try:
            with open("data/media.json", "r", encoding="utf-8") as f:
                media = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return await ctx.send("Media config not found.")

        guild_id = str(ctx.guild.id)
        if guild_id in media and channel.id in media[guild_id]["channel"]:
            media[guild_id]["channel"].remove(channel.id)

            with open("data/media.json", "w", encoding="utf-8") as f:
                json.dump(media, f, indent=4)

            await ctx.send(
                embed=discord.Embed(
                    description=(
                        f"Successfully removed {channel.mention} "
                        "from media only channels."
                    ),
                    color=self.color,
                ),
                mention_author=False,
            )

    @med.command(
        name="config",
        aliases=["show"],
        help="Show configured media-only channels.",
    )
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def config(self, ctx: Context) -> None:
        """Show all configured media-only channels."""
        perm_check = (
            ctx.author == ctx.guild.owner
            or ctx.author.top_role.position > ctx.guild.me.top_role.position
        )
        if not perm_check:
            embed = discord.Embed(
                description=(
                    "```yaml\n"
                    " - You must have Administrator permission.\n"
                    " - Your top role should be above my top role.```"
                ),
                color=self.color,
            )
            embed.set_author(
                name=ctx.author,
                icon_url=ctx.author.display_avatar.url,
            )
            return await ctx.send(embed=embed)

        try:
            with open("data/media.json", "r", encoding="utf-8") as f:
                media = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return await ctx.send("Media config not found.")

        guild_id = str(ctx.guild.id)
        chan_ids = media.get(guild_id, {}).get("channel", [])

        channels = []
        for cid in chan_ids:
            ch = self.bot.get_channel(cid)
            if ch:
                channels.append(ch.mention)

        embed = discord.Embed(
            title=f"Media Only Channels for {ctx.guild.name}",
            color=0x2f3136,
        )
        for i, mention in enumerate(channels, 1):
            embed.add_field(name=str(i), value=mention, inline=True)

        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @med.command(
        name="reset",
        help="Clear all media-only channel configurations.",
    )
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def reset(self, ctx: Context) -> None:
        """Reset all media-only channel configs."""
        perm_check = (
            ctx.author == ctx.guild.owner
            or ctx.author.top_role.position > ctx.guild.me.top_role.position
        )
        if not perm_check:
            embed = discord.Embed(
                description=(
                    "```yaml\n"
                    " - You must have Administrator permission.\n"
                     " - Your top role should be above my top role.```"
                ),
                color=self.color,
            )
            embed.set_author(
                name=ctx.author,
                icon_url=ctx.author.display_avatar.url,
            )
            return await ctx.send(embed=embed)

        try:
            with open("data/media.json", "r", encoding="utf-8") as f:
                media = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return await ctx.send("Media config not found.")

        guild_id = str(ctx.guild.id)
        if guild_id in media:
            media[guild_id]["channel"] = []

            with open("data/media.json", "w", encoding="utf-8") as f:
                json.dump(media, f, indent=4)

        await ctx.send(
            embed=discord.Embed(
                description="Successfully removed all media only channels.",
                color=self.color,
            ),
            mention_author=False,
        )

    # ─── Event Listeners ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Initialize media.json on bot ready."""
        try:
            with open("data/media.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        for guild in self.bot.guilds:
            if str(guild.id) not in data:
                data[str(guild.id)] = {"channel": []}

        with open("data/media.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Initialize guild data when bot joins.
        
        This is also handled by on_ready, but provides extra safety.
        """
        try:
            with open("data/media.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        if str(guild.id) not in data:
            data[str(guild.id)] = {"channel": []}

        with open("data/media.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Enforce media-only channel rules."""
        if message.guild is None or message.author.bot:
            return

        try:
            with open("data/media.json", "r", encoding="utf-8") as f:
                media = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return

        guild_id = str(message.guild.id)
        if guild_id not in media:
            return

        if message.channel.id in media[guild_id].get("channel", []):
            if not message.attachments:
                try:
                    await message.delete()
                    await message.channel.send(
                        "This channel is configured for media only. "
                        "You are only allowed to send media files.",
                        delete_after=5,
                    )
                except discord.Forbidden:
                    pass
                except discord.NotFound:
                    pass

async def setup(bot):
    await bot.add_cog(General(bot))