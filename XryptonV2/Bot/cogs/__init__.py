from __future__ import annotations
from core import Astroz

# ____________ Commands ___________
from .commands.embed import EmbedScripting
from .commands.sticky import Sticky
from .commands.afk import afk
from .commands.help import Help
from .commands.general import General as GeneralCommands
from .commands.moderation import Moderation as ModCommands
from .commands.vcroles import Voice as VoiceCommands
from .commands.role import ServerRoles
# from .commands.nsfw import Nsfw as NsfwCommands
from .commands.ignore import Ignore
from .commands.roleplay import Roleplay as RoleplayCommands
from .commands.vcrole import Invcrole
from .commands.logging import Logging as LoggingCommands
from .commands.AutoPfp import AutoPfp
from .commands.extra import Extra
from .commands.welcome import Welcomer as WelcomeCog
from .commands.ai import Ai
from .commands.selfrole import Selfroles
from .commands.customize import Customize
from .commands.uwulock import UwuLock
from .commands.vanity import VanityStatus
from .commands.level import Leveling
from .commands.confessions import ConfessionsCog
from .commands.bumpreminder import BumpReminder
from .commands.giveaway import Giveaways
from .commands.premium import Premium
from .commands.owner import Owner
from .commands.raidmode import AutoMod
from .commands.misc import Misc
from .commands.games import Games
from .commands.tickets import Tickets
from .commands.fun import Fun
from .commands.images import Media
from .commands.anti import AntiNuke
# ____________ Events _____________
from .events.antiban import antiban

from .events.antichannel import antichannel
from .events.antiguild import antiguild
from .events.antirole import antirole
from .events.antibot import antibot
from .events.antikick import antikick
from .events.antiprune import antiprune
from .events.antiwebhook import antiwebhook
from .events.antiping import antipinginv
from .events.antiemostick import antiemostick
# from .events.antintegration import antintegration
from .events.autoblacklist import AutoBlacklist
from .events.antiemojid import antiemojid
from .events.antiemojiu import antiemojiu
from .events.Errors import Errors
from .events.on_guild import Guild
from .events.greet2 import greet
from .events.voiceupdate import Vcroles2
from .events.member_update import member_update
from .events.automodevent import automodevent
from .events.auto import Autorole
from .events.autorole import Autorole2
from .events.misc_events import MiscEvents
# ____________ Dropdowns _____________
from utils.dropdown import (
    Antinuke,
    Moderation,
    Antiraid,
    WelcomerDrop,
    Logging,
    Extras,
    General,
    Voice,
    Roleplay,
    AIEmbed,
    Utilities,
    Nsfw,
    TicketDrop,
)

# ____________ Setup _____________
async def setup(bot: Astroz):

    # __ Dropdown cogs (help system UI) __
    await bot.add_cog(Antinuke(bot))
    await bot.add_cog(Moderation(bot))
    await bot.add_cog(Antiraid(bot))
    await bot.add_cog(WelcomerDrop(bot))
    await bot.add_cog(Logging(bot))
    await bot.add_cog(Extras(bot))
    await bot.add_cog(General(bot))
    await bot.add_cog(Voice(bot))
    await bot.add_cog(Roleplay(bot))
    await bot.add_cog(AIEmbed(bot))
    await bot.add_cog(Utilities(bot))
    await bot.add_cog(TicketDrop(bot))
    # await bot.add_cog(Nsfw(bot))

    # __ Command cogs __
    await bot.add_cog(GeneralCommands(bot))
    await bot.add_cog(ModCommands(bot))
    await bot.add_cog(AntiNuke(bot))
    await bot.add_cog(EmbedScripting(bot))
    await bot.add_cog(Sticky(bot))
    await bot.add_cog(afk(bot))
    await bot.add_cog(Help(bot))
    await bot.add_cog(VoiceCommands(bot))
    await bot.add_cog(ServerRoles(bot))
    await bot.add_cog(Media(bot))
    # await bot.add_cog(NsfwCommands(bot))
    await bot.add_cog(Ignore(bot))
    await bot.add_cog(RoleplayCommands(bot))
    await bot.add_cog(Invcrole(bot))
    await bot.add_cog(LoggingCommands(bot))
    await bot.add_cog(AutoPfp(bot))
    await bot.add_cog(Extra(bot))
    await bot.add_cog(WelcomeCog(bot))
    await bot.add_cog(Ai(bot))
    await bot.add_cog(Selfroles(bot))
    await bot.add_cog(Customize(bot))
    await bot.add_cog(UwuLock(bot))
    await bot.add_cog(VanityStatus(bot))
    await bot.add_cog(Leveling(bot))
    await bot.add_cog(ConfessionsCog(bot))
    await bot.add_cog(BumpReminder(bot))
    await bot.add_cog(AutoMod(bot))
    await bot.add_cog(Premium(bot))
    await bot.add_cog(Owner(bot))
    await bot.add_cog(Giveaways(bot))
    await bot.add_cog(Misc(bot))
    await bot.add_cog(Games(bot))
    await bot.add_cog(Fun(bot))
    await bot.add_cog(Tickets(bot))
    # __ Event cogs __
    await bot.add_cog(antiban(bot))
    await bot.add_cog(antichannel(bot))
    await bot.add_cog(antiguild(bot))
    await bot.add_cog(antirole(bot))
    await bot.add_cog(antibot(bot))
    await bot.add_cog(antikick(bot))
    await bot.add_cog(antiprune(bot))
    await bot.add_cog(antiwebhook(bot))
    await bot.add_cog(antipinginv(bot))
    await bot.add_cog(antiemostick(bot))
    await bot.add_cog(automodevent(bot))
    await bot.add_cog(AutoBlacklist(bot))
    await bot.add_cog(antiemojid(bot))
    await bot.add_cog(antiemojiu(bot))
    await bot.add_cog(Guild(bot))
    await bot.add_cog(Errors(bot))
    await bot.add_cog(greet(bot))
    await bot.add_cog(Vcroles2(bot))
    await bot.add_cog(member_update(bot))
    await bot.add_cog(Autorole(bot))
    await bot.add_cog(Autorole2(bot))
    await bot.add_cog(MiscEvents(bot))