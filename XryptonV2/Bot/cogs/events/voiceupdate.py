import discord
from discord.ext import commands
from core import Astroz, Cog
from discord.utils import *
from discord import *
from utils.Tools import *

from discord.utils import get




class Vcroles2(Cog):
    def __init__(self, bot: Astroz):
        self.bot = bot



    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        data = getvcrole(member.guild.id)
        if member.bot:
            role_id = data.get("bots")
            if not role_id:
                return
            if not before.channel and after.channel:
                try:
                    br = get(member.guild.roles, id=role_id)
                    if br:
                        await member.add_roles(br, reason=f"{self.bot.user.name} | VC Roles (Joined VC)")
                except Exception as e:
                    print(e)
            elif before.channel and not after.channel:
                try:
                    br = get(member.guild.roles, id=role_id)
                    if br:
                        await member.remove_roles(br, reason=f"{self.bot.user.name} | VC Roles (Left VC)")
                except Exception as e:
                    print(e)
        else:
            role_id = data.get("humans")
            if not role_id:
                return
            if not before.channel and after.channel:
                try:
                    br = get(member.guild.roles, id=role_id)
                    if br:
                        await member.add_roles(br, reason=f"{self.bot.user.name} | VC Roles (Joined VC)")
                except Exception as e:
                    print(e)
            elif before.channel and not after.channel:
                try:
                    br = get(member.guild.roles, id=role_id)
                    if br:
                        await member.remove_roles(br, reason=f"{self.bot.user.name} | VC Roles (Left VC)")
                except Exception as e:
                    print(e)

async def setup(client):
    await client.add_cog(Vcroles2(client))