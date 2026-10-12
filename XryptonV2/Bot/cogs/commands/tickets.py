from __future__ import annotations

import asyncio
import os
import json
import discord
from discord import Embed, ButtonStyle
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Optional

from core import Cog, Astroz, Context
from utils.Tools import blacklist_check, ignore_check

COLOR = 0x2b2d31
APPROVE_COLOR = 0x2b2d31
WARN_COLOR = 0x2b2d31

TICKET_CONFIG_PATH = "data/ticket/ticket_config.json"
TICKET_OPEN_PATH = "data/ticket/ticket_open.json"
TICKET_TOPICS_PATH = "data/ticket/ticket_topics.json"


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        if path == TICKET_CONFIG_PATH:
            return {"guilds": {}}
        return {}


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_ticket():
    async def predicate(ctx: commands.Context):
        data = _load_json(TICKET_OPEN_PATH)
        guild_data = data.get(str(ctx.guild.id), [])
        return any(t["channel_id"] == ctx.channel.id for t in guild_data)
    return commands.check(predicate)


async def make_transcript(channel):
    filename = f"{channel.name}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        async for msg in channel.history(oldest_first=True):
            if not msg.author.bot:
                file.write(f"{msg.created_at} - {msg.author.display_name}: {msg.clean_content}\n")
    return filename


class TicketTopic(discord.ui.Modal, title="Add ticket topic"):
    name = discord.ui.TextInput(label="Topic Name", placeholder="The ticket topics name.", required=True, style=discord.TextStyle.short)
    description = discord.ui.TextInput(label="Topic Description", placeholder="The description of the ticket topic.", required=False, max_length=100, style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        data = _load_json(TICKET_TOPICS_PATH)
        guild_id = str(interaction.guild.id)
        if guild_id not in data:
            data[guild_id] = []

        if any(t["topic"] == self.name.value for t in data[guild_id]):
            return await interaction.response.send_message(
                embed=Embed(description=f"⚠️ {interaction.user.mention}: A topic with the name **{self.name.value}** already exists", color=WARN_COLOR),
                ephemeral=True
            )

        identifier = f"topic_{interaction.guild.id}_{len(data[guild_id])}"
        data[guild_id].append({
            "identifier": identifier,
            "topic": self.name.value,
            "template": self.description.value,
            "category_id": None,
        })
        _save_json(TICKET_TOPICS_PATH, data)

        await interaction.response.send_message(
            embed=Embed(description=f"✅ {interaction.user.mention}: Added new ticket topic **{self.name.value}**", color=APPROVE_COLOR),
            ephemeral=True
        )


class CreateTicket(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create", emoji="🎫", style=ButtonStyle.gray, custom_id="persistent_view:create")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = _load_json(TICKET_CONFIG_PATH).get(str(interaction.guild.id))
        if not config:
            return await interaction.response.send_message(
                embed=Embed(description=f"⚠️ {interaction.user.mention}: Ticket module was disabled", color=WARN_COLOR),
                ephemeral=True
            )

        open_data = _load_json(TICKET_OPEN_PATH)
        guild_open = open_data.get(str(interaction.guild.id), [])
        if any(t["user_id"] == interaction.user.id for t in guild_open):
            return await interaction.response.send_message(
                embed=Embed(description=f"⚠️ {interaction.user.mention}: You already have a ticket opened", color=WARN_COLOR),
                ephemeral=True
            )

        topics = _load_json(TICKET_TOPICS_PATH).get(str(interaction.guild.id), [])

        if not topics:
            await self._create_ticket(interaction, config)
        else:
            options = [discord.SelectOption(label=topic["topic"] or "Untitled", description=topic["template"] or "No description", value=topic["topic"] or "untitled") for topic in topics if topic["topic"]]
            if not options:
                await self._create_ticket(interaction, config)
                return

            embed = Embed(description="🔍 Please choose a topic", color=COLOR)
            select = Select(options=options, placeholder="select a topic...")

            async def select_callback(inte: discord.Interaction):
                await self._create_ticket(inte, config, select.values[0])

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _create_ticket(self, interaction: discord.Interaction, config, topic=None):
        all_topics = _load_json(TICKET_TOPICS_PATH).get(str(interaction.guild.id), [])
        button_config = next((t for t in all_topics if t.get("category_id")), None)
        category = interaction.guild.get_channel(button_config["category_id"]) if button_config and button_config.get("category_id") else None
        channel_name = config.get("channel_name") or f"ticket-{interaction.user.name}"

        text = await interaction.guild.create_text_channel(
            name=channel_name.replace("{user}", interaction.user.name),
            reason="opened ticket",
            category=category
        )

        overwrites = discord.PermissionOverwrite(send_messages=True, view_channel=True, attach_files=True, embed_links=True)
        await text.set_permissions(interaction.user, overwrite=overwrites)

        overwrite1 = text.overwrites_for(interaction.guild.default_role)
        overwrite1.view_channel = False
        await text.set_permissions(interaction.guild.default_role, overwrite=overwrite1)

        embed = Embed(
            title=topic if topic else "Support Ticket",
            description="Support will be with you shortly, please be patient.\n\nTo close the ticket press the button down below.",
            color=COLOR
        )

        open_data = _load_json(TICKET_OPEN_PATH)
        guild_id = str(interaction.guild.id)
        if guild_id not in open_data:
            open_data[guild_id] = []
        open_data[guild_id].append({
            "identifier": f"ticket_{interaction.guild.id}_{text.id}",
            "guild_id": interaction.guild.id,
            "channel_id": text.id,
            "user_id": interaction.user.id,
            "topic": topic,
        })
        _save_json(TICKET_OPEN_PATH, open_data)

        if hasattr(interaction, 'response') and not interaction.response.is_done():
            await interaction.response.send_message(
                embed=Embed(description=f"✅ {interaction.user.mention}: Opened ticket in {text.mention}", color=APPROVE_COLOR),
                ephemeral=True
            )
        else:
            await interaction.edit_original_response(
                embed=Embed(description=f"✅ {interaction.user.mention}: Opened ticket in {text.mention}", color=APPROVE_COLOR),
                view=None
            )

        mes = await text.send(content=f"{interaction.user.mention}, Welcome.", embed=embed, view=DeleteView(), allowed_mentions=discord.AllowedMentions.all())

        for staff_id in config.get("staff_ids", []):
            await text.send(f'<@&{staff_id}>', allowed_mentions=discord.AllowedMentions(roles=True), delete_after=5)

        await mes.pin()


class DeleteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="", emoji="🗑️", style=ButtonStyle.gray, custom_id="persistent_view:delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        close = discord.ui.Button(label="Close", style=discord.ButtonStyle.red)
        cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.gray)

        async def close_callback(inte: discord.Interaction):
            logs_channel = _load_json(TICKET_CONFIG_PATH).get(str(inte.guild.id), {}).get("logging_channel")

            if logs_channel and logs_channel != 0:
                filename = await make_transcript(interaction.channel)
                embed = Embed(
                    title="ticket logs",
                    description=f"Logs for ticket `{inte.channel.id}` | closed by **{inte.user}**",
                    timestamp=discord.utils.utcnow(),
                    color=COLOR
                )
                try:
                    await inte.guild.get_channel(logs_channel).send(embed=embed, file=discord.File(filename))
                except Exception:
                    pass
                os.remove(filename)

            open_data = _load_json(TICKET_OPEN_PATH)
            guild_id = str(inte.guild.id)
            if guild_id in open_data:
                open_data[guild_id] = [t for t in open_data[guild_id] if t["channel_id"] != inte.channel.id]
                _save_json(TICKET_OPEN_PATH, open_data)

            await inte.response.edit_message(content=f"closed by {inte.user.mention}", view=None)
            await asyncio.sleep(2)
            await inte.channel.delete()

        async def cancel_callback(inte: discord.Interaction):
            await inte.response.edit_message(content="Aborting closure...", view=None)

        close.callback = close_callback
        cancel.callback = cancel_callback

        view = View()
        view.add_item(close)
        view.add_item(cancel)
        await interaction.response.send_message("Are you sure you want to close the ticket?", view=view)


class Tickets(Cog):
    def __init__(self, bot: Astroz):
        self.bot = bot
        self.bot.add_view(CreateTicket())
        self.bot.add_view(DeleteView())

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.TextChannel):
            open_data = _load_json(TICKET_OPEN_PATH)
            guild_id = str(channel.guild.id)
            if guild_id in open_data:
                open_data[guild_id] = [t for t in open_data[guild_id] if t["channel_id"] != channel.id]
                _save_json(TICKET_OPEN_PATH, open_data)

    @commands.group(invoke_without_command=True, name="ticket")
    @blacklist_check()
    @ignore_check()
    async def ticket(self, ctx: Context):
        await ctx.send_help(ctx.command)

    @ticket.command(name="add")
    @commands.has_permissions(manage_channels=True)
    @get_ticket()
    @blacklist_check()
    @ignore_check()
    async def ticket_add(self, ctx: Context, *, member: discord.Member):
        overwrites = discord.PermissionOverwrite(send_messages=True, view_channel=True, attach_files=True, embed_links=True)
        await ctx.channel.set_permissions(member, overwrite=overwrites)
        await ctx.reply(embed=Embed(description=f"I have added **{member}** to the ticket.", color=COLOR))

    @ticket.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    @get_ticket()
    @blacklist_check()
    @ignore_check()
    async def ticket_remove(self, ctx: Context, *, member: discord.Member):
        overwrites = discord.PermissionOverwrite(send_messages=False, view_channel=False, attach_files=False, embed_links=False)
        await ctx.channel.set_permissions(member, overwrite=overwrites)
        await ctx.reply(embed=Embed(description=f"I have removed **{member}** from the ticket.", color=COLOR))

    @ticket.command(name="topics")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def ticket_topics(self, ctx: Context):
        config = _load_json(TICKET_CONFIG_PATH).get(str(ctx.guild.id))
        if not config:
            return await ctx.reply(embed=Embed(description="⚠️ no ticket panel created", color=WARN_COLOR))

        topics = _load_json(TICKET_TOPICS_PATH).get(str(ctx.guild.id), [])
        embed = Embed(description="🔍 Choose a setting", color=COLOR)

        button1 = discord.ui.Button(label="add topic", style=discord.ButtonStyle.gray)
        button2 = discord.ui.Button(label="remove topic", style=discord.ButtonStyle.red, disabled=len(topics) == 0)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message(
                    embed=Embed(description=f"⚠️ {interaction.user.mention}: You are **not** the author of this message.", color=WARN_COLOR),
                    ephemeral=True
                )
            await interaction.response.send_modal(TicketTopic())

        async def button2_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message(
                    embed=Embed(description=f"⚠️ {interaction.user.mention}: You are **not** the author of this message.", color=WARN_COLOR),
                    ephemeral=True
                )

            e = Embed(description="🔍 Select a topic to delete.", color=COLOR)
            options = [discord.SelectOption(label=topic["topic"] or "Untitled", description=topic["template"] or "No description", value=topic["topic"] or "untitled") for topic in topics if topic["topic"]]
            if not options:
                return await interaction.response.send_message(
                    embed=Embed(description=f"⚠️ {interaction.user.mention}: No valid topics to remove.", color=WARN_COLOR),
                    ephemeral=True
                )
            select = Select(options=options, placeholder="Select a topic.")

            async def select_callback(inter: discord.Interaction):
                if inter.user != ctx.author:
                    return await inter.response.send_message(
                        embed=Embed(description=f"⚠️ {inter.user.mention}: You are **not** the author of this message.", color=WARN_COLOR),
                        ephemeral=True
                    )

                topic_data = _load_json(TICKET_TOPICS_PATH)
                guild_id = str(inter.guild.id)
                if guild_id in topic_data:
                    topic_data[guild_id] = [t for t in topic_data[guild_id] if t["topic"] != select.values[0]]
                    _save_json(TICKET_TOPICS_PATH, topic_data)

                await inter.response.send_message(
                    embed=Embed(description=f"✅ {inter.user.mention}: I have removed **{select.values[0]}** topic.", color=APPROVE_COLOR),
                    ephemeral=True
                )

            select.callback = select_callback
            v = View()
            v.add_item(select)
            await interaction.response.edit_message(embed=e, view=v)

        button1.callback = button1_callback
        button2.callback = button2_callback

        view = View()
        view.add_item(button1)
        view.add_item(button2)
        await ctx.reply(embed=embed, view=view)

    @ticket.command(name="staff")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def ticket_staff(self, ctx: Context, role: Optional[discord.Role] = None):
        config = _load_json(TICKET_CONFIG_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in config:
            config[guild_id] = {}

        if not role:
            config[guild_id]["staff_ids"] = []
            _save_json(TICKET_CONFIG_PATH, config)
            return await ctx.reply(embed=Embed(description="I have removed **support roles**.", color=COLOR))

        staff_ids = config[guild_id].get("staff_ids", [])
        if role.id in staff_ids:
            staff_ids.remove(role.id)
            config[guild_id]["staff_ids"] = staff_ids
            _save_json(TICKET_CONFIG_PATH, config)
            await ctx.reply(embed=Embed(description=f"I have removed **{role.name}** as a **support role**.", color=COLOR))
        else:
            staff_ids.append(role.id)
            config[guild_id]["staff_ids"] = staff_ids
            _save_json(TICKET_CONFIG_PATH, config)
            await ctx.reply(embed=Embed(description=f"I have added **{role.name}** as a **support role**.", color=COLOR))

    @ticket.command(name="category")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def ticket_category(self, ctx: Context, channel: Optional[discord.CategoryChannel] = None):
        topic_data = _load_json(TICKET_TOPICS_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in topic_data:
            topic_data[guild_id] = []

        if channel:
            existing = next((t for t in topic_data[guild_id] if t["identifier"].startswith("category_")), None)
            if existing:
                existing["category_id"] = channel.id
            else:
                topic_data[guild_id].append({
                    "identifier": f"category_{ctx.guild.id}",
                    "category_id": channel.id,
                })
            _save_json(TICKET_TOPICS_PATH, topic_data)
            await ctx.reply(embed=Embed(description=f"tickets category set to {channel.mention}", color=COLOR))
        else:
            for t in topic_data[guild_id]:
                if t["identifier"].startswith("category_"):
                    t["category_id"] = None
            _save_json(TICKET_TOPICS_PATH, topic_data)
            await ctx.reply(embed=Embed(description="I have **removed** tickets category.", color=COLOR))

    @ticket.command(name="channel")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def ticket_channel(self, ctx: Context, *, channel: Optional[discord.TextChannel] = None):
        config = _load_json(TICKET_CONFIG_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in config:
            config[guild_id] = {}

        if channel:
            config[guild_id]["channel_id"] = channel.id
            config[guild_id]["message_id"] = 0
            _save_json(TICKET_CONFIG_PATH, config)
            await ctx.reply(embed=Embed(description=f"tickets channel set to {channel.mention}", color=COLOR))
        else:
            config[guild_id]["channel_id"] = 0
            _save_json(TICKET_CONFIG_PATH, config)
            await ctx.reply(embed=Embed(description="I have **removed** the tickets channel.", color=COLOR))

    @ticket.command(name="logs")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def ticket_logs(self, ctx: Context, *, channel: Optional[discord.TextChannel] = None):
        config = _load_json(TICKET_CONFIG_PATH)
        guild_id = str(ctx.guild.id)
        if guild_id not in config:
            config[guild_id] = {}

        if channel:
            config[guild_id]["logging_channel"] = channel.id
            _save_json(TICKET_CONFIG_PATH, config)
            await ctx.reply(embed=Embed(description=f"tickets logs set to {channel.mention}", color=COLOR))
        else:
            config[guild_id]["logging_channel"] = 0
            _save_json(TICKET_CONFIG_PATH, config)
            await ctx.reply(embed=Embed(description="I have **removed** the tickets logs.", color=COLOR))

    @ticket.command(name="send")
    @commands.has_permissions(administrator=True)
    @blacklist_check()
    @ignore_check()
    async def ticket_send(self, ctx: Context):
        config = _load_json(TICKET_CONFIG_PATH).get(str(ctx.guild.id))
        if not config or not config.get("channel_id"):
            return await ctx.reply(embed=Embed(description="⚠️ You have **not** set a ticket channel.", color=WARN_COLOR))

        channel = ctx.guild.get_channel(config["channel_id"])
        if not channel:
            return await ctx.reply(embed=Embed(description="⚠️ I could **not** find that channel.", color=WARN_COLOR))

        embed = Embed(
            title="Create a ticket",
            description="Click on the button below this message to create a ticket",
            color=COLOR
        )

        message = await channel.send(embed=embed, view=CreateTicket())
        config["message_id"] = message.id
        data = _load_json(TICKET_CONFIG_PATH)
        data[str(ctx.guild.id)] = config
        _save_json(TICKET_CONFIG_PATH, data)
        await ctx.reply(embed=Embed(description=f"Sent the **ticket** message to {channel.mention}", color=COLOR))

    @ticket.command(name="settings")
    @blacklist_check()
    @ignore_check()
    async def ticket_settings(self, ctx: Context):
        config = _load_json(TICKET_CONFIG_PATH).get(str(ctx.guild.id))
        if not config:
            return await ctx.reply(embed=Embed(description="⚠️ You have **not** created a ticket panel.", color=WARN_COLOR))

        topics = _load_json(TICKET_TOPICS_PATH).get(str(ctx.guild.id), [])
        button_config = next((t for t in topics if t.get("category_id")), None)

        embed = Embed(title="Ticket Settings", description=f"Settings for **{ctx.guild.name}**", color=COLOR)
        embed.add_field(name="Ticket Channel", value=ctx.guild.get_channel(config.get("channel_id")).mention if config.get("channel_id") and ctx.guild.get_channel(config.get("channel_id")) else "N/A")
        embed.add_field(name="Logs Channel", value=ctx.guild.get_channel(config.get("logging_channel")).mention if config.get("logging_channel") and ctx.guild.get_channel(config.get("logging_channel")) else "N/A")
        embed.add_field(name="Category", value=ctx.guild.get_channel(button_config["category_id"]).mention if button_config and button_config.get("category_id") and ctx.guild.get_channel(button_config["category_id"]) else "N/A")
        await ctx.send(embed=embed)


async def setup(bot: Astroz):
    await bot.add_cog(Tickets(bot))
