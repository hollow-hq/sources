from discord.ext import commands
from core import Astroz, Cog
import discord, requests
import json
from utils.Tools import *
from discord.ui import Button, View, LayoutView, Container, Section, TextDisplay, Thumbnail, ActionRow, Separator, MediaGallery
import logging
from discord import Webhook

joinhook = "https://ptb.discord.com/api/webhooks/1517801936336715897/gH4ndc5e6dkBrE10dThq_BirUQ8FdiqGRr8eNbV2okBtapnuQsxhmTiGQIboiro0EnL0"
leavehook = "https://ptb.discord.com/api/webhooks/1517802184165687408/bJZ3zHKYNT-c2xHWkF1xUPoSVACobZ95ldLPPjUZ5ZoRRwwn4Q81T58HLyPrhqDyBD1Y"

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

class LogComponents(LayoutView):    
    def __init__(self, bot: discord.Client, guild: discord.Guild, title: str, g_before: int, g_after: int, u_before: int, u_after: int, invite_info: str = None):
        super().__init__()
        banner = guild.banner.url if guild.banner else "https://placehold.co/500x350"
        invite_line = f"\n**Invite Info:** {invite_info}" if invite_info else ""
        self.container1 = Container(
            Section(
                TextDisplay(content=f"# {title}\n__**Guild Information**__\nServer Name: `{guild.name}`\nServer ID: `{guild.id}`\nOwner: {guild.owner} \nMembers: [**`{guild.member_count}`**]\nRoles: [{len(guild.roles)}]\nChannels: [{len(guild.channels)}]\n{invite_line}"),
                accessory=Thumbnail(
                    media=bot.user.display_avatar.url,
                ),
            ),
            Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            TextDisplay(content=f"## __BOT INFO__\n**Guild Count**\nGuild Count After: {g_after}\nGuild Count Before: {g_before}\n**Member Count**\nMember Count After: {u_after}\nMember Count Before: {u_before}"),
            MediaGallery(
                discord.MediaGalleryItem(
                    media=banner,
                ),
            ),
        )
        self.add_item(self.container1)


class Guild(Cog):

  def __init__(self, client: Astroz):
    self.client = client

  @commands.Cog.listener(name="on_guild_join")
  async def hacker(self, guild):
    rope = [
      inv for inv in await guild.invites()
      if inv.max_age == 0 and inv.max_uses == 0
    ]
    me = discord.SyncWebhook.from_url(joinhook)
    
    channels = len(set(self.client.get_all_channels()))
    
    users = sum(g.member_count for g in self.client.guilds
                if g.member_count != None)
    
    g_after = len(self.client.guilds)
    g_before = g_after - 1
    u_after = users
    u_before = users - (guild.member_count or 0)

    invite_text = f"{guild.id} | {rope[0]}" if rope else f"{guild.id} | No Pre-Made Invite Found"
    view = LogComponents(self.client, guild, "Bot Joined New Server", g_before, g_after, u_before, u_after, invite_info=invite_text)
    try:
        me.send(view=view)
    except Exception as e:
        print(f"Failed to send join log: {e}")

    if not guild.chunked:
      await guild.chunk()
    view = WelcomeComponents(self.client)
    channel = discord.utils.get(guild.text_channels, name="general")
    if not channel:
      channels = [
        channel for channel in guild.text_channels
        if channel.permissions_for(guild.me).send_messages
      ]
      channel = channels[0]
      await channel.send(view=view)
      return 

  @commands.Cog.listener(name="on_guild_remove")
  async def on_g_remove(self, guild):
    hook = discord.SyncWebhook.from_url(leavehook)
    channels = len(set(self.client.get_all_channels()))
    users = sum(g.member_count for g in self.client.guilds
                if g.member_count != None)
    
    g_after = len(self.client.guilds)
    g_before = g_after + 1
    u_after = users
    u_before = users + (guild.member_count or 0)

    view = LogComponents(self.client, guild, "Bot Left Server", g_before, g_after, u_before, u_after)
    try:
        hook.send(view=view)
    except Exception as e:
        print(f"Failed to send leave log: {e}")
    return 

async def setup(client):
    await client.add_cog(Guild(client))