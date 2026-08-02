from unittest.mock import AsyncMock, MagicMock

import pytest

from pontobot.cogs.setup import ReconfigureConfirmationView, Setup, SetupWizardView, TimezoneModal


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.db = AsyncMock()
    return bot


class TestTimezoneModal:
    async def test_valid_timezone_submits_successfully(self, mock_bot):
        wizard = SetupWizardView(mock_bot, author_id=123)
        modal = TimezoneModal(wizard_view=wizard)
        modal.tz_input._value = " Europe/Berlin "

        interaction = AsyncMock()
        await modal.on_submit(interaction)

        assert wizard.timezone == "Europe/Berlin"
        interaction.response.edit_message.assert_called_once()

    async def test_invalid_timezone_shows_error(self, mock_bot):
        wizard = SetupWizardView(mock_bot, author_id=123)
        modal = TimezoneModal(wizard_view=wizard)
        modal.tz_input._value = "Not/A_Real_Timezone"

        interaction = AsyncMock()
        await modal.on_submit(interaction)

        assert wizard.timezone == "America/Sao_Paulo"  # Unchanged default
        interaction.response.send_message.assert_called_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "Invalid timezone" in args[0]
        assert kwargs.get("ephemeral") is True


class TestReconfigureConfirmationView:
    async def test_interaction_check_owner_allowed(self, mock_bot):
        view = ReconfigureConfirmationView(mock_bot, author_id=123)
        interaction = AsyncMock()
        interaction.user.id = 123

        assert await view.interaction_check(interaction) is True

    async def test_interaction_check_non_owner_denied(self, mock_bot):
        view = ReconfigureConfirmationView(mock_bot, author_id=123)
        interaction = AsyncMock()
        interaction.user.id = 999

        assert await view.interaction_check(interaction) is False
        interaction.response.send_message.assert_called_once()

    async def test_confirm_launches_setup_wizard(self, mock_bot):
        view = ReconfigureConfirmationView(mock_bot, author_id=123)
        interaction = AsyncMock()

        await view.confirm.callback(interaction)

        interaction.response.edit_message.assert_called_once()
        _, kwargs = interaction.response.edit_message.call_args
        assert isinstance(kwargs["view"], SetupWizardView)

    async def test_cancel_removes_view(self, mock_bot):
        view = ReconfigureConfirmationView(mock_bot, author_id=123)
        interaction = AsyncMock()

        await view.cancel.callback(interaction)

        interaction.response.edit_message.assert_called_once()
        _, kwargs = interaction.response.edit_message.call_args
        assert kwargs["view"] is None
        assert "cancelled" in kwargs["content"].lower()


class TestSetupWizardViewTimezone:
    async def test_preset_timezone_selection(self, mock_bot):
        wizard = SetupWizardView(mock_bot, author_id=123)
        interaction = AsyncMock()

        await wizard._handle_timezone(interaction, ["Europe/London"])

        assert wizard.timezone == "Europe/London"
        interaction.response.edit_message.assert_called_once()

    async def test_custom_timezone_opens_modal(self, mock_bot):
        wizard = SetupWizardView(mock_bot, author_id=123)
        interaction = AsyncMock()

        await wizard._handle_timezone(interaction, ["custom"])

        interaction.response.send_modal.assert_called_once()
        modal_arg = interaction.response.send_modal.call_args[0][0]
        assert isinstance(modal_arg, TimezoneModal)


class TestSetupCommand:
    async def test_setup_unconfigured_guild_starts_wizard(self, mock_bot):
        mock_bot.db.get_guild.return_value = None
        cog = Setup(mock_bot)

        interaction = AsyncMock()
        interaction.guild.id = 456
        interaction.user.id = 123

        await cog.setup.callback(cog, interaction)

        interaction.response.send_message.assert_called_once()
        _, kwargs = interaction.response.send_message.call_args
        assert isinstance(kwargs["view"], SetupWizardView)

    async def test_setup_configured_guild_shows_reconfig_prompt(self, mock_bot):
        mock_bot.db.get_guild.return_value = MagicMock()
        cog = Setup(mock_bot)

        interaction = AsyncMock()
        interaction.guild.id = 456
        interaction.user.id = 123

        await cog.setup.callback(cog, interaction)

        interaction.response.send_message.assert_called_once()
        args, kwargs = interaction.response.send_message.call_args
        message_text = args[0] if args else kwargs.get("content", "")
        assert "already configured" in message_text.lower()
