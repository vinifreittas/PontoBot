# cogs/management/cog.py
import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from pontobot.i18n import resolve_lang, t

from .views import ManagementView

if TYPE_CHECKING:
    from pontobot import PontoBot

logger = logging.getLogger(__name__)


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
        return self.log_stream.get_recent_lines(lines)

    def get_main_embed(self, lang: str = "en") -> discord.Embed:
        """Generates a dynamic, professional unified main dashboard embed interface."""
        latency = round(self.bot.latency * 1000)
        total_guilds = len(self.bot.guilds)
        total_users = sum(g.member_count for g in self.bot.guilds if g.member_count)
        uptime = str(timedelta(seconds=int(time.time() - self.start_time)))

        embed = discord.Embed(
            title=t("management.title", lang=lang),
            description=t("management.description", lang=lang),
            color=self.embed_colors.get("default", discord.Color.blue()),
        )

        status_msg = (
            t("management.status_attention", lang=lang)
            if self.bot.has_errors
            else t("management.status_normal", lang=lang)
        )
        embed.add_field(name=t("management.status_field", lang=lang), value=status_msg, inline=False)
        embed.add_field(
            name=t("management.performance_field", lang=lang),
            value=t("management.performance_val", lang=lang, latency=latency, uptime=uptime),
            inline=True,
        )
        embed.add_field(
            name=t("management.scope_field", lang=lang),
            value=t("management.scope_val", lang=lang, servers=total_guilds, users=total_users),
            inline=True,
        )

        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(text=t("management.footer", lang=lang), icon_url=self.bot.user.display_avatar.url)
        return embed

    @app_commands.command(name="management", description=app_commands.locale_str("commands.management.description"))
    @app_commands.guild_only()
    async def management(self, interaction: discord.Interaction):
        guild_config = await self.db.get_guild(interaction.guild_id)
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)

        if not await self.bot.has_access(interaction.user, interaction.guild):
            role = interaction.guild.get_role(guild_config.master_role_id) if guild_config else None
            master_name = role.name if role else "Master"
            embed = discord.Embed(
                title=t("common.permission_denied", lang=lang),
                description=t("common.permission_denied_desc", lang=lang, role=master_name),
                color=self.embed_colors.get("error", discord.Color.red()),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_message(
            embed=self.get_main_embed(lang=lang),
            view=ManagementView(self, owner_id=interaction.user.id, lang=lang),
            ephemeral=True,
        )
