import discord
import json
from discord.utils import *
from core import Astroz, Cog
from utils.Tools import *
from discord.ext import commands
from discord.ui import Button, View, LayoutView, Container, Section, TextDisplay, Thumbnail, ActionRow

class WelcomeComponents(LayoutView):    
    def __init__(self, bot: discord.Client):
        super().__init__()
        invite_url = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        self.container1 = Container(
            Section(
                TextDisplay(content="## Thank you for adding me to your server!\n・ My default prefix is `.`\n・ You can use the `.help` command to get list of commands\n・ Feel free to join our Support Server if you need help/support for anything related to the bot"),
                accessory=Thumbnail(
                    media=bot.user.display_avatar.url,
                ),
            ),
            ActionRow(
                Button(
                    url="https://discord.gg/5MTPwCzrk9",
                    style=discord.ButtonStyle.link,
                    label="Support Server",
                ),
                Button(
                    url=invite_url,
                    style=discord.ButtonStyle.link,
                    label="Invite Me!",
                ),
            ),
        )
        self.add_item(self.container1)

class Autorole(Cog):
    def __init__(self, bot: Astroz):
        self.bot = bot
        
        
    @commands.Cog.listener(name="on_member_join")
    async def on_member_join(self, member):
        data = getautorole(member.guild.id)
        arb = data["bots"]
        arh = data["humans"]
        if arb == []:
            return
        else:
            try:
                with open("config.json", "r") as f:
                    conf = json.load(f)
                    bot_name = conf["bot"]["bot_name"]
            except Exception:
                bot_name = self.bot.user.name

            if member.bot:
                for role in arb:
                    try:
                        await member.add_roles(discord.Object(id=int(role)), reason=f"{bot_name} | Autoroles")
                    except Exception as e:
                        print(e)
            else:
                pass                        
                        
    @commands.Cog.listener(name="on_guild_join") 
    async def send_msg_to_adder(self, guild: discord.Guild):
        async for entry in guild.audit_logs(limit=3):  
            if entry.action == discord.AuditLogAction.bot_add: 
                view = WelcomeComponents(self.bot)
                try:
                    await entry.user.send(view=view)
                except Exception as e:
                    print(e)

async def setup(client):
    await client.add_cog(Autorole(client))