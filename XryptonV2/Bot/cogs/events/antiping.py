import os
import discord
from discord.ext import commands
import requests
import sys
from cogs.events import antiemostick
from utils.Tools import getConfig, add_user_to_blacklist, getanti
import setuptools
from itertools import cycle
from collections import Counter
import threading
import datetime
import logging
from core import Astroz, Cog
import time
import asyncio
import aiohttp
import tasksio
from discord.ui import View, Button
import json
from discord.ext import tasks
import random
from utils.Tools import *



proxies = open('proxies.txt').read().split('\n')
proxs = cycle(proxies)
proxies={"http": 'http://' + next(proxs)}

class antipinginv(Cog):
    def __init__(self, client: Astroz):
        self.client = client
        self.spam_control = commands.CooldownMapping.from_cooldown(10, 12.0, commands.BucketType.user)

    @commands.Cog.listener()
    async def on_message(self, message):
      try:
       
        with open("data/blacklist.json", "r") as f:
          data2 = json.load(f)
          astroz = f'<@{self.client.user.id}>'
          try:
            data = getConfig(message.guild.id)
            anti = getanti(message.guild.id)
            event= getHacker(message.guild.id)
            antievent = event["antinuke"]["antiping"]
            prefix = data["prefix"]
            wled = data["whitelisted"]
            punishment = data["punishment"]
            wlrole = data['wlrole']
            guild = message.guild

          except Exception:
            pass
          guild = message.guild
          if message.mention_everyone:
            if str(message.author.id) in wled or anti == "off" or antievent == False or message.author.id == guild.owner.id:
              pass
            else:
              if punishment == "ban":
                await message.delete()
                await message.guild.ban(message.author, reason="Mentioning Everyone | Not Whitelisted")
                return 
              elif punishment == "kick":
                await message.delete()
                await message.guild.kick(message.author, reason="Mentioning Everyone | Not Whitelisted")
                return 
              elif punishment == "none":
                return


          elif message.content == astroz or message.content == f"<@!{self.client.user.id}>":
            if str(message.author.id) in data2["ids"] or message.author.bot:
              pass
                
                
            else:
              view = discord.ui.LayoutView()
              view.add_item(
                discord.ui.Container(
                  discord.ui.Section(
                    discord.ui.TextDisplay(
                      content=f"# {message.author.display_name}\n\n> my prefix is `{prefix}`\n> use `{prefix}help` to use all commands"
                    ),
                    accessory=discord.ui.Thumbnail(
                      media=message.author.display_avatar.url,
                    ),
                  ),
                )
              )
              await message.reply(view=view, mention_author=True)
              return 
          else:
            return
      except Exception as error:
        if isinstance(error, discord.Forbidden):
              return


async def setup(client):
    await client.add_cog(antipinginv(client))