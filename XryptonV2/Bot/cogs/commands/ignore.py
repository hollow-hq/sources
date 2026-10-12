from __future__ import annotations
import discord
from discord.ext import commands, tasks
from core import *
from utils.Tools import *
from typing import Optional
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
from utils.constants import GreenTick2, error

class Ignore(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.color = 0x4862DE

    @commands.group(name="ignore", invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    async def _ignore(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @_ignore.group(name="channel",
                   aliases=["chnl"],
                   invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @blacklist_check()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _channel(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @_channel.command(name="add")
    @commands.has_permissions(administrator=True)
    async def channel_add(self, ctx: Context, channel: discord.TextChannel):
        data = getIgnore(ctx.guild.id)
        ch= data["channel"]
        if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
            if str(channel.id) in ch:
                embed = discord.Embed(
                        description=
                        f"| {channel.mention} is already in ignore channel list .",
                    color=self.color)
                await ctx.reply(embed=embed, mention_author=False)
            else:
                ch.append(str(channel.id))
                updateIgnore(ctx.guild.id, data)
                success_embed = discord.Embed(
                    color=self.color,
                    description=f"{GreenTick2} | Successfully added {channel.mention} to ignore channel list .")
                success_embed.set_author(
                    name=ctx.author,
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=success_embed)
        else:
            perm_embed = discord.Embed(
                description="""```yaml\n - You must have Administrator permission.\n - Your top role should be above my top role.```""",
                color=self.color)
            perm_embed.set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.reply(embed=perm_embed)

    @_channel.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def channel_remove(self, ctx, channel: discord.TextChannel):
        data = getIgnore(ctx.guild.id)
        ch= data["channel"]
        if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:   
            if len(ch) == 0:
                error_embed = discord.Embed(
                    color=self.color,
                    description=
                    f"{error} | This server dont have any ignore channel setupped yet .")
                error_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=error_embed)   
            else:
                if str(channel.id) not in ch:   
                    error_embed = discord.Embed(
                        color=self.color,
                        description=
                        f"{error} | This channel is not in the ignore channels list .")
                    error_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                    await ctx.send(embed=error_embed) 
                else:
                    ch.remove(str(channel.id))
                    updateIgnore(ctx.guild.id, data)
                    success_embed = discord.Embed(
                        color=self.color,
                        description=
                        f"{GreenTick2} | Successfully removed {channel.mention} from ignore channel list .")
                    success_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                    await ctx.send(embed=success_embed)
        else:
            perm_embed = discord.Embed(
                description=
                """```yaml\n - You must have Administrator permission.\n - Your top role should be above my top role.```""",
                color=self.color)
            perm_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.reply(embed=perm_embed)                    
                    

######################



                    
################

    @_ignore.group(name="user",
                   aliases=["member", "u"],
                   invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @blacklist_check()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _user(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)
            
            
            
    @_user.command(name="add")
    @commands.has_permissions(administrator=True)
    async def user_add(self, ctx: Context, user: discord.User):
        data = getIgnore(ctx.guild.id)
        ch= data["user"]
        if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
            if str(user.id) in ch:
                embed = discord.Embed(
                        description=
                        f"| {user.mention} is already in ignore users list .",
                        color=self.color)
                await ctx.reply(embed=embed, mention_author=False)
            else:
                ch.append(str(user.id))
                updateIgnore(ctx.guild.id, data)
                success_embed = discord.Embed(
                        color=self.color,
                        description=
                        f"{GreenTick2} | Successfully added {user.mention} to ignore users list .")
                success_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=success_embed)
        else:
            perm_embed = discord.Embed(
                description=
                """```yaml\n - You must have Administrator permission.\n - Your top role should be above my top role.```""",
                color=self.color)
            perm_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.reply(embed=perm_embed)

    @_user.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def user_remove(self, ctx, user: discord.User):
        data = getIgnore(ctx.guild.id)
        ch= data["user"]
        if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:   
            if len(ch) == 0:
                error_embed = discord.Embed(
                    color=self.color,
                    description=
                    f"{error} | This server dont have any ignore users setupped yet .")
                error_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=error_embed)   
            else:
                if str(user.id) not in ch:   
                    error_embed = discord.Embed(
                        color=self.color,
                        description=
                        f"{error} | {user.mention} is not in the ignore users list .")
                    error_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                    await ctx.send(embed=error_embed) 
                else:
                    ch.remove(str(user.id))
                    updateIgnore(ctx.guild.id, data)
                    success_embed = discord.Embed(
                        color=self.color,
                        description=
                        f"{GreenTick2} | Successfully removed {user.mention} from ignore users list .")
                    success_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                    await ctx.send(embed=success_embed)
        else:
            perm_embed = discord.Embed(
                description=
                """```yaml\n - You must have Administrator permission.\n - Your top role should be above my top role.```""",
                color=self.color)
            perm_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.reply(embed=perm_embed)                   
                    
                    
###################






    @_ignore.group(name="bypass", invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    async def _bypass(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

                    
                    




            
            
            
################

    @_bypass.group(name="user",
                   aliases=["member", "u"],
                   invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @blacklist_check()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _buser(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)
            
            
            
    @_buser.command(name="add")
    @commands.has_permissions(administrator=True)
    async def buser_add(self, ctx: Context, user: discord.User):
        data = getIgnore(ctx.guild.id)
        ch= data["bypassuser"]
        if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:
            if str(user.id) in ch:
                embed = discord.Embed(
                        description=
                        f"| {user.mention} is already in bypass users list .",
                        color=self.color)
                await ctx.reply(embed=embed, mention_author=False)
            else:
                ch.append(str(user.id))
                updateIgnore(ctx.guild.id, data)
                success_embed = discord.Embed(
                        color=self.color,
                        description=
                        f"{GreenTick2} | Successfully added {user.mention} to bypass users list .")
                success_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=success_embed)
        else:
            perm_embed = discord.Embed(
                description=
                """```yaml\n - You must have Administrator permission.\n - Your top role should be above my top role.```""",
                color=self.color)
            perm_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.reply(embed=perm_embed)

    @_buser.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def buser_remove(self, ctx, user: discord.User):
        data = getIgnore(ctx.guild.id)
        ch= data["bypassuser"]
        if ctx.author == ctx.guild.owner or ctx.author.top_role.position > ctx.guild.me.top_role.position:   
            if len(ch) == 0:
                error_embed = discord.Embed(
                    color=self.color,
                    description=
                    f"{error} | This server dont have any bypass users setupped yet .")
                error_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                await ctx.send(embed=error_embed)   
            else:
                if str(user.id) not in ch:   
                    error_embed = discord.Embed(
                        color=self.color,
                        description=
                        f"{error} | {user.mention} is not in the bypass users list .")
                    error_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                    await ctx.send(embed=error_embed) 
                else:
                    ch.remove(str(user.id))
                    updateIgnore(ctx.guild.id, data)
                    success_embed = discord.Embed(
                        color=self.color,
                        description=
                        f"{GreenTick2} | Successfully removed {user.mention} from bypass users list .")
                    success_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                    await ctx.send(embed=success_embed)
        else:
            perm_embed = discord.Embed(
                description=
                """```yaml\n - You must have Administrator permission.\n - Your top role should be above my top role.```""",
                color=self.color)
            perm_embed.set_author(name=ctx.author,
                                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            await ctx.reply(embed=perm_embed)
            
            
            
 
            
 
    @_user.command(name="show",
                        help="Shows list of ignored users in the server .",
                        usage="ignore user show")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def iuser_show(self, ctx):
        data = getIgnore(ctx.guild.id)
        ch= data["user"] 
        if len(ch) == 0:
            error_embed = discord.Embed(
                color=self.color,
                title=f"{self.client.user.name}",
                description=
                f"{error} | There aren\'t any ignored users for this server"
            )
            await ctx.reply(embed=error_embed, mention_author=False)
        else:
            entries = [
                f"`{no}` | <@!{idk}> | ID: [{idk}](https://discord.com/users/{idk})"
                for no, idk in enumerate(ch, start=1)
            ]
            paginator = Paginator(source=DescriptionEmbedPaginator(
                entries=entries,
                title=f"Ignored Users of {ctx.guild.name} - {len(ch)}",
                description="",
                color=self.color),
                                  ctx=ctx)
            await paginator.paginate()
            
            
            
    @_buser.command(name="show",
                        help="Shows list of ignore bypass users in the server .",
                        usage="ignore user show")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 4, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def buser_show(self, ctx):
        data = getIgnore(ctx.guild.id)
        ch= data["bypassuser"] 
        if len(ch) == 0:
            error_embed = discord.Embed(
                color=self.color,
                title=f"{self.client.user.name}",
                description=
                f"{error} | There aren\'t any ignore bypass users for this server"
            )
            await ctx.reply(embed=error_embed, mention_author=False)
        else:
            entries = [
                f"`{no}` | <@!{idk}> | ID: [{idk}](https://discord.com/users/{idk})"
                for no, idk in enumerate(ch, start=1)
            ]
            paginator = Paginator(source=DescriptionEmbedPaginator(
                entries=entries,
                title=f"Ignore Bypass Users of {ctx.guild.name} - {len(ch)}",
                description="",
                color=self.color),
                                  ctx=ctx)
            await paginator.paginate()
            
async def setup(client):
    await client.add_cog(Ignore(client))
