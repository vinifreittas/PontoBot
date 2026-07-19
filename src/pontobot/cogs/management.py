# cogs/management.py
import asyncio
import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from pontobot import PontoBot

logger = logging.getLogger(__name__)
VIEW_TIMEOUT = 300


# ==============================================================================
# UI COMPONENTS
# ==============================================================================


class UserManagementView(discord.ui.View):
    """View used for managing individual guild members."""

    def __init__(self, cog: "Management"):
        super().__init__(timeout=VIEW_TIMEOUT)
        self.cog = cog
        self.selected_member = None

        # Select menu built directly inline to keep components cohesive
        self.select_menu = discord.ui.UserSelect(
            placeholder="Select a member to manage...", min_values=1, max_values=1, row=0
        )
        self.select_menu.callback = self._user_select_callback
        self.add_item(self.select_menu)

    async def _user_select_callback(self, inter: discord.Interaction):
        self.selected_member = self.select_menu.values[0]

        embed = discord.Embed(
            title="👥 User Management Control Panel",
            description=f"Target Member: {self.selected_member.mention}\n\nChoose an action below:",
            color=discord.Color.blue(),
        )

        # Enable the action buttons now that a user is selected
        self.special_tag_btn.disabled = False
        await inter.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Special Tag", style=discord.ButtonStyle.primary, emoji="✨", row=1, disabled=True)
    async def special_tag_btn(self, inter: discord.Interaction, button: discord.ui.Button):
        if not self.selected_member or not inter.guild:
            return await inter.response.send_message("❌ No member selected.", ephemeral=True)

        guild_data = await self.cog.db.get_guild(inter.guild.id)
        special_role_name = guild_data.special_role_name

        role = discord.utils.get(inter.guild.roles, name=special_role_name)
        if not role:
            return await inter.response.send_message(f"❌ Role '{special_role_name}' not found.", ephemeral=True)

        await self.selected_member.add_roles(role)
        await inter.response.send_message(
            f"⭐ Special tag **{role.name}** assigned to {self.selected_member.mention}.", ephemeral=True
        )

    @discord.ui.button(label="Back to Menu", style=discord.ButtonStyle.gray, emoji="⬅️", row=1)
    async def back_button(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.edit_message(embed=self.cog.get_main_embed(), view=ManagementView(self.cog))
        self.stop()


class ManagementView(discord.ui.View):
    """Main administrative dashboard view."""

    def __init__(self, cog: "Management"):
        super().__init__(timeout=VIEW_TIMEOUT)
        self.cog = cog
        self.lock = asyncio.Lock()

        # Dropdown built inline to save vertical space and keep scope close
        self.dropdown = discord.ui.Select(
            placeholder="Select an administrative category...",
            min_values=1,
            max_values=1,
            row=0,
            options=[
                discord.SelectOption(
                    label="User Management", description="Manage members and moderation rules.", emoji="👥"
                ),
                discord.SelectOption(
                    label="Bot Configurations", description="Configure slowmodes and server categories.", emoji="⚙️"
                ),
                discord.SelectOption(
                    label="Bot Activity Logs", description="Review system tasks and live operations.", emoji="📜"
                ),
            ],
        )
        self.dropdown.callback = self._dropdown_callback
        self.add_item(self.dropdown)

    def _disable_all_items(self):
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True

    async def _dropdown_callback(self, inter: discord.Interaction):
        embed = discord.Embed().set_footer(
            text=f"Requested by {inter.user.name}", icon_url=inter.user.display_avatar.url
        )
        target_view = self

        match self.dropdown.values[0]:
            case "User Management":
                embed.title = "👥 User Management Dashboard"
                embed.description = "Select a user from the dropdown menu below, then choose an action to process."
                embed.color = discord.Color.blue()
                target_view = UserManagementView(self.cog)

            case "Bot Configurations":
                embed.title = "⚙️ Bot Configuration Dashboard"
                embed.description = "Nothing to see here."
                embed.color = discord.Color.orange()

            case "Bot Activity Logs":
                embed.title = "📜 System Activity Logs (Real-Time)"
                embed.description = f"```yaml\n{self.cog._get_last_logs()}```"
                embed.color = discord.Color.dark_gray()

        await inter.response.edit_message(embed=embed, view=target_view)

    @discord.ui.button(label="Home Menu", style=discord.ButtonStyle.secondary, emoji="🏠", row=1)
    async def home_button(self, inter: discord.Interaction, button: discord.ui.Button):
        await inter.response.edit_message(embed=self.cog.get_main_embed(), view=self)

    @discord.ui.button(label="Emergency Lockdown", style=discord.ButtonStyle.danger, emoji="🚨", row=1)
    async def lock_button(self, inter: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            embed = discord.Embed(
                title="🚨 EMERGENCY LOCKDOWN",
                description="❌ This button is not functional yet.",
                color=discord.Color.red(),
            ).set_footer(text=f"Triggered by {inter.user.name}", icon_url=inter.user.display_avatar.url)
            await inter.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Close Console", style=discord.ButtonStyle.gray, emoji="🔒", row=1)
    async def close_button(self, inter: discord.Interaction, button: discord.ui.Button):
        self._disable_all_items()
        await inter.response.edit_message(content="❌ *Administrative session terminated.*", embed=None, view=self)
        self.stop()


# ==============================================================================
# COG CLASS
# ==============================================================================


class Management(commands.Cog):
    """Cog responsible for managing the bot."""

    def __init__(self, bot: "PontoBot"):
        self.bot = bot
        self.db = self.bot.db
        self.embed_colors = self.bot.embed_colors
        self.log_stream = self.bot.log_stream
        self.start_time = self.bot.start_time

    def _get_last_logs(self, lines: int = 12) -> str:
        """Extracts the last N lines from the memory logging stream."""
        log_lines = self.log_stream.getvalue().splitlines()
        return "\n".join(log_lines[-lines:]) if log_lines else "No logs recorded yet."

    def get_main_embed(self) -> discord.Embed:
        """Generates a dynamic, professional unified main dashboard embed interface."""
        latency = round(self.bot.latency * 1000)
        total_guilds = len(self.bot.guilds)
        total_users = sum(g.member_count for g in self.bot.guilds if g.member_count)
        uptime = str(timedelta(seconds=int(time.time() - self.start_time)))

        embed = discord.Embed(
            title="🛠️ Central Control System | PontoBot",
            description="Secure administration operations panel. Use the tools and menus below to monitor metrics and manage global configurations.",
            color=self.embed_colors.get("default", discord.Color.blue()),
        )

        status_msg = (
            "🔴 **Attention:** Errors detected in system logs!"
            if self.bot.has_errors
            else "🟢 All operational systems are running normally."
        )
        embed.add_field(name="📌 System Status", value=status_msg, inline=False)
        embed.add_field(
            name="📊 Performance", value=f"⚡ **Latency:** `{latency}ms`\n⏱️ **Uptime:** `{uptime}`", inline=True
        )
        embed.add_field(
            name="🌐 Scope", value=f"🖥️ **Servers:** `{total_guilds}`\n👥 **Users:** `{total_users}`", inline=True
        )

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(
                text="Restricted Access • Administrator Console", icon_url=self.bot.user.display_avatar.url
            )
        return embed

    @app_commands.command(name="management", description="Bot management menu.")
    @app_commands.guild_only()
    async def management(self, interaction: discord.Interaction):
        guild_config = await self.db.get_guild(interaction.guild_id)

        if not await self.bot.has_access(interaction.user, interaction.guild):
            embed = discord.Embed(
                title="⛔ Permission Denied",
                description=f"You need the `{guild_config.master_role_name}` role to manage the bot.",
                color=self.embed_colors.get("error", discord.Color.red()),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_message(embed=self.get_main_embed(), view=ManagementView(self), ephemeral=True)


async def setup(bot: "PontoBot"):
    await bot.add_cog(Management(bot))
