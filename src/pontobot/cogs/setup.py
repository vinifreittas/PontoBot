# cogs/setup.py
import logging
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from pontobot import PontoBot

logger = logging.getLogger(__name__)


# ==============================================================================
# UI COMPONENTS
# ==============================================================================


class TimezoneModal(discord.ui.Modal, title="Timezone Configuration"):
    tz_input = discord.ui.TextInput(
        label="Timezone (IANA format)",
        placeholder="e.g. Europe/Berlin, Asia/Tokyo, America/Chicago",
        default="America/Sao_Paulo",
        max_length=50,
    )

    def __init__(self, wizard_view: "SetupWizardView"):
        super().__init__()
        self.wizard_view = wizard_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        tz_str = self.tz_input.value.strip()
        try:
            ZoneInfo(tz_str)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            await interaction.response.send_message(
                f"❌ Invalid timezone: `{tz_str}`. Please enter a valid IANA timezone identifier (e.g., `Europe/Berlin`, `Asia/Tokyo`).",
                ephemeral=True,
            )
            return

        self.wizard_view.timezone = tz_str
        await self.wizard_view._handle_timezone_complete(interaction)


class ReconfigureConfirmationView(discord.ui.View):
    """View asking for confirmation before reconfiguring an existing guild setup."""

    def __init__(self, bot: "PontoBot", author_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "⛔ Only the administrator who initiated setup can respond.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Reconfigure Bot", style=discord.ButtonStyle.danger, custom_id="confirm_reconfig")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        wizard = SetupWizardView(self.bot, author_id=self.author_id)
        await interaction.response.edit_message(
            content="Let's reconfigure PontoBot! First, select the **Master Role** (the role that will manage the system).",
            view=wizard,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_reconfig")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(
            content="⚙️ Setup cancelled. Existing configuration was kept.",
            view=None,
        )


class SetupWizardView(discord.ui.View):
    def __init__(self, bot: "PontoBot", author_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.author_id = author_id

        # Configuration state
        self.master_role_id = None
        self.special_role_id = None
        self.clock_channel_id = None
        self.timezone = "America/Sao_Paulo"
        self.language = "en"

        # Initialize Step 1
        self.add_item(discord.ui.RoleSelect(placeholder="Select the Master Role...", custom_id="select_master"))

    def _update_view(self, interaction: discord.Interaction, content: str, item: discord.ui.Item):
        """Helper method to clear items, add a new component, and edit the message."""
        self.clear_items()
        self.add_item(item)
        return interaction.response.edit_message(content=content, view=self)

    async def _handle_master(self, interaction: discord.Interaction, values: list):
        self.master_role_id = int(values[0])

        await self._update_view(
            interaction,
            content="Great! Now, select the **Special Role**.",
            item=discord.ui.RoleSelect(placeholder="Select the Special Role...", custom_id="select_special"),
        )

    async def _handle_special(self, interaction: discord.Interaction, values: list):
        self.special_role_id = int(values[0])

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
                discord.SelectOption(label="Brasília (America/Sao_Paulo)", value="America/Sao_Paulo"),
                discord.SelectOption(label="Amazonas (America/Manaus)", value="America/Manaus"),
                discord.SelectOption(label="Fernando de Noronha (America/Noronha)", value="America/Noronha"),
                discord.SelectOption(label="New York (America/New_York)", value="America/New_York"),
                discord.SelectOption(label="London (Europe/London)", value="Europe/London"),
                discord.SelectOption(label="Paris (Europe/Paris)", value="Europe/Paris"),
                discord.SelectOption(label="UTC (Coordinated Universal Time)", value="UTC"),
                discord.SelectOption(label="Other (Custom IANA Timezone...)", value="custom"),
            ],
            custom_id="select_timezone",
        )
        await self._update_view(
            interaction, content="Almost done! Next, select your server's **timezone**.", item=timezone_select
        )

    async def _handle_timezone(self, interaction: discord.Interaction, values: list):
        tz_str = values[0]
        if tz_str == "custom":
            await interaction.response.send_modal(TimezoneModal(wizard_view=self))
            return

        try:
            ZoneInfo(tz_str)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            await interaction.response.send_message(
                f"❌ Invalid timezone: `{tz_str}`.",
                ephemeral=True,
            )
            return

        self.timezone = tz_str
        await self._handle_timezone_complete(interaction)

    async def _handle_timezone_complete(self, interaction: discord.Interaction):
        language_select = discord.ui.Select(
            placeholder="Select your Language...",
            options=[
                discord.SelectOption(label="Português (Brasil)", value="pt-br"),
                discord.SelectOption(label="English", value="en"),
            ],
            custom_id="select_language",
        )
        await self._update_view(
            interaction, content="Almost done! Lastly, select your server's **language**.", item=language_select
        )

    async def _handle_language(self, interaction: discord.Interaction, values: list):
        self.language = values[0]

        try:
            await self.bot.db.add_guild(
                guild_id=interaction.guild.id,
                master_role_id=self.master_role_id,
                special_role_id=self.special_role_id,
                clock_channel_id=self.clock_channel_id,
                timezone=self.timezone,
                language=self.language,
            )
            self.bot.dispatch("guild_setup", interaction.guild)

            self.clear_items()
            await interaction.response.edit_message(
                content="✅ **Setup Complete!** Your server has been successfully registered in the database.",
                view=self,
            )
        except Exception as e:
            logger.error("Error saving guild setup: %s", e)
            await interaction.response.edit_message(
                content="❌ An error occurred while saving the configuration. Please try again later.", view=None
            )
        finally:
            self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "⛔ Only the administrator who initiated setup can use this wizard.",
                ephemeral=True,
            )
            return False

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
            "select_language": self._handle_language,
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
            view = ReconfigureConfirmationView(self.bot, author_id=interaction.user.id)
            await interaction.response.send_message(
                "⚙️ **This server is already configured.**\nDo you want to reconfigure PontoBot? This will overwrite your existing configuration.",
                view=view,
                ephemeral=True,
            )
            return

        view = SetupWizardView(self.bot, author_id=interaction.user.id)
        await interaction.response.send_message(
            "Let's configure PontoBot! First, select the **Master Role** (the role that will manage the system).",
            view=view,
            ephemeral=True,
        )


async def setup(bot: "PontoBot") -> None:
    await bot.add_cog(Setup(bot))
