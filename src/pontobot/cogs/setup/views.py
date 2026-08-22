# cogs/setup/views.py
import logging
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord

from pontobot.i18n import resolve_lang, t
from pontobot.utils.views import OwnedView

if TYPE_CHECKING:
    from pontobot import PontoBot

logger = logging.getLogger(__name__)


class TimezoneModal(discord.ui.Modal):
    def __init__(self, wizard_view: "SetupWizardView", lang: str = "en"):
        super().__init__(title=t("setup.modal_tz_title", lang=lang))
        self.wizard_view = wizard_view
        self.lang = lang

        self.tz_input = discord.ui.TextInput(
            label=t("setup.modal_tz_label", lang=lang),
            placeholder=t("setup.modal_tz_placeholder", lang=lang),
            default="America/Sao_Paulo",
            max_length=50,
        )
        self.add_item(self.tz_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        tz_str = self.tz_input.value.strip()
        try:
            ZoneInfo(tz_str)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            await interaction.response.send_message(
                t("setup.invalid_tz", lang=lang, tz=tz_str),
                ephemeral=True,
            )
            return

        self.wizard_view.timezone = tz_str
        await self.wizard_view._handle_timezone_complete(interaction)


class ReconfigureConfirmationView(OwnedView):
    """View asking for confirmation before reconfiguring an existing guild setup."""

    def __init__(self, bot: "PontoBot", author_id: int, lang: str = "en"):
        super().__init__(owner_id=author_id, timeout=60)
        self.bot = bot
        self.lang = lang
        self.confirm.label = t("setup.btn_reconfigure", lang=lang)
        self.cancel.label = t("setup.btn_cancel", lang=lang)

    @discord.ui.button(label="Reconfigure Bot", style=discord.ButtonStyle.danger, custom_id="confirm_reconfig")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        wizard = SetupWizardView(self.bot, author_id=self.owner_id, lang=lang)
        await interaction.response.edit_message(
            content=t("setup.reconfig_confirm", lang=lang),
            view=wizard,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_reconfig")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        await interaction.response.edit_message(
            content=t("setup.reconfig_cancel", lang=lang),
            view=None,
        )


class SetupWizardView(OwnedView):
    def __init__(self, bot: "PontoBot", author_id: int, lang: str = "en"):
        super().__init__(owner_id=author_id, timeout=300)
        self.bot = bot
        self.lang = lang

        # Configuration state
        self.master_role_id = None
        self.special_role_id = None
        self.clock_channel_id = None
        self.timezone = "America/Sao_Paulo"
        self.language = lang

        # Initialize Step 1
        self.add_item(
            discord.ui.RoleSelect(placeholder=t("setup.placeholder_master", lang=lang), custom_id="select_master")
        )

    def _update_view(self, interaction: discord.Interaction, content: str, item: discord.ui.Item):
        """Helper method to clear items, add a new component, and edit the message."""
        self.clear_items()
        self.add_item(item)
        return interaction.response.edit_message(content=content, view=self)

    async def _handle_master(self, interaction: discord.Interaction, values: list):
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        self.master_role_id = int(values[0])

        await self._update_view(
            interaction,
            content=t("setup.step_special", lang=lang),
            item=discord.ui.RoleSelect(
                placeholder=t("setup.placeholder_special", lang=lang), custom_id="select_special"
            ),
        )

    async def _handle_special(self, interaction: discord.Interaction, values: list):
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        self.special_role_id = int(values[0])

        await self._update_view(
            interaction,
            content=t("setup.step_channel", lang=lang),
            item=discord.ui.ChannelSelect(
                placeholder=t("setup.placeholder_channel", lang=lang),
                channel_types=[discord.ChannelType.text],
                custom_id="select_channel",
            ),
        )

    async def _handle_channel(self, interaction: discord.Interaction, values: list):
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        self.clock_channel_id = int(values[0])

        timezone_select = discord.ui.Select(
            placeholder=t("setup.placeholder_timezone", lang=lang),
            options=[
                discord.SelectOption(label="Brasilia (America/Sao_Paulo)", value="America/Sao_Paulo"),
                discord.SelectOption(label="Amazonas (America/Manaus)", value="America/Manaus"),
                discord.SelectOption(label="Fernando de Noronha (America/Noronha)", value="America/Noronha"),
                discord.SelectOption(label="New York (America/New_York)", value="America/New_York"),
                discord.SelectOption(label="London (Europe/London)", value="Europe/London"),
                discord.SelectOption(label="Paris (Europe/Paris)", value="Europe/Paris"),
                discord.SelectOption(label="UTC (Coordinated Universal Time)", value="UTC"),
                discord.SelectOption(label=t("setup.opt_tz_custom", lang=lang), value="custom"),
            ],
            custom_id="select_timezone",
        )
        await self._update_view(interaction, content=t("setup.step_timezone", lang=lang), item=timezone_select)

    async def _handle_timezone(self, interaction: discord.Interaction, values: list):
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        tz_str = values[0]
        if tz_str == "custom":
            await interaction.response.send_modal(TimezoneModal(wizard_view=self, lang=lang))
            return

        try:
            ZoneInfo(tz_str)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            await interaction.response.send_message(
                t("setup.invalid_tz", lang=lang, tz=tz_str),
                ephemeral=True,
            )
            return

        self.timezone = tz_str
        await self._handle_timezone_complete(interaction)

    async def _handle_timezone_complete(self, interaction: discord.Interaction):
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        language_select = discord.ui.Select(
            placeholder=t("setup.placeholder_language", lang=lang),
            options=[
                discord.SelectOption(label=t("setup.opt_lang_ptbr", lang=lang), value="pt-br"),
                discord.SelectOption(label=t("setup.opt_lang_en", lang=lang), value="en"),
            ],
            custom_id="select_language",
        )
        await self._update_view(interaction, content=t("setup.step_language", lang=lang), item=language_select)

    async def _handle_language(self, interaction: discord.Interaction, values: list):
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
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
                content=t("setup.setup_complete", lang=lang),
                view=self,
            )
        except Exception as e:
            logger.error("Error saving guild setup: %s", e)
            await interaction.response.edit_message(content=t("setup.setup_error", lang=lang), view=None)
        finally:
            self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await super().interaction_check(interaction):
            return False

        custom_id = interaction.data.get("custom_id")
        values = interaction.data.get("values", [])

        if not values:
            return True

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
