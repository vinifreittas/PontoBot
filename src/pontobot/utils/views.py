# utils/views.py
import discord

from pontobot.i18n import t

VIEW_TIMEOUT = 300


class OwnedView(discord.ui.View):
    """Base View that restricts interactions to the original invoker."""

    def __init__(self, *, owner_id: int, timeout: float = VIEW_TIMEOUT):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                t("common.only_owner_can_interact", lang=interaction.locale),
                ephemeral=True,
            )
            return False
        return True
