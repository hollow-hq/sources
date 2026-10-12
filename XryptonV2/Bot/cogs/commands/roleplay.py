import discord
from discord.ext import commands
import nekosbest
import json
import os

class Components(discord.ui.LayoutView):    
    def __init__(self, user: str, action: str, target: str, url: str):
        super().__init__()
        self.container1 = discord.ui.Container(
            discord.ui.TextDisplay(content=f"# {user} just {action} {target} for the **first** time!"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media=url,
                ),
            ),
        )

def get_ordinal(n: int) -> str:
    """Returns the ordinal number (1st, 2nd, 3rd, etc.) for an integer."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

def load_counts():
    """Loads roleplay counts from local storage."""
    try:
        with open("data/roleplay_counts.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_counts(data):
    """Saves roleplay counts to local storage."""
    os.makedirs("data", exist_ok=True)
    with open("data/roleplay_counts.json", "w") as f:
        json.dump(data, f, indent=4)

class Roleplay(commands.Cog, name='RoleplayCommands'):
    """Fun roleplay commands like hug, kiss, and slap!"""

    def __init__(self, bot):
        self.bot = bot
        self.nekos_client = nekosbest.Client()

    async def cog_unload(self):
        await self.nekos_client.close()

    async def _execute_action(self, ctx, action: str, past_tense: str, target: discord.Member):
        if target is None:
            tar_id = "0"
            target_display = "the void"
        else:
            tar_id = str(target.id)
            target_display = target.display_name

        data = load_counts()
        auth_id = str(ctx.author.id)
        if auth_id not in data: data[auth_id] = {}
        if tar_id not in data[auth_id]: data[auth_id][tar_id] = {}
        
        count = data[auth_id][tar_id].get(action, 0) + 1
        data[auth_id][tar_id][action] = count
        save_counts(data)

        try:
            result = await self.nekos_client.get_image(action)
            embed = discord.Embed(
                description=f"### {ctx.author.display_name} {past_tense} {target_display} for the **{get_ordinal(count)}** time!",
                color=0x2f3136
            )
            embed.set_image(url=result.url)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    # ==========================================
    #               ROLEPLAY COMMANDS           
    # ==========================================

    @commands.command()
    async def angry(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "angry", "got angry at", target)

    @commands.command()
    async def baka(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "baka", "called", target)

    @commands.command()
    async def bite(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "bite", "bit", target)

    @commands.command()
    async def bleh(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "bleh", "went bleh at", target)

    @commands.command()
    async def blowkiss(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "blowkiss", "blew a kiss to", target)

    @commands.command()
    async def blush(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "blush", "blushed at", target)

    @commands.command()
    async def bonk(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "bonk", "bonked", target)

    @commands.command()
    async def bored(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "bored", "looked bored at", target)

    @commands.command()
    async def carry(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "carry", "carried", target)

    @commands.command()
    async def clap(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "clap", "clapped for", target)

    @commands.command()
    async def confused(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "confused", "looked confused at", target)

    @commands.command()
    async def cry(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "cry", "cried on", target)

    @commands.command()
    async def cuddle(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "cuddle", "cuddled", target)

    @commands.command()
    async def dance(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "dance", "danced with", target)

    @commands.command()
    async def facepalm(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "facepalm", "facepalmed at", target)

    @commands.command()
    async def feed(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "feed", "fed", target)

    @commands.command()
    async def handhold(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "handhold", "held hands with", target)

    @commands.command()
    async def handshake(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "handshake", "shook hands with", target)

    @commands.command()
    async def happy(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "happy", "smiled happily at", target)

    @commands.command()
    async def highfive(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "highfive", "high-fived", target)

    @commands.command()
    async def hug(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "hug", "hugged", target)

    @commands.command()
    async def kabedon(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "kabedon", "kabedoned", target)

    @commands.command()
    async def kiss(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "kiss", "kissed", target)

    @commands.command()
    async def lappillow(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "lappillow", "gave a lap pillow to", target)

    @commands.command()
    async def laugh(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "laugh", "laughed at", target)

    @commands.command()
    async def lurk(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "lurk", "lurked near", target)

    @commands.command()
    async def nod(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "nod", "nodded at", target)

    @commands.command()
    async def nom(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "nom", "nommed on", target)

    @commands.command()
    async def nope(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "nope", "noped away from", target)

    @commands.command()
    async def nya(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "nya", "meowed at", target)

    @commands.command()
    async def pat(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "pat", "patted", target)

    @commands.command()
    async def peck(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "peck", "pecked", target)

    @commands.command()
    async def poke(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "poke", "poked", target)

    @commands.command()
    async def pout(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "pout", "pouted at", target)

    @commands.command()
    async def punch(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "punch", "punched", target)

    @commands.command()
    async def run(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "run", "ran away from", target)

    @commands.command()
    async def salute(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "salute", "saluted", target)

    @commands.command()
    async def shake(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "shake", "shook", target)

    @commands.command()
    async def shoot(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "shoot", "shot", target)

    @commands.command()
    async def shocked(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "shocked", "was shocked by", target)

    @commands.command()
    async def shrug(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "shrug", "shrugged at", target)

    @commands.command()
    async def sip(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "sip", "sipped drinks with", target)

    @commands.command()
    async def slap(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "slap", "slapped", target)

    @commands.command()
    async def sleep(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "sleep", "slept next to", target)

    @commands.command()
    async def smile(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "smile", "smiled at", target)

    @commands.command()
    async def smug(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "smug", "smugged at", target)

    @commands.command()
    async def spin(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "spin", "spun around with", target)

    @commands.command()
    async def stare(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "stare", "stared at", target)

    @commands.command()
    async def tableflip(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "tableflip", "flipped a table at", target)

    @commands.command()
    async def teehee(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "teehee", "giggled at", target)

    @commands.command()
    async def think(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "think", "thought about", target)

    @commands.command()
    async def thumbsup(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "thumbsup", "gave a thumbs up to", target)

    @commands.command()
    async def tickle(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "tickle", "tickled", target)

    @commands.command()
    async def wag(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "wag", "wagged their tail at", target)

    @commands.command()
    async def wave(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "wave", "waved at", target)

    @commands.command()
    async def wink(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "wink", "winked at", target)

    @commands.command()
    async def yawn(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "yawn", "yawned at", target)

    @commands.command()
    async def yet(self, ctx, target: discord.Member = None):
        await self._execute_action(ctx, "yet", "yeeted", target)

async def setup(bot):
    await bot.add_cog(Roleplay(bot))