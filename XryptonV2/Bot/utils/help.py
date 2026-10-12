import discord
import json
import functools
from utils.Tools import *
from utils.constants import error
from .dropdown import HelpDropdown


class Components(discord.ui.LayoutView):
    def __init__(self, mapping: dict, ctx: discord.ext.commands.context.Context, prefix: str):
        super().__init__()
        self.mapping, self.ctx, self.prefix = mapping, ctx, prefix
        self.index = 0
        self.options = self._gen_options()
        self.invoker = ctx.author
        self.bot_avatar = self.ctx.bot.user.display_avatar.url
        
        try:
            with open("config.json", "r") as f:
                conf = json.load(f)
                bot_name = conf["bot"]["bot_name"]
        except Exception:
            bot_name = self.ctx.bot.user.name

        cogs = self._get_cogs()
        module_list = ""
        for cog in cogs:
            emoji, label, description = cog.help_custom()
            module_list += f"{emoji} **{label}** - {description}\n"

        self.home_text = (
            f"> # {bot_name} Help\n"
            f"> Welcome to **{bot_name}**, the future of discord bots\n"
            f"> `{len(set(self.ctx.bot.walk_commands()))}` Total Commands\n"
            f"## My Modules Include:\n"
            f"> Moderation & Automod\n"
            f"> Antinuke & Antiraid\n"
            f"> Utility & Fun\n"
            f"> Logging, Vanity, Embed Scripting & much, much more!\n"
        )

        self._build_view()
        
    def _build_view(self):
        self.main_text = discord.ui.TextDisplay(content=self.home_text)
        
        select_options = self.options if self.options else [discord.SelectOption(label="No modules available")]
        select = HelpDropdown(self, select_options)
        
        self.startB = Buttons(label="≪", style=discord.ButtonStyle.blurple, command=self.set_page, args=0, ctx=self.ctx)
        self.backB = Buttons(label="Back", style=discord.ButtonStyle.success, command=self.to_page, args=-1, ctx=self.ctx)
        self.nextB = Buttons(label="Next", style=discord.ButtonStyle.success, command=self.to_page, args=+1, ctx=self.ctx)
        self.endB = Buttons(label="≫", style=discord.ButtonStyle.blurple, command=self.set_page, args=len(self.options) - 1, ctx=self.ctx)
        
        container = discord.ui.Container(
            discord.ui.Section(
                self.main_text,
                accessory=discord.ui.Thumbnail(
                    media=self.bot_avatar,
                ),
            ),
            discord.ui.Separator(visible=False),
            discord.ui.ActionRow(self.startB, self.backB, self.nextB, self.endB),
            discord.ui.Separator(visible=False),
            discord.ui.ActionRow(select),
        )
        self.add_item(container)
        self.container = container
        self._update_buttons()
        
    def _update_content(self):
        cogs = self._get_cogs()
        if self.index == 0:
            self.main_text.content = self.home_text
        elif 0 < self.index <= len(cogs):
            cog = cogs[self.index - 1]
            text = self._get_cog_text(cog)
            self.main_text.content = text
        else:
            self.main_text.content = self.home_text
        self._update_buttons()
        
    def _update_buttons(self):
        for button in [self.startB, self.backB, self.nextB, self.endB]:
            button.disabled = False
        if self.index == 0:
            self.startB.disabled = True
            self.backB.disabled = True
        elif self.index >= len(self.options) - 1:
            self.nextB.disabled = True
            self.endB.disabled = True

    def _get_cog_text(self, cog):
        if cog and hasattr(cog, "help_custom"):
            emoji, label, _ = cog.help_custom()
            lines = [f"## {emoji} {label}", ""]
            cmds = getattr(cog, 'commands', cog.get_commands() if hasattr(cog, 'get_commands') else [])
            if isinstance(cmds, list):
                for cmd in cmds:
                    lines.append(f"`{cmd}`")
                return "\n".join(lines)
            cmds_list = list(cmds)
            if cmds_list and cmds_list[0].name.startswith("__") and cmds_list[0].help:
                lines.append(cmds_list[0].help)
            else:
                for cmd in cmds_list:
                    params = " ".join(f"<{p}>" for p in cmd.clean_params)
                    lines.append(f"`{cmd.name}{params}` - {cmd.help or ''}")
            return "\n".join(lines)
        return self.home_text
        
    def _gen_options(self):
        options = []
        for cog in self.mapping.keys():
            if cog and hasattr(cog, "help_custom"):
                emoji, label, description = cog.help_custom()
                options.append(discord.SelectOption(label=label, emoji=emoji, description=description, value=cog.qualified_name))
        return options
    
    def _get_cogs(self):
        cogs = []
        for cog in self.mapping.keys():
            if cog and hasattr(cog, "help_custom"):
                cogs.append(cog)
        return cogs

    async def to_page(self, page: int, interaction: discord.Interaction):
        new_index = self.index + page
        if 0 <= new_index <= len(self.options) - 1:
            self.index = new_index
            self._update_content()
            await interaction.response.edit_message(view=self)

    async def set_page(self, page: int, interaction: discord.Interaction):
        self.index = page
        self._update_content()
        await interaction.response.edit_message(view=self)

    async def quit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class Dropdown(discord.ui.Select):

    def __init__(self, ctx, options):
        super().__init__(placeholder="select a module.",
                         min_values=1,
                         max_values=1,
                         options=options)
        self.invoker = ctx.author

    async def callback(self, interaction: discord.Interaction):
        if self.invoker == interaction.user:
            index = self.view.find_index_from_select(self.values[0])
            if not index: index = 0
            await self.view.set_page(index, interaction)
        else:
            await interaction.response.send_message(
                f"this is not your session. {error}", ephemeral=True)

class randi(discord.ui.Button):

    def __init__(self,
                 command,
                 ctx,
                 emoji,
                 style: discord.ButtonStyle,
                 args=None):
        disable = False
        if args == -1 or args == 0: disable = True
        super().__init__(emoji=emoji, style=style, disabled=disable)
        self.command = command
        self.invoker = ctx.author
        self.args = args

    async def callback(self, interaction: discord.Interaction):
        if self.invoker == interaction.user:
            if self.args or self.args == 0:
                func = functools.partial(self.command, self.args, interaction)
                await func()
            else:
                await self.command(interaction)
        else:
            await interaction.response.send_message(
                f"this is not your session. {error}", ephemeral=True)




class Buttons(discord.ui.Button):

    def __init__(self,
                 command,
                 ctx,
                 label,
                 style: discord.ButtonStyle,
                 args=None):
        disable = False
        if args == -1 or args == 0: disable = True
        super().__init__(label=label, style=style, disabled=disable)
        self.command = command
        self.invoker = ctx.author
        self.args = args

    async def callback(self, interaction: discord.Interaction):
        if self.invoker == interaction.user:
            if self.args or self.args == 0:
                func = functools.partial(self.command, self.args, interaction)
                await func()
            else:
                await self.command(interaction)
        else:
            await interaction.response.send_message(
                f"this is not your session. {error}", ephemeral=True)


class View(discord.ui.View):

    def __init__(self, mapping: dict,
                 ctx: discord.ext.commands.context.Context,
                 homeembed: discord.embeds.Embed, ui: int):
        super().__init__()
        self.mapping, self.ctx, self.home = mapping, ctx, homeembed
        self.index, self.buttons = 0, None

        self.options, self.embeds = self.gen_embeds()

        if ui == 0: self.add_item(Dropdown(ctx=self.ctx, options=self.options))
        elif ui == 1: self.buttons = self.add_buttons()
        else:
        
            self.buttons = self.add_buttons()
            self.add_item(Dropdown(ctx=self.ctx, options=self.options))
            

    def add_buttons(self):
        self.startB = Buttons(label="≪",
                              style=discord.ButtonStyle.blurple,
                              command=self.set_page,
                              args=0,
                              ctx=self.ctx)
        self.backB = Buttons(label="Back",
                             style=discord.ButtonStyle.success,
                             command=self.to_page,
                             args=-1,
                             ctx=self.ctx)
        self.nextB = Buttons(label="Next",
                             style=discord.ButtonStyle.success,
                             command=self.to_page,
                             args=+1,
                             ctx=self.ctx)
        self.endB = Buttons(label="≫",
                            style=discord.ButtonStyle.blurple,
                            command=self.set_page,
                            args=len(self.options) - 1,
                            ctx=self.ctx)
        self.quitB = randi(emoji="<a:astroz_error:1071025931696742481>",
                             style=discord.ButtonStyle.danger,
                             command=self.quit,
                             ctx=self.ctx)
        buttons = [self.startB, self.backB, self.quitB, self.nextB, self.endB]
        for button in buttons:
            self.add_item(button)
        return buttons

    def find_index_from_select(self, value):
        i = 0
        seen = set()
        for cog in self.get_cogs():
            if "help_custom" in dir(cog):
                _, label, _ = cog.help_custom()
                if label in seen:
                    continue
                seen.add(label)
                if label == value: return i + 1
                i += 1

    def get_cogs(self):
        cogs = []
        for cog in self.mapping.keys():
            cogs.append(cog)
        return cogs

    def gen_embeds(self):
        options, embeds = [], []
        options.append(
            discord.SelectOption(label="Index",
                                 emoji='<a:hacker_developer_bot:1063109615321100368>', description="Show You Index"))
        embeds.append(self.home)
        seen_labels = set()
        for cog in self.get_cogs():
            if "help_custom" in dir(cog):
                emoji, label, description = cog.help_custom()
                if label in seen_labels:
                    continue
                seen_labels.add(label)
                options.append(discord.SelectOption(label=label, emoji=emoji,description=description))
                embed = discord.Embed(title=f"{emoji} {label}",
                                      color=0x2f3136)
                embed.set_footer(text=f"Requested By {self.ctx.message.author}", icon_url=self.ctx.message.author.display_avatar.url)
                embed.timestamp = discord.utils.utcnow()
                for command in getattr(cog, 'commands', cog.get_commands() if hasattr(cog, 'get_commands') else []):
                    if isinstance(command, str):
                        embed.add_field(name=command, value="", inline=True)
                    else:
                        params = ""
                        for param in command.clean_params:
                            params += f" <{param}>"
                        embed.add_field(name=f"{command.name}{params}",
                                        value=f"{command.help}\n\u200b",
                                        inline=True)
                embeds.append(embed)
        return options, embeds

    async def quit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    async def to_page(self, page: int, interaction: discord.Interaction):
        if not self.index + page < 0 or not self.index + page > len(
                self.options):
            await self.set_index(page)
            embed = self.embeds[self.index]

            await interaction.response.edit_message(embed=embed, view=self)

    async def set_page(self, page: int, interaction: discord.Interaction):
        self.index = page
        await self.to_page(0, interaction)

    async def set_index(self, page):
        self.index += page
        if self.buttons:
            for button in self.buttons[0:-1]:
                button.disabled = False
            if self.index == 0:
                self.backB.disabled = True
                self.startB.disabled = True
            elif self.index == len(self.options) - 1:
                self.nextB.disabled = True
                self.endB.disabled = True