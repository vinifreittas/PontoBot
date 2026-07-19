# cogs/setup.py
import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from pontobot import PontoBot

logger = logging.getLogger(__name__)


# ==============================================================================
# UI COMPONENTS
# ==============================================================================


class SetupWizardView(discord.ui.View):
    def __init__(self, bot: "PontoBot"):
        super().__init__(timeout=300)
        self.bot = bot

        # Configuration state
        self.master_role_name = None
        self.special_role_name = None
        self.clock_channel_id = None
        self.timezone = "America/Sao_Paulo"

        # Initialize Step 1
        self.add_item(discord.ui.RoleSelect(placeholder="Select the Master Role...", custom_id="select_master"))

    def _update_view(self, interaction: discord.Interaction, content: str, item: discord.ui.Item):
        """Helper method to clear items, add a new component, and edit the message."""
        self.clear_items()
        self.add_item(item)
        return interaction.response.edit_message(content=content, view=self)

    async def _handle_master(self, interaction: discord.Interaction, values: list):
        role = interaction.guild.get_role(int(values[0]))
        self.master_role_name = role.name if role else "Master"

        await self._update_view(
            interaction,
            content="Great! Now, select the **Special Role**.",
            item=discord.ui.RoleSelect(placeholder="Select the Special Role...", custom_id="select_special"),
        )

    async def _handle_special(self, interaction: discord.Interaction, values: list):
        role = interaction.guild.get_role(int(values[0]))
        self.special_role_name = role.name if role else "Special"

        await self._update_view(
            interaction,
            content="Awesome. Next, choose the **text channel** where points will be logged.",
            item=discord.ui.ChannelSelect(
                placeholder="Select the tracking channel...",
                channel_types=[discord.ChannelType.text],
                custom_id="select_channel",
            ),
        )

    async def _handle_channel(self, interaction: discord.Interaction, values: list):
        self.clock_channel_id = int(values[0])

        timezone_select = discord.ui.Select(
            placeholder="Select your Timezone...",
            options=[
                discord.SelectOption(label="Brasília (UTC-3)", value="America/Sao_Paulo"),
                discord.SelectOption(label="Amazonas (UTC-4)", value="America/Manaus"),
                discord.SelectOption(label="Fernando de Noronha (UTC-2)", value="America/Noronha"),
            ],
            custom_id="select_timezone",
        )
        await self._update_view(
            interaction, content="Almost done! Lastly, select your server's **timezone**.", item=timezone_select
        )

    async def _handle_timezone(self, interaction: discord.Interaction, values: list):
        self.timezone = values[0]

        try:
            await self.bot.db.add_guild(
                guild_id=interaction.guild.id,
                master_role_name=self.master_role_name,
                special_role_name=self.special_role_name,
                clock_channel_id=self.clock_channel_id,
                timezone=self.timezone,
            )
            self.bot.dispatch("guild_setup", interaction.guild)

            self.clear_items()
            await interaction.response.edit_message(
                content="✅ **Setup Complete!** Your server has been successfully registered in the database.",
                view=self,
            )
        except Exception as e:
            logger.error(f"Error saving guild setup: {e}")
            await interaction.response.edit_message(
                content="❌ An error occurred while saving the configuration. Please try again later.", view=None
            )
        finally:
            self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        values = interaction.data.get("values", [])

        if not values:
            return True

        # Action map to eliminate the long if/elif chain
        handlers = {
            "select_master": self._handle_master,
            "select_special": self._handle_special,
            "select_channel": self._handle_channel,
            "select_timezone": self._handle_timezone,
        }

        handler = handlers.get(custom_id)
        if handler:
            await handler(interaction, values)

        return True


# ==============================================================================
# COG CLASS
# ==============================================================================


class Setup(commands.Cog):
    def __init__(self, bot: "PontoBot"):
        self.bot = bot

    @app_commands.command(name="setup_pontobot", description="Configure PontoBot on your server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Initializes the bot configuration."""
        guild_data = await self.bot.db.get_guild(interaction.guild.id)
        if guild_data:
            await interaction.response.send_message("⚙️ This server is already configured.", ephemeral=True)
            return

        view = SetupWizardView(self.bot)
        await interaction.response.send_message(
            "Let's configure PontoBot! First, select the **Master Role** (the role that will manage the system).",
            view=view,
            ephemeral=True,
        )


async def setup(bot: "PontoBot") -> None:
    await bot.add_cog(Setup(bot))
