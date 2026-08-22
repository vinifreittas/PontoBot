# cogs/attendance/views.py
import discord

from pontobot.utils.views import OwnedView

DAYS_PER_PAGE = 5


class PaginationView(OwnedView):
    """View to navigate through paginated embeds using Previous and Next buttons."""

    def __init__(self, pages: list[discord.Embed], owner_id: int, timeout: float = 180):
        super().__init__(owner_id=owner_id, timeout=timeout)
        self.pages = pages
        self.current = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current >= len(self.pages) - 1

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current > 0:
            self.current -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current < len(self.pages) - 1:
            self.current += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current], view=self)
