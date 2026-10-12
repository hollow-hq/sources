import discord
import json
import asyncio
import datetime
import time
import random
from discord.ext import commands, tasks

GIVEAWAYS_PATH = "data/giveaways.json"

# ── File helpers ──────────────────────────────────────────────────────────────

def load_giveaways() -> dict:
    try:
        with open(GIVEAWAYS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_giveaways(data: dict):
    with open(GIVEAWAYS_PATH, "w") as f:
        json.dump(data, f, indent=4)


# ── Time converter ────────────────────────────────────────────────────────────

TIME_UNITS = {
    "s": (1, "Second", "Seconds"),
    "m": (60, "Minute", "Minutes"),
    "h": (3600, "Hour", "Hours"),
    "d": (86400, "Day", "Days"),
}


def convert(raw: str) -> tuple[int, str] | int:
    """
    Parse a duration string like '5m', '2h', '1d'.
    Returns (seconds, label) on success, -1 for bad unit, -2 for bad value.
    """
    unit = raw[-1]
    if unit not in TIME_UNITS:
        return -1
    try:
        val = int(raw[:-1])
    except ValueError:
        return -2
    multiplier, singular, plural = TIME_UNITS[unit]
    label = singular if val == 1 else plural
    return val * multiplier, label


# ── Core giveaway logic ───────────────────────────────────────────────────────

async def stop_giveaway(bot: discord.Client, g_id: str, data: dict):
    channel = bot.get_channel(data["channel_id"])
    if channel is None:
        return

    try:
        giveaway_message = await channel.fetch_message(int(g_id))
    except (discord.NotFound, discord.HTTPException):
        return

    # Collect valid entrants (exclude the bot itself)
    if not giveaway_message.reactions:
        users = []
    else:
        users = [
            user
            async for user in giveaway_message.reactions[0].users()
            if not user.bot
        ]

    winner_count = min(len(users), data["winners"])

    if users:
        winners = random.sample(users, winner_count)
        mentions = ", ".join(w.mention for w in winners)
        description = f"Congratulations {mentions}, you won the giveaway!"
    else:
        description = "No one entered the giveaway. No winners this time."

    result_embed = discord.Embed(
        title=f"🎉 {data['prize']} 🎉",
        description=description,
        color=0x2f3136,
    )
    result_embed.set_footer(text="Giveaway Ended!", icon_url=bot.user.avatar.url)
    await giveaway_message.edit(embed=result_embed)

    # Clean up from storage
    giveaways = load_giveaways()
    giveaways.pop(g_id, None)
    save_giveaways(giveaways)


# ── Cog ───────────────────────────────────────────────────────────────────────

class Giveaways(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.color = 0x4862DE
        self.giveaway_task.start()

    def cog_unload(self):
        self.giveaway_task.cancel()

    # ── Background task ───────────────────────────────────────────────────────

    @tasks.loop(seconds=5)
    async def giveaway_task(self):
        await self.bot.wait_until_ready()
        giveaways = load_giveaways()
        now = int(time.time())
        # Snapshot keys to avoid mutation during iteration
        for g_id in list(giveaways.keys()):
            if now > giveaways[g_id]["end_time"]:
                await stop_giveaway(self.bot, g_id, giveaways[g_id])

    # ── /giveaway ─────────────────────────────────────────────────────────────

    @commands.command(name="giveaway", aliases=["gstart"])
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: commands.Context):
        try:
            with open("config.json", "r") as f:
                conf = json.load(f)
                bot_name = conf["bot"]["bot_name"]
        except Exception:
            bot_name = self.bot.user.name

        init_embed = discord.Embed(
            title="🎉 New Giveaway! 🎉",
            description="Please answer the following questions to create the giveaway.",
            color=self.color,
        )
        init_embed.set_footer(text=bot_name, icon_url=self.bot.user.avatar.url)
        init_msg = await ctx.send(embed=init_embed)

        questions = [
            "What is the prize for the giveaway?",
            "Which channel should the giveaway be in? (Mention the channel)",
            "How long should the giveaway last? Example: `1d`, `1h`, `30m`, `60s`",
            "How many winners do you want?",
        ]

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        answers = []
        question_msg = None

        for i, question in enumerate(questions):
            embed = discord.Embed(title="Giveaway Setup 🎉", description=question, color=self.color)
            embed.set_footer(text="Giveaway!", icon_url=self.bot.user.avatar.url)

            if i == 0:
                question_msg = await ctx.send(embed=embed)
            else:
                await question_msg.edit(embed=embed)

            try:
                response = await self.bot.wait_for("message", timeout=120, check=check)
                await response.delete()
            except asyncio.TimeoutError:
                await ctx.send(embed=discord.Embed(
                    title="Timed Out",
                    description="You took too long to respond. Please restart the giveaway setup.",
                    color=self.color,
                ))
                return

            answers.append(response.content)

        # ── Validate channel ──────────────────────────────────────────────────
        raw_channel = answers[1]
        if not (raw_channel.startswith("<#") and raw_channel.endswith(">")):
            await ctx.send(f"You didn't mention the channel correctly. Try again like {ctx.channel.mention}.")
            return
        try:
            channel_id = int(raw_channel[2:-1])
        except ValueError:
            await ctx.send(f"Invalid channel mention. Please use {ctx.channel.mention} format.")
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            await ctx.send("I couldn't find that channel. Make sure I have access to it.")
            return

        # ── Validate winners ──────────────────────────────────────────────────
        try:
            winners = abs(int(answers[3]))
            if winners == 0:
                await ctx.send("The number of winners must be a positive integer.")
                return
        except ValueError:
            await ctx.send("You didn't enter a valid number for winners.")
            return

        # ── Validate duration ─────────────────────────────────────────────────
        converted = convert(answers[2])
        if converted == -1:
            await ctx.send("Invalid time unit. Use `s`, `m`, `h`, or `d` (e.g. `30m`, `2h`).")
            return
        elif converted == -2:
            await ctx.send("The time value must be a whole number (e.g. `30m`, not `1.5h`).")
            return

        duration_seconds, duration_label = converted
        prize = answers[0].title()
        end_timestamp = int(time.time()) + duration_seconds

        await init_msg.delete()
        await question_msg.delete()

        # ── Send giveaway embed ───────────────────────────────────────────────
        winner_label = "winner" if winners == 1 else "winners"
        giveaway_embed = discord.Embed(
            title=f"🎉 {prize} 🎉",
            color=self.color,
            description=(
                f"» **{winners}** {winner_label}\n"
                f"» Hosted by {ctx.author.mention}\n\n"
                f"» React with 🎉 to enter!\n"
                f"» **Ends:** <t:{end_timestamp}:F>"
            ),
        )
        giveaway_embed.set_footer(text="Ends at", icon_url=self.bot.user.avatar.url)
        giveaway_embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration_seconds)

        giveaway_msg = await channel.send(embed=giveaway_embed)
        await giveaway_msg.add_reaction("🎉")

        # ── Save to storage ───────────────────────────────────────────────────
        giveaways = load_giveaways()
        giveaways[str(giveaway_msg.id)] = {
            "prize": prize,
            "host": ctx.author.id,
            "winners": winners,
            "end_time": end_timestamp,
            "channel_id": channel.id,
        }
        save_giveaways(giveaways)

    # ── /gstop ────────────────────────────────────────────────────────────────

    @commands.command(name="gstop", aliases=["gwstop"], usage="<giveaway_id>")
    @commands.has_permissions(manage_guild=True)
    async def gstop(self, ctx: commands.Context, message_id: str):
        await ctx.message.delete()
        giveaways = load_giveaways()

        if message_id not in giveaways:
            embed = discord.Embed(
                title="Error",
                description="That giveaway ID wasn't found. Make sure it's correct.",
                color=self.color,
            )
            return await ctx.send(embed=embed)

        await stop_giveaway(self.bot, message_id, giveaways[message_id])


# ── Setup ─────────────────────────────────────────────────────────────────────

async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaways(bot))