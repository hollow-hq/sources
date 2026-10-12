from __future__ import annotations

import json
import os
import typing

import discord
from discord import *
from discord.ext import commands

from utils import constants
from utils.config import OWNER_IDS, NO_PREFIX, get_bot_name


class HelpDropdown(discord.ui.Select):
    """Select menu for navigating help categories."""

    def __init__(self, help_view, options):
        super().__init__(
            placeholder="Select a category to view commands",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="help_select_menu"
        )
        self.help_view = help_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.help_view.invoker.id:
            return await interaction.response.send_message("This help menu is not yours!", ephemeral=True)

        selected_value = self.values[0]
        for i, opt in enumerate(self.help_view.options):
            if opt.value == selected_value:
                self.help_view.index = i + 1
                break

        self.help_view._update_content()
        await interaction.response.edit_message(view=self.help_view)


class Antinuke(commands.Cog):
    """Antinuke help category."""
    __cog_name__ = "AntinukeDropdown"
    commands = ["antinuke", "antinuke settings", "antinuke whitelist", "antinuke admin",
    "antinuke whitelisted", "antinuke admins", "antinuke enable", "antinuke disable",
    "antinuke toggle", "antinuke threshold", "antinuke action"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.Security
        label = "Antinuke Commands"
        description = "protect your server against nukers"
        return emoji, label, description


class Moderation(commands.Cog):
    """Moderation help category."""
    __cog_name__ = "ModerationDropdown"
    commands = ["mute", "unmute", "kick", "warn", "ban", "unban", "clone", "nick",
    "slowmode", "unslowmode", "clear", "clear all", "clear bots", "clear embeds",
    "clear files", "clear mentions", "clear images", "clear contains",
    "clear reactions", "clear user", "clear emoji", "nuke", "lock", "unlock", "hide",
    "unhide", "hideall", "unhideall", "audit", "role", "role temp", "role remove",
    "role delete", "role create", "role rename", "enlarge", "role humans",
    "role unverified", "role bots", "role all", "removerole humans",
    "removerole unverified", "removerole bots", "removerole all",
    "admin add", "admin remove", "admin show", "admin role", "admin reset",
    "mod add", "mod remove", "mod show", "mod role", "mod reset", "roleicon",
    "steal", "deleteemoji", "deletesticker", "addsticker", "sticky add",
    "sticky edit", "sticky remove", "sticky list"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.Moderation
        label = "Moderation Commands"
        description = "moderate your server"
        return emoji, label, description


class Fun(commands.Cog):
    """Fun help category."""
    __cog_name__ = "FunDropdown"
    commands = ["makemp3", "duckduckgo", "8ball", "coinflip", "roll", "choose",
    "reverse", "mock", "rate", "howgay", "ascii"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = "🎮"
        label = "Fun Commands"
        description = "fun and entertaining commands"
        return emoji, label, description


class Antiraid(commands.Cog):
    """Antiraid help category."""
    __cog_name__ = "AntiraidDropdown"
    commands = ["automod", "automod list", "automod view", "automod delete",
    "automod enable", "automod disable", "automod keyword create",
    "automod keyword add", "automod keyword remove", "automod keyword regex",
    "automod keyword whitelist", "automod spam create", "automod spam toggle",
    "automod preset create", "automod preset whitelist", "automod mentions create",
    "automod mentions raidprotection", "automod profile create", "automod profile add",
    "automod action block", "automod action alert", "automod action timeout",
    "automod action blockinteraction", "automod exempt role", "automod exempt channel",
    "automod unexempt role", "automod unexempt channel", "automod setup profanity",
    "automod setup spam", "automod setup mentions", "automod setup slurs",
    "automod stats", "automod export", "automod import"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.Raidmode
        label = "Antiraid Commands"
        description = "stop raids from happening in your server"
        return emoji, label, description


class WelcomerDrop(commands.Cog):
    """Welcomer help category."""
    __cog_name__ = "WelcomerDropdown"
    commands = ["greet channel add", "greet channel remove", "greet channel",
     "greet embed", "greet image", "greet message", "greet ping", "greet test",
      "greet thumbnail", "greet autodel", "greet title", "greet footer", "greet",
       "autorole bots add", "autorole bots remove", "autorole bots", "autorole config",
        "autorole humans add", "autorole humans remove", "autorole humans",
         "autorole reset all", "autorole reset bots", "autorole reset humans",
           "autorole reset", "autorole",
           "welcome config", "welcome setup", "welcome clear", "welcome invoke"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.Welcomer
        label = "Welcomer Commands"
        description = "greet and auto-role new members"
        return emoji, label, description


class Logging(commands.Cog):
    """Logging help category."""
    __cog_name__ = "LoggingDropdown"
    commands = ["msglog", "memberlog", "serverlog",
    "channellog", "rolelog", "modlog"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.Logging
        label = "Logging Commands"
        description = "log actions happening in the server"
        return emoji, label, description


class Extras(commands.Cog):
    """Extra utility commands."""
    __cog_name__ = "ExtrasDropdown"
    commands = ["botinfo", "stats", "invite", "serverinfo", "userinfo", "roleinfo",
     "status", "boosts", "unbanall", "joined-at", "ping", "github", "vcinfo",
      "channelinfo", "badges", "list boosters", "list inrole", "list emojis",
       "list bots", "list admins", "list invoice", "list mods", "list early",
        "list activedeveloper", "list createpos", "list roles", "banner user",
         "banner server", "ignore channel add", "ignore channel remove",
          "ignore user add", "ignore user remove", "pfp", "pfp random",
           "pfp auto enable", "pfp auto disable", "chatbot setup",
            "chatbot reset", "imagine"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.Extra
        label = "Extra Commands"
        description = "extra utility commands"
        return emoji, label, description


class General(commands.Cog):
    """General commands category."""
    __cog_name__ = "GeneralDropdown"
    commands = ["ask", "ai", "gpt", "generate", "gen", "draw", "chatgpt", "edit",
     "avatar", "servericon", "membercount", "poll", "hack", "token", "users",
      "italicize", "strike", "quote", "code", "bold", "censor", "underline",
       "gender", "wizz", "pikachu", "shorten", "urban", "rickroll", "hash",
        "snipe", "setup", "setup staff", "setup girl", "setup friend", "setup vip",
         "setup guest", "setup config", "setup create", "setup delete", "setup list",
          "staff", "girl", "friend", "vip", "guest", "remove staff", "remove girl",
           "remove friend", "remove vip", "remove guest", "ar", "ar create",
            "ar delete", "ar edit", "ar config", "reset", "afk", "jail", "unjail",
             "media setup", "media remove", "media config", "media reset"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.General
        label = "General Commands"
        description = "general utility and fun commands"
        return emoji, label, description


class Voice(commands.Cog):
    """Voice help category."""
    __cog_name__ = "VoiceDropdown"
    commands = ["voice kick", "voice kickall", "voice mute", "voice muteall",
     "voice unmute", "voice unmuteall", "voice deafen", "voice deafenall",
      "voice undeafen", "voice undeafenall", "voice moveall", "vcrole bots add",
       "vcrole bots remove", "vcrole bots", "vcrole config", "vcrole humans add",
        "vcrole humans remove", "vcrole humans", "vcrole reset"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.Voice
        label = "Voice Commands"
        description = "voice channel management"
        return emoji, label, description


class Nsfw(commands.Cog):
    """NSFW help category."""
    __cog_name__ = "NsfwDropdown"
    commands = [
        "nsfw hentai ecchi", "nsfw hentai hentai", "nsfw hentai uniform",
        "nsfw hentai maid", "nsfw hentai oppai", "nsfw hentai selfies",
        "nsfw hentai raiden", "nsfw hentai marin", "nsfw hentai ass",
        "nsfw hentai paizuri", "nsfw hentai ero", "nsfw hentai milf",
        "nsfw hentai oral", "nsfw rule34 images"
    ]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = constants.Nsfw
        label = "NSFW Commands"
        description = "NSFW related commands"
        return emoji, label, description


class TicketDrop(commands.Cog):
    """Ticket help category."""
    __cog_name__ = "TicketDropdown"
    commands = ["ticket add", "ticket remove", "ticket topics", "ticket staff",
     "ticket category", "ticket channel", "ticket logs", "ticket send",
      "ticket settings"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = "🎫"
        label = "Ticket Commands"
        description = "manage server support tickets"
        return emoji, label, description


class ConfessionsDrop(commands.Cog):
    """Confessions help category."""
    __cog_name__ = "ConfessionsDropdown"
    commands = ["confessions add", "confessions reportchannel", "confessions report",
     "confessions disable", "confessions name", "confessions avatar",
      "confessions config", "confessions mute", "confessions unmute",
       "confessions mutelist", "confessions blacklist", "confessions blacklist add",
        "confessions blacklist remove", "confessions blacklist list",
         "confessions blacklist clear"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = "💬"
        label = "Confessions Commands"
        description = "manage anonymous confessions"
        return emoji, label, description


class BumpReminderDrop(commands.Cog):
    """Bumpreminder help category."""
    __cog_name__ = "BumperReminderDropdown"
    commands = ["bumpreminder channel", "bumpreminder message",
     "bumpreminder thankyou", "bumpreminder autoclean", "bumpreminder autolock",
      "bumpreminder config", "bumpreminder test"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = "🔔"
        label = "Bumpreminder Commands"
        description = "manage Disboard bump reminders"
        return emoji, label, description


class Roleplay(commands.Cog):
    """Roleplay help category."""
    __cog_name__ = "RoleplayDropdown"
    commands = ["angry", "baka", "bite", "bleh", "blowkiss", "blush", "bonk", "bored",
     "carry", "clap", "confused", "cry", "cuddle", "dance", "facepalm", "feed",
      "handhold", "handshake", "happy", "highfive", "hug", "kabedon", "kick", "kiss",
       "lappillow", "laugh", "lurk", "nod", "nom", "nope", "nya", "pat", "peck",
        "poke", "pout", "punch", "run", "salute", "shake", "shoot", "shocked",
         "shrug", "sip", "slap", "sleep", "smile", "smug", "spin", "stare",
          "tableflip", "teehee", "think", "thumbsup", "tickle", "wag", "wave",
            "wink", "yawn", "yet"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = "🎭"
        label = "Roleplay Commands"
        description = "fun roleplay actions"
        return emoji, label, description


class AIEmbed(commands.Cog):
    """AI and Embed Scripting help category."""
    __cog_name__ = "AIEmbedDropdown"
    commands = ["ask", "generate", "edit", "reset", "embed", "embed create",
     "embed run", "embed list", "embed delete", "embed copy"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = "🤖"
        label = "AI & Embed Scripting"
        description = "AI chat, image generation and embed scripting"
        return emoji, label, description


class Media(commands.Cog):
    """Image manipulation help category."""
    __cog_name__ = "MediaDropdown"
    commands = ["imagetogif", "speechbubble", "caption", "blackandwhite",
    "pixelate", "invert", "deepfry", "stretch", "saturate", "overlay", "flip"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = "🖼️"
        label = "Image Commands"
        description = "manipulate and process images"
        return emoji, label, description


class Utilities(commands.Cog):
    """Misc utility commands."""
    __cog_name__ = "UtilitiesDropdown"
    commands = ["afk", "giveaway", "gstop", "level", "level toggle",
     "level leaderboard", "level threshold", "level role add", "level role remove",
      "level role list", "sticky add", "sticky edit", "sticky remove", "sticky list",
       "giveaway start", "vanitystatus", "vanitystatus keyword",
        "vanitystatus addrole", "vanitystatus removerole", "ignore",
         "ignore channel add", "ignore channel remove", "ignore user add",
          "ignore user remove", "uwulock", "uwulock enable", "uwulock add",
           "uwulock remove", "uwulock config", "boosterrole create", "boosterrole hoist",
            "boosterrole color", "boosterrole share", "boosterrole cleanup",
             "boosterrole name", "boosterrole delete", "boosterrole", "pingonjoin set",
              "pingonjoin remove", "pingonjoin", "joindm set", "joindm disable",
               "joindm enable", "joindm remove", "joindm", "snipefilter add",
                "snipefilter remove", "snipefilter", "reactionrole add",
                 "reactionrole remove", "reactionrole removeall", "reactionrole list",
                  "reactionrole", "skull count", "skull channel", "skull remove",
                   "skull stats", "skull emoji", "skull", "setprefix", "embedcode",
                    "editsnipe", "clearsnipe", "cleareditsnipe", "snipe",
                    "games tictactoe", "games rps", "games snake", "games blackjack", "games cookie"]

    def __init__(self, bot):
        self.bot = bot

    def help_custom(self):
        emoji = "🧰"
        label = "Utilities"
        description = "AFK, giveaways, levels, sticky and more"
        return emoji, label, description


async def setup(bot):
    await bot.add_cog(Antinuke(bot))
    await bot.add_cog(Moderation(bot))
    await bot.add_cog(Fun(bot))
    await bot.add_cog(Antiraid(bot))
    await bot.add_cog(Media(bot))
    await bot.add_cog(Utilities(bot))
    await bot.add_cog(WelcomerDrop(bot))
    await bot.add_cog(Logging(bot))
    await bot.add_cog(Extras(bot))
    await bot.add_cog(General(bot))
    await bot.add_cog(Voice(bot))
    await bot.add_cog(Roleplay(bot))
    await bot.add_cog(AIEmbed(bot))
    await bot.add_cog(Utilities(bot))
    await bot.add_cog(TicketDrop(bot))
    await bot.add_cog(ConfessionsDrop(bot))
    await bot.add_cog(BumpReminderDrop(bot))
    await bot.add_cog(Nsfw(bot))