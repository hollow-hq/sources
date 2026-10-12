import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import json

API_KEY = "0c5189c7e8155c13180eab96d9e618de3b5f1b2a69d99286e2452eeb4ce29758b414a61842537b96e956614a6f13a02241a30b4d225cec01c12c076ab6ffadcf"
USER_ID = "5568513"


class Nsfw(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(
        name="nsfw",
        description="NSFW related commands",
    )
    @commands.guild_only()
    async def nsfw(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @nsfw.group(name="hentai", description="Hentai related commands")
    async def hentai(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @nsfw.group(name="rule34", description="rule34 related commands")
    async def rule34(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    async def _fetch_hentai(self, ctx, tag: str) -> str | None:
        url = "https://api.waifu.im/images/"
        params = {"IncludedTags": [tag], "IsNsfw": "True"}
        headers = {"X-Api-Key": API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                try:
                    return data['items'][0]['url']
                except (KeyError, IndexError):
                    return None

    def _send(self, ctx, content):
        if ctx.interaction:
            return ctx.followup.send(content)
        return ctx.send(content)

    async def _defer(self, ctx):
        if ctx.interaction:
            await ctx.defer()

    @rule34.command(name="images", description="images Rule34 for NSFW content")
    @app_commands.describe(query="images query for Rule34 content")
    async def rule34images(self, ctx: commands.Context, query: str):
        await self._defer(ctx)
        api_url = (
            f"https://api.rule34.xxx/index.php?"
            f"page=dapi&s=post&q=index&json=1&limit=100&tags={query}"
            f"&user_id={USER_ID}&api_key={API_KEY}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    return await self._send(ctx, "Failed to fetch data from Rule34.")

                try:
                    data = await response.json()
                except Exception:
                    text = await response.text()
                    return await self._send(ctx, f"Rule34 returned an invalid response:\n```{text[:500]}```")

                if not isinstance(data, list) or not data:
                    return await self._send(ctx, f"No results found for `{query}`.")

                post = random.choice(data)
                image_url = post.get("file_url")
                if not image_url:
                    return await self._send(ctx, f"No image found for `{query}`.")

                return await self._send(ctx, image_url)

    @rule34images.autocomplete("query")
    async def rule34_autocomplete(self, ctx: commands.Context, current: str) -> list[app_commands.Choice[str]]:
        if not current:
            return []

        url = f"https://api.rule34.xxx/autocomplete.php?q={current}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                try:
                    text = await response.text()
                    data = json.loads(text)
                    return [
                        app_commands.Choice(name=tag["label"], value=tag["value"])
                        for tag in data[:25]
                    ]
                except Exception:
                    return []

    @hentai.command(name="ecchi", description="✨ Spicy hentai content: ecchi")
    async def ecchi(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "ecchi")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[ecchi]({image_url})")

    @hentai.command(name="hentai", description="✨ Spicy hentai content: hentai")
    async def hentai(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "hentai")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[hentai]({image_url})")

    @hentai.command(name="uniform", description="✨ Spicy hentai content: uniform")
    async def uniform(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "uniform")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[uniform]({image_url})")

    @hentai.command(name="maid", description="✨ Spicy hentai content: maid")
    async def maid(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "maid")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[maid]({image_url})")

    @hentai.command(name="oppai", description="✨ Spicy hentai content: oppai")
    async def oppai(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "oppai")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[oppai]({image_url})")

    @hentai.command(name="selfies", description="✨ Spicy hentai content: selfies")
    async def selfies(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "selfies")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[selfies]({image_url})")

    @hentai.command(name="raiden", description="✨ Spicy hentai content: raiden")
    async def raiden(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "raiden")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[raiden]({image_url})")

    @hentai.command(name="marin", description="✨ Spicy hentai content: marin")
    async def marin(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "marin")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[marin]({image_url})")

    @hentai.command(name="ass", description="✨ Spicy hentai content: ass")
    async def ass(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "ass")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[ass]({image_url})")

    @hentai.command(name="paizuri", description="✨ Spicy hentai content: paizuri")
    async def paizuri(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "paizuri")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[paizuri]({image_url})")

    @hentai.command(name="ero", description="✨ Spicy hentai content: ero")
    async def ero(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "ero")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[ero]({image_url})")

    @hentai.command(name="milf", description="✨ Spicy hentai content: milf")
    async def milf(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "milf")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[milf]({image_url})")

    @hentai.command(name="oral", description="✨ Spicy hentai content: oral")
    async def oral(self, ctx: commands.Context):
        await self._defer(ctx)
        image_url = await self._fetch_hentai(ctx, "oral")
        if not image_url:
            return await self._send(ctx, "Failed to fetch content.")
        return await self._send(ctx, f"[oral]({image_url})")
