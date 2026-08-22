# cogs/management/views.py
import logging
from typing import TYPE_CHECKING

import discord

from pontobot.i18n import resolve_lang, t
from pontobot.utils.views import OwnedView

if TYPE_CHECKING:
    from .cog import Management

logger = logging.getLogger(__name__)
VIEW_TIMEOUT = 300


class UserManagementView(OwnedView):
    """View used for managing individual guild members."""

    def __init__(self, cog: "Management", owner_id: int, lang: str = "en"):
        super().__init__(owner_id=owner_id, timeout=VIEW_TIMEOUT)
        self.cog = cog
        self.lang = lang
        self.selected_member = None

        self.select_menu = discord.ui.UserSelect(
            placeholder=t("management.user_mgmt_placeholder", lang=lang), min_values=1, max_values=1, row=0
        )
        self.select_menu.callback = self._user_select_callback
        self.add_item(self.select_menu)

        self.special_tag_btn.label = t("management.btn_special_tag", lang=lang)
        self.back_button.label = t("management.btn_back_to_menu", lang=lang)

    async def _user_select_callback(self, inter: discord.Interaction):
        lang = resolve_lang(locale=inter.locale, ephemeral=True)
        self.selected_member = self.select_menu.values[0]

        embed = discord.Embed(
            title=t("management.user_mgmt_title", lang=lang),
            description=t("management.user_mgmt_desc", lang=lang, member=self.selected_member.mention),
            color=discord.Color.blue(),
        )

        self.special_tag_btn.disabled = False
        await inter.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Special Tag", style=discord.ButtonStyle.primary, emoji="✨", row=1, disabled=True)
    async def special_tag_btn(self, inter: discord.Interaction, button: discord.ui.Button):
        lang = resolve_lang(locale=inter.locale, ephemeral=True)
        if not self.selected_member or not inter.guild:
            return await inter.response.send_message(t("management.no_member_selected", lang=lang), ephemeral=True)

        guild_data = await self.cog.db.get_guild(inter.guild.id)
        special_role_id = guild_data.special_role_id if guild_data else None

        role = inter.guild.get_role(special_role_id) if special_role_id else None
        if not role:
            return await inter.response.send_message(t("management.special_role_not_found", lang=lang), ephemeral=True)

        try:
            await self.selected_member.add_roles(role)
            await inter.response.send_message(
                t("management.special_tag_assigned", lang=lang, role=role.name, member=self.selected_member.mention),
                ephemeral=True,
            )
        except discord.Forbidden:
            await inter.response.send_message(t("management.role_perm_error", lang=lang), ephemeral=True)

    @discord.ui.button(label="Back to Menu", style=discord.ButtonStyle.gray, emoji="⬅️", row=1)
    async def back_button(self, inter: discord.Interaction, button: discord.ui.Button):
        lang = resolve_lang(locale=inter.locale, ephemeral=True)
        await inter.response.edit_message(
            embed=self.cog.get_main_embed(lang=lang), view=ManagementView(self.cog, owner_id=self.owner_id, lang=lang)
        )
        self.stop()


class ManagementView(OwnedView):
    """Main administrative dashboard view."""

    def __init__(self, cog: "Management", owner_id: int, lang: str = "en"):
        super().__init__(owner_id=owner_id, timeout=VIEW_TIMEOUT)
        self.cog = cog
        self.lang = lang

        self.dropdown = discord.ui.Select(
            placeholder=t("management.category_placeholder", lang=lang),
            min_values=1,
            max_values=1,
            row=0,
            options=[
                discord.SelectOption(
                    label=t("management.cat_user_mgmt", lang=lang),
                    description=t("management.cat_user_mgmt_desc", lang=lang),
                    value="User Management",
                    emoji="👥",
                ),
                discord.SelectOption(
                    label=t("management.cat_activity_logs", lang=lang),
                    description=t("management.cat_activity_logs_desc", lang=lang),
                    value="Bot Activity Logs",
                    emoji="📜",
                ),
            ],
        )
        self.dropdown.callback = self._dropdown_callback
        self.add_item(self.dropdown)

        self.home_button.label = t("management.btn_home_menu", lang=lang)
        self.close_button.label = t("management.btn_close_console", lang=lang)

    def _disable_all_items(self):
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True

    async def _dropdown_callback(self, inter: discord.Interaction):
        lang = resolve_lang(locale=inter.locale, ephemeral=True)
        embed = discord.Embed().set_footer(
            text=t("management.requested_by", lang=lang, user=inter.user.name), icon_url=inter.user.display_avatar.url
        )
        target_view = self

        match self.dropdown.values[0]:
            case "User Management":
                embed.title = t("management.user_mgmt_dashboard_title", lang=lang)
                embed.description = t("management.user_mgmt_dashboard_desc", lang=lang)
                embed.color = discord.Color.blue()
                target_view = UserManagementView(self.cog, owner_id=self.owner_id, lang=lang)

            case "Bot Activity Logs":
                embed.title = t("management.logs_title", lang=lang)
                embed.description = f"```yaml\n{self.cog._get_last_logs()}```"
                embed.color = discord.Color.dark_gray()

        await inter.response.edit_message(embed=embed, view=target_view)

    @discord.ui.button(label="Home Menu", style=discord.ButtonStyle.secondary, emoji="🏠", row=1)
    async def home_button(self, inter: discord.Interaction, button: discord.ui.Button):
        lang = resolve_lang(locale=inter.locale, ephemeral=True)
        await inter.response.edit_message(embed=self.cog.get_main_embed(lang=lang), view=self)

    @discord.ui.button(label="Close Console", style=discord.ButtonStyle.gray, emoji="🔒", row=1)
    async def close_button(self, inter: discord.Interaction, button: discord.ui.Button):
        lang = resolve_lang(locale=inter.locale, ephemeral=True)
        self._disable_all_items()
        await inter.response.edit_message(content=t("management.session_closed", lang=lang), embed=None, view=self)
        self.stop()
