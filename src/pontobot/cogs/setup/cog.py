# cogs/setup/cog.py
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from pontobot.i18n import resolve_lang, t

from .views import ReconfigureConfirmationView, SetupWizardView

if TYPE_CHECKING:
    from pontobot import PontoBot


class Setup(commands.Cog):
    def __init__(self, bot: "PontoBot"):
        self.bot = bot

    @app_commands.command(
        name="setup_pontobot", description=app_commands.locale_str("commands.setup_pontobot.description")
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Initializes the bot configuration."""
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        guild_data = await self.bot.db.get_guild(interaction.guild.id)
        if guild_data:
            view = ReconfigureConfirmationView(self.bot, author_id=interaction.user.id, lang=lang)
            await interaction.response.send_message(
                t("setup.already_configured_desc", lang=lang),
                view=view,
                ephemeral=True,
            )
            return

        view = SetupWizardView(self.bot, author_id=interaction.user.id, lang=lang)
        await interaction.response.send_message(
            t("setup.step_init", lang=lang),
            view=view,
            ephemeral=True,
        )
