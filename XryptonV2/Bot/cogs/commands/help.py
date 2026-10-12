import discord
from discord.ext import commands
from difflib import get_close_matches
from contextlib import suppress
from core import Context
from core.Astroz import Astroz
from core.Cog import Cog
from utils.Tools import getConfig
from itertools import chain
import json
from utils import help as vhelp
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
import asyncio
from utils.Tools import *
from utils.constants import Extra as EXTRA_CONST

color = 0x4862DE

class HelpListView(discord.ui.LayoutView):
    def __init__(self, command_name: str, count: int, commands_text: str):
        super().__init__()
        self.container1 = discord.ui.Container(
            discord.ui.TextDisplay(content=f"## {command_name} - [{count}]\n<...> is required | [...] is optional\n{commands_text}"),
        )
        self.add_item(self.container1)


class HelpCommand(commands.HelpCommand):
    async def on_help_command_error(self, ctx, error):
        damn = [
            commands.CommandOnCooldown, commands.CommandNotFound,
            discord.HTTPException, commands.CommandInvokeError
        ]
        if not type(error) in damn:
            await self.context.reply(f"Unknown Error Occurred\n{error.original}", mention_author=False)
        else:
            if type(error) == commands.CommandOnCooldown:
                return
            return await super().on_help_command_error(ctx, error)

    async def command_not_found(self, string: str) -> None:
        with open('data/blacklist.json', 'r') as f:
            bled = json.load(f)
        data = getIgnore(self.context.guild.id)
        ch = data["channel"]
        iuser = data["user"]
        buser = data["bypassuser"]
        bl = discord.Embed(
            description="You are blacklisted from using my commannds.\nreason could be excessive use or spamming commands\nJoin our [Support Server](https://discord.gg/dGx99V37xx) to appeal .",
            color=discord.Colour(0x2f3136)
        )
        embed = discord.Embed(
            description="This Channel is in ignored channel list try my commands in another channel .",
            color=discord.Colour(0x2f3136)
        )
        ign = discord.Embed(
            description=f"You are set as a ignored users for {self.context.guild.name} .\nTry my commands or modules in another guild .",
            color=discord.Colour(0x2f3136)
        )

        if str(self.context.author.id) in bled["ids"]:
            return

        if str(self.context.author.id) in iuser and str(self.context.author.id) not in buser:
            return

        if self.context.channel.id in ch and self.context.author.id not in buser:
            return
        else:
            if string.lower() in ("security", "anti", "antinuke"):
                cog = self.context.bot.get_cog("Antinuke")
                with suppress(discord.HTTPException):
                    await self.send_cog_help(cog)
            else:
                msg = f"Command `{string}` is not found...\n"
                hacker = await self.context.bot.fetch_user(1474988168603242590)
                cmds = (str(cmd) for cmd in self.context.bot.walk_commands())
                mtchs = get_close_matches(string, cmds)
                if mtchs:
                    for okaay, okay in enumerate(mtchs, start=1):
                        msg += f"Did You Mean: \n`[{okaay}]`. `{okay}`\n"
                return msg

    async def send_bot_help(self, mapping):
        with open('data/blacklist.json', 'r') as f:
            bled = json.load(f)
        data = getIgnore(self.context.guild.id)
        ch = data["channel"]
        iuser = data["user"]
        buser = data["bypassuser"]
        bl = discord.Embed(
            description="You are blacklisted from using my commannds.\nreason could be excessive use or spamming commands\nJoin our [Support Server](https://discord.gg/dGx99V37xx) to appeal .",
            color=discord.Colour(0x2f3136)
        )
        embed = discord.Embed(
            description="This Channel is in ignored channel list try my commands in another channel .",
            color=discord.Colour(0x2f3136)
        )
        ign = discord.Embed(
            description=f"You are set as a ignored users for {self.context.guild.name} .\nTry my commands or modules in another guild .",
            color=discord.Colour(0x2f3136)
        )

        if str(self.context.author.id) in bled["ids"]:
            return

        if str(self.context.author.id) in iuser and str(self.context.author.id) not in buser:
            return

        if self.context.channel.id in ch and self.context.author.id not in buser:
            return

        wait_embed = discord.Embed(
            description=f"**Processing the command...**",
            color=color
        )
        ok = await self.context.reply(embed=wait_embed)
        data = getConfig(self.context.guild.id)
        prefix = data["prefix"]
        filtered = await self.filter_commands(self.context.bot.walk_commands(), sort=True)
        view = vhelp.Components(mapping=mapping, ctx=self.context, prefix=prefix)
        await ok.delete()
        await self.context.send(view=view)

    async def send_command_help(self, command):
        with open('data/blacklist.json', 'r') as f:
            bled = json.load(f)
        data = getIgnore(self.context.guild.id)
        ch = data["channel"]
        iuser = data["user"]
        buser = data["bypassuser"]
        bl = discord.Embed(
            description="You are blacklisted from using my commannds.\nreason could be excessive use or spamming commands\nJoin our [Support Server](https://discord.gg/dGx99V37xx) to appeal .",
            color=discord.Colour(0x2f3136)
        )
        embed = discord.Embed(
            description="This Channel is in ignored channel list try my commands in another channel .",
            color=discord.Colour(0x2f3136)
        )
        ign = discord.Embed(
            description=f"You are set as a ignored users for {self.context.guild.name} .\nTry my commands or modules in another guild .",
            color=discord.Colour(0x2f3136)
        )

        if str(self.context.author.id) in bled["ids"]:
            return

        if str(self.context.author.id) in iuser and str(self.context.author.id) not in buser:
            return

        if self.context.channel.id in ch and self.context.author.id not in buser:
            return
        else:
            data = getConfig(self.context.guild.id)
            prefix = data["prefix"]
            alias = ' | '.join(command.aliases) if command.aliases else 'None'
            desc = command.help if command.help else 'No description provided'
            usage = f"{command.qualified_name} {command.usage or command.signature}".strip()

            embed = discord.Embed(
                color=4743902,
                title=f"{command.name}",
                description=f"Command: `{prefix}{command.qualified_name}`\nUsage: `{prefix}{usage}`\nAlias: {alias}\nDescription: {desc}\n```diff\n+ [] = optional argument\n+ <> = required argument```",
            )
            embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/YqsSL0Nh8UfQoiFDtOhk8ciVynEpGm4zIv_C36JvxsQ/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/1482613924703764541/afb5d4c0778c3012ed5b36449b4e0bb5.png?format=webp&quality=lossless&width=355&height=355")
            embed.set_footer(text=f"{command.cog.qualified_name.title()} module")
            await self.context.reply(embed=embed, mention_author=False)

    async def send_missing_argument_help(self, command, argument):
        with open('data/blacklist.json', 'r') as f:
            bled = json.load(f)
        data = getIgnore(self.context.guild.id)
        ch = data["channel"]
        iuser = data["user"]
        buser = data["bypassuser"]
        bl = discord.Embed(
            description="You are blacklisted from using my commannds.\nreason could be excessive use or spamming commands\nJoin our [Support Server](https://discord.gg/dGx99V37xx) to appeal .",
            color=discord.Colour(0x2f3136)
        )
        embed = discord.Embed(
            description="This Channel is in ignored channel list try my commands in another channel .",
            color=discord.Colour(0x2f3136)
        )
        ign = discord.Embed(
            description=f"You are set as a ignored users for {self.context.guild.name} .\nTry my commands or modules in another guild .",
            color=discord.Colour(0x2f3136)
        )

        if str(self.context.author.id) in bled["ids"]:
            return

        if str(self.context.author.id) in iuser and str(self.context.author.id) not in buser:
            return

        if self.context.channel.id in ch and self.context.author.id not in buser:
            return
        else:
            data = getConfig(self.context.guild.id)
            prefix = data["prefix"]
            alias = ' | '.join(command.aliases) if command.aliases else 'None'
            desc = command.help if command.help else 'No description provided'
            usage = f"{command.qualified_name} {command.usage or command.signature}".strip()

            embed = discord.Embed(
                color=4743902,
                title=f"Missing Argument: {argument}",
                description=f"Command: `{prefix}{command.qualified_name}`\nUsage: `{prefix}{usage}`\nAlias: {alias}\nDescription: {desc}\n```diff\n+ [] = optional argument\n+ <> = required argument```",
            )
            embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/YqsSL0Nh8UfQoiFDtOhk8ciVynEpGm4zIv_C36JvxsQ/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/1482613924703764541/afb5d4c0778c3012ed5b36449b4e0bb5.png?format=webp&quality=lossless&width=355&height=355")
            embed.set_footer(text=f"{command.cog.qualified_name.title()} module")
            await self.context.reply(embed=embed, mention_author=False)

    def get_command_signature(self, command: commands.Command) -> str:
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = ' | '.join(command.aliases)
            fmt = f'[{command.name} | {aliases}]'
            if parent:
                fmt = f'{parent}'
            alias = f'[{command.name} | {aliases}]'
        else:
            alias = command.name if not parent else f'{parent} {command.name}'
        return f'{alias} {command.signature}'

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f'{command.description}\n\n{command.help}'
        else:
            embed_like.description = command.help or 'No help found...'

    async def send_group_help(self, group):
        with open('data/blacklist.json', 'r') as f:
            bled = json.load(f)
        data = getIgnore(self.context.guild.id)
        ch = data["channel"]
        iuser = data["user"]
        buser = data["bypassuser"]
        bl = discord.Embed(
            description="You are blacklisted from using my commannds.\nreason could be excessive use or spamming commands\nJoin our [Support Server](https://discord.gg/dGx99V37xx) to appeal .",
            color=discord.Colour(0x2f3136)
        )
        embed = discord.Embed(
            description="This Channel is in ignored channel list try my commands in another channel .",
            color=discord.Colour(0x2f3136)
        )
        ign = discord.Embed(
            description=f"You are set as a ignored users for {self.context.guild.name} .\nTry my commands or modules in another guild .",
            color=discord.Colour(0x2f3136)
        )

        if str(self.context.author.id) in bled["ids"]:
            return

        if str(self.context.author.id) in iuser and str(self.context.author.id) not in buser:
            return

        if self.context.channel.id in ch and self.context.author.id not in buser:
            return
        else:
            prefix = self.context.prefix
            count = len(group.commands)
            cmd_names = "\n".join([f"`{prefix}{cmd.qualified_name}`" for cmd in group.commands])
            view = HelpListView(group.qualified_name, count, cmd_names)
            await self.context.reply(view=view, mention_author=False)

    async def send_cog_help(self, cog):
        with open('data/blacklist.json', 'r') as f:
            bled = json.load(f)
        data = getIgnore(self.context.guild.id)
        ch = data["channel"]
        iuser = data["user"]
        buser = data["bypassuser"]
        bl = discord.Embed(
            description="You are blacklisted from using my commannds.\nreason could be excessive use or spamming commands\nJoin our [Support Server](https://discord.gg/dGx99V37xx) to appeal .",
            color=discord.Colour(0x2f3136)
        )
        embed = discord.Embed(
            description="This Channel is in ignored channel list try my commands in another channel .",
            color=discord.Colour(0x2f3136)
        )
        ign = discord.Embed(
            description=f"You are set as a ignored users for {self.context.guild.name} .\nTry my commands or modules in another guild .",
            color=discord.Colour(0x2f3136)
        )

        if str(self.context.author.id) in bled["ids"]:
            return

        if str(self.context.author.id) in iuser and str(self.context.author.id) not in buser:
            return

        if self.context.channel.id in ch and self.context.author.id not in buser:
            return

        prefix = self.context.prefix
        cmds = cog.get_commands()
        count = len(cmds)
        cmd_names = "\n".join([f"`{prefix}{cmd.qualified_name}`" for cmd in cmds])
        view = HelpListView(cog.qualified_name.title(), count, cmd_names)
        await self.context.reply(view=view, mention_author=False)


class Help(Cog, name="help"):

    def __init__(self, client: Astroz):
        self._original_help_command = client.help_command
        attributes = {
            'name': "help",
            'aliases': ['h'],
            'cooldown': commands.CooldownMapping.from_cooldown(1, 5, commands.BucketType.user),
            'help': 'Shows help about bot, a command or a category'
        }
        client.help_command = HelpCommand(command_attrs=attributes)
        client.help_command.cog = self

    async def cog_unload(self):
        self.help_command = self._original_help_command


async def setup(client):
    await client.add_cog(Help(client))
