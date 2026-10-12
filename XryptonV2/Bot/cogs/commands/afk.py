import discord
from discord.ext import commands
import json
import time
import re
from typing import Optional, Union
from utils.Tools import *
from utils.constants import GreenTick2, xmark

AFK_PATH = "data/afk.json"

INVITE_PATTERN = re.compile(r'(discord\.gg/|\.gg/)', re.IGNORECASE)


def load_afk() -> dict:
    try:
        with open(AFK_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_afk(afk: dict):
    with open(AFK_PATH, 'w') as f:
        json.dump(afk, f)


def default_user_data() -> dict:
    return {
        'AFK': 'False',
        'reason': 'None',
        'time': 0,
        'mentions': 0,
        'guild': [],
        'dm': 'False',
    }


class BasicView(discord.ui.View):
    # This class is fine as a top-level class or nested. The error is not here.
    def __init__(self, ctx: commands.Context, timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                embed=discord.Embed( # Using self.ctx.prefix to make it dynamic
                    description=f"You can't use this. Use **{self.ctx.prefix}afk** to run this command.",
                    color=0x2f3136
                ),
                ephemeral=True
            )
            return False
        return True


class OnOrOff(BasicView):
    # This class is fine as a top-level class or nested. The error is not here.
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx, timeout=60)
        self.value = None

    @discord.ui.button(label="Yes", emoji=GreenTick2, custom_id='Yes', style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = 'Yes'
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="No", emoji=xmark, custom_id='No', style=discord.ButtonStyle.danger)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = 'No'
        await interaction.response.defer()
        self.stop()


class afk(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.color = 0x2f3136 # Initialize color attribute for consistency

    async def _time_formatter(self, seconds: float) -> str:
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60) # This line was already correct
        days, hours = divmod(hours, 24)
        parts = []
        if days:
            parts.append(f"{days} days")
        if hours:
            parts.append(f"{hours} hours")
        if minutes:
            parts.append(f"{minutes} minutes")
        if seconds:
            parts.append(f"{seconds} seconds")
        return ', '.join(parts) if parts else '0 seconds'

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return

        afk = load_afk()

        author_id = str(message.author.id)

        # Ensure author has entry
        if author_id not in afk:
            afk[author_id] = default_user_data()

        # Check if author is returning from AFK
        if afk[author_id]['AFK'] == 'True' and message.guild.id in afk[author_id]['guild']:
            elapsed = time.time() - afk[author_id]['time'] # Use float for elapsed time
            been_afk_for = await self._time_formatter(elapsed)
            mentions = afk[author_id]['mentions']

            afk[author_id]['AFK'] = 'False'
            afk[author_id]['guild'].remove(message.guild.id)
            afk[author_id]['reason'] = 'None'
            afk[author_id]['mentions'] = 0
            save_afk(afk)

            embed = discord.Embed(
                description=(
                    f'Welcome back {message.author.mention}! '
                    f'You got **{mentions}** mention(s) while AFK ' # This line was already correct
                    f'and were away for **{been_afk_for}**.'
                ),
                color=0x2f3136
            )
            await message.channel.send(embed=embed)

            try:
                if message.author.display_name.startswith('[AFK] '):
                    await message.author.edit(nick=message.author.display_name[6:])
            except discord.Forbidden:
                pass

            return

        # Notify if a mentioned user is AFK
        for mentioned_user in message.mentions:
            mentioned_id = str(mentioned_user.id)
            if mentioned_id not in afk:
                continue

            user_data = afk[mentioned_id]
            if user_data['AFK'] != 'True' or message.guild.id not in user_data['guild']:
                continue

            reason = user_data['reason']
            afk_time = user_data['time']

            embed = discord.Embed(
                description=f'{mentioned_user} went AFK <t:{afk_time}:R>, reason: **{reason}**',
                color=self.color # Use self.color for consistency
            )
            await message.channel.send(embed=embed)

            # Track mention count and optionally DM the AFK user
            afk[mentioned_id]['mentions'] = int(user_data['mentions']) + 1
            save_afk(afk)

            if user_data.get('dm') == 'True':
                dm_embed = discord.Embed(
                    description=f'You were mentioned in **{message.guild.name}** by **{message.author}**', # This line was already correct
                    color=self.color # Use self.color for consistency
                )
                dm_embed.add_field(name="Total Mentions", value=afk[mentioned_id]['mentions'], inline=False) # This line was already correct
                dm_embed.add_field(name="Content", value=message.content or '*No content*', inline=False) # This line was already correct
                dm_embed.add_field(name="Message URL", value=f"[Jump to message]({message.jump_url})", inline=False)
                try:
                    await mentioned_user.send(embed=dm_embed)
                except discord.Forbidden:
                    pass

    @commands.hybrid_command(description="Sets AFK status for the user in the server.")
    @commands.guild_only()
    @commands.cooldown(1, 2, commands.BucketType.user)
    @blacklist_check()
    @ignore_check()
    async def afk(self, ctx: commands.Context, *, reason: str = 'None'):
        if INVITE_PATTERN.search(reason):
            embed = discord.Embed(description="You cannot advertise in your AFK reason.", color=0x2f3136)
            return await ctx.send(embed=embed) # This line was already correct

        view = OnOrOff(ctx)
        em = discord.Embed(description="Should the bot DM you when you're mentioned while AFK?", color=self.color) # Use self.color for consistency
        try:
            em.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        except AttributeError:
            em.set_author(name=str(ctx.author))

        prompt_msg = await ctx.reply(embed=em, view=view)
        await view.wait()

        if view.value is None:
            return await prompt_msg.edit(content="Timed out. Re-run `.afk` to try again.", view=None, embed=None)

        afk = load_afk()

        if str(ctx.author.id) not in afk:
            afk[str(ctx.author.id)] = default_user_data()

        user_data = afk[str(ctx.author.id)]
        user_data['AFK'] = 'True'
        user_data['reason'] = reason
        user_data['time'] = int(time.time())
        user_data['mentions'] = 0
        user_data['dm'] = 'True' if view.value == 'Yes' else 'False'

        if ctx.guild.id not in user_data['guild']:
            user_data['guild'].append(ctx.guild.id)

        save_afk(afk)

        await prompt_msg.delete()
        af = discord.Embed(
            description=f'{ctx.author.mention}, your AFK has been set. Reason: **{reason}**',
            color=self.color # Use self.color for consistency
        )
        await ctx.send(embed=af)

        try:
            await ctx.author.edit(nick=f'[AFK] {ctx.author.display_name}'[:32])
        except discord.Forbidden:
            pass


async def setup(client):
    await client.add_cog(afk(client))
