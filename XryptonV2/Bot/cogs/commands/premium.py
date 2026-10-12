import discord
from discord.ext import commands,tasks
import os
import sys
import datetime, time
import re
#from dateutil.relativedelta import relativedelta
from typing import Optional, Union, List, Any, Dict
import json
import asyncio
from utils.Tools import *
from utils.config import get_bot_name

anp=[]
def convert(date):
    pos = ["s", "m", "h", "d"]
    time_dic = {"s": 1, "m": 60, "h": 3600, "d": 3600 * 24}
    i = {"s": "Seconds", "m": "Minutes", "h": "Hours", "d": "Days"}
    unit = date[-1]
    if unit not in pos:
        return -1
    try:
        val = int(date[:-1])
    except ValueError:
        return -2
    if val == 1:
        return val * time_dic[unit], i[unit][:-1]
    else:
        return val * time_dic[unit], i[unit]
async def remove_premium(user):

    with open("data/premium.json", "r") as f:
        data = json.load(f)
        user_id_str = str(user.id)
        if user_id_str not in data:
            return
        
        data.pop(user_id_str, None)

    with open("data/premium.json", "w") as f:

        json.dump(data, f, indent=4)

#async def is_guild_premium(guild):

	#with open("data/premium.json", "r") as file:

	#	data = json.load(file)

#	for userId in data:

		#data1 = data[userId]  
  #  if str(guild.id) in data1["premium_guilds"]:
      #  return True  
    #else:
       # return False
    
class Premium(commands.Cog):

    def __init__(self, bot):
 
        self.bot = bot
        self.color = 0x4862DE
        self.premium_remover.start()
        #self._premium = asyncio.Lock()

    def cog_unload(self):
        self.premium_remover.cancel()

    @tasks.loop(minutes=5)
    async def premium_remover(self):
        await self.bot.wait_until_ready()
        try:
            with open("data/premium.json", "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return

        changed = False
        for premium_user in list(data.keys()):
            data2 = data[premium_user]
            if int(time.time()) > data2["expire_at"]:
                del data[premium_user]
                changed = True
        
        if changed:
            with open("data/premium.json", "w") as f:
                json.dump(data, f, indent=4)                         
                       
                
                #remove_premium(data2)

      
    @commands.group(name="prime", aliases=["pre"], invoke_without_command=True)
    @commands.is_owner()
    async def _premium(self, ctx):
        prefix = ctx.prefix
        developer = discord.utils.get(self.bot.users, id=1474988168603242590)

        listem = discord.Embed(
            title=f"Premium (9)",
            colour=self.color,
            description=f"""<...> Duty | [...] Optional\n\n
{prefix}premium add <user> <tier>
Give premium to a user.

{prefix}premium remove <user>
Remove a user from premium list.

{prefix}premium status <user>
Show premium status of user.

""")
        listem.set_author(name=f"{str(ctx.author)}",
                          icon_url=ctx.author.display_avatar.url)
        listem.set_footer(text=f"Made by {str(developer)}",
                          icon_url=developer.avatar.url if developer and developer.avatar else self.bot.user.avatar.url)
        await ctx.send(embed=listem)

    @_premium.command(name="add", aliases=["a", "set"])
    async def _premium_add(self, ctx, user: Union[discord.User, discord.Member], tier_name: str): # type: ignore
        if await self.bot.is_owner(ctx.author):
            with open("data/premium.json", "r") as file:
                data = json.load(file)

            if tier_name.lower() in ["gold", "golden", "g"]:
                tier = "Gold Tier"
                convert_time = "30d"
                guilds = 10
                tier_act = "1 Month"
            elif tier_name.lower() in ["platinum", "platinium", "pltnm"]:
                tier = "Platinum Tier"
                convert_time = "90d"
                guilds = 20
                tier_act = "3 Months"
            elif tier_name.lower() in ["diamond", "💎", "dmnd"]:
                tier = "Diamond Tier"
                convert_time = "365d"
                guilds = 60
                tier_act = "1 Year"
            else:
                return await ctx.send("Invalid tier name. Choose from Gold, Platinum, or Diamond.")

            res = convert(convert_time)
            if isinstance(res, int):
                return await ctx.send("An error occurred calculating the time tier.")

            converted_time_seconds = res[0]
            now = int(time.time())
            data[str(user.id)] = {
                "tier": tier,
                "guild_limit": guilds,
                "premium_guilds": [],
                "expire_at": now + converted_time_seconds
            }

            with open("data/premium.json", "w") as file1:
                json.dump(data, file1, indent=4)

            _e = discord.Embed(
                color=self.color,
                title="",
                description=f"{GreenTick2} | Succesfully activated `{tier}` premium of {user.mention} for `{tier_act}`"
            )
            _e.set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.send(embed=_e)
        else:
            await ctx.send(f"this command can only be used by team members of {get_bot_name()}!")

    @_premium.command(name="status")
    @blacklist_check()
    @ignore_check()
    async def _premium_status(self, ctx, user: Optional[discord.User] = None):
        mem = user or ctx.author
        with open("data/premium.json", "r") as f:
            data = json.load(f)

        if str(mem.id) in data:
            d2 = data[str(mem.id)]
            t = d2["tier"]
            e = d2["expire_at"]

            embed2 = discord.Embed(color=self.color)
            embed2.set_author(
                name=f"Profile For {mem}",
                icon_url=mem.avatar.url if mem.avatar else mem.default_avatar.url)
            embed2.add_field(name=f"{self.bot.user.name}'s Premium", value=f"**`Type`:**{t}\n**`Expire`:**<t:{e}:F>", inline=False)
            embed2.set_thumbnail(
                url=mem.avatar.url if mem.avatar else mem.default_avatar.url)
            await ctx.reply(embed=embed2, mention_author=False)
        else:
            embed = discord.Embed(
                color=self.color,
                description=f"\n\n* Oops! Looks Like {mem} Don't Have Any Type Of Premium Plans To Be Displayed!*"
            )
            embed.set_thumbnail(url=mem.avatar.url if mem.avatar else mem.default_avatar.url)
            embed.set_author(
                name=f"Profile For {mem}",
                icon_url=mem.avatar.url if mem.avatar else mem.default_avatar.url)
            await ctx.send(embed=embed)

    @_premium.command(name="remove", aliases=["r"])
    async def _premium_remove(self, ctx, *, user: Union[discord.User, discord.Member]): # type: ignore
        if await self.bot.is_owner(ctx.author):
            with open("data/premium.json", "r") as ok:
                data = json.load(ok)
            if str(user.id) not in data:
                pass
            else:
                del data[str(user.id)]
                with open("data/premium.json", "w") as ok:
                    json.dump(data, ok, indent=4)
                _e = discord.Embed(
                    color=self.color,
                    title="",
                    description=f"{GreenTick2} | Succesfully removed premium from {user.name} ."
                )
                _e.set_author(
                    name=ctx.author,
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
                )
                await ctx.send(embed=_e)
        else:
            await ctx.send(f"this command can only be used by team members of {self.bot.user.name} !")
            
async def setup(client):
    await client.add_cog(Premium(client))
