# cogs/attendance/cog.py
import logging
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from pontobot.i18n import resolve_lang, t
from pontobot.utils.embeds import create_base_embed, send_error_embed, truncate_text

from .helpers import (
    filter_dates_by_period,
    first_time_guild_onboarding,
    get_period_label,
    parse_custom_date,
    post_offline_recovery_routine,
    process_general_report,
    process_individual_report,
)

if TYPE_CHECKING:
    from pontobot import PontoBot

logger = logging.getLogger(__name__)


class Attendance(commands.Cog):
    """Cog responsible for managing user attendance records and synchronization."""

    def __init__(self, bot: "PontoBot"):
        self.bot = bot
        self.db = self.bot.db
        self.embed_colors = self.bot.embed_colors
        self._has_synced: bool = False

    # -------------------------- Lifecycle Events --------------------------

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Executed ONLY when the bot starts up. Synchronizes past history for existing guilds."""
        if self._has_synced:
            return

        self._has_synced = True
        logger.info("🔄 Bot started. Running post-offline recovery routine...")
        for guild in self.bot.guilds:
            if guild_data := await self.db.get_guild(guild.id):
                await post_offline_recovery_routine(self.bot, guild, guild_data)
        logger.info("✅ Initial sync scan completed.")

    @commands.Cog.listener()
    async def on_guild_setup(self, guild: discord.Guild) -> None:
        """Executed ONLY when a new guild completes /setup. Performs guild onboarding."""
        logger.info("⚡ First-time setup detected for guild: %s (%s)", guild.name, guild.id)
        if guild_data := await self.db.get_guild(guild.id):
            await first_time_guild_onboarding(self.db, guild, guild_data)

    # -------------------------- Commands --------------------------

    @commands.command(name="ponto", aliases=["checkin"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ponto(self, ctx: commands.Context) -> None:
        """Text alternative method to record presence parameters."""
        guild_data = await self.db.get_guild(ctx.guild.id)
        if not guild_data:
            lang = await self.bot.get_guild_language(ctx.guild.id) if ctx.guild else "en"
            return await ctx.message.reply(t("common.unconfigured_guild_short", lang=lang), delete_after=10)

        lang = guild_data.language

        if ctx.channel.id != guild_data.clock_channel_id:
            embed = create_base_embed(
                self.embed_colors,
                t("attendance.incorrect_channel_title", lang=lang),
                t("attendance.incorrect_channel_desc", lang=lang),
                "error",
            )
            return await ctx.message.reply(embed=embed, delete_after=10)

        tz = ZoneInfo(guild_data.timezone)
        now = datetime.now(tz)

        member = await self.db.ensure_member(
            ctx.guild.id, ctx.author.id, ctx.author.name, ctx.author.display_name, ctx.message.created_at.date()
        )
        if not await self.db.register_attendance(member, now):
            embed = create_base_embed(
                self.embed_colors,
                t("attendance.duplicate_record_title", lang=lang),
                t("attendance.duplicate_record_desc", lang=lang, user=ctx.author.mention),
                "warning",
            )
            return await ctx.message.reply(embed=embed, delete_after=10)

        await self.db.set_last_verification(ctx.guild.id, now)

        success_embed = discord.Embed(
            title=t("attendance.confirmed_title", lang=lang), color=self.embed_colors["success"], timestamp=now
        )
        success_embed.set_thumbnail(url=ctx.author.display_avatar.url)
        success_embed.set_footer(text=t("attendance.footer", lang=lang))

        fields = [
            (t("attendance.field_member", lang=lang), ctx.author.mention),
            (t("attendance.field_nickname", lang=lang), ctx.author.display_name),
            (t("attendance.field_date", lang=lang), now.strftime("%d/%m/%Y")),
            (t("attendance.field_time", lang=lang), now.strftime("%H:%M:%S")),
        ]
        for name, value in fields:
            success_embed.add_field(name=name, value=value, inline=True)

        await ctx.message.reply(embed=success_embed)

    async def period_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Provides dynamic suggestions for the period argument."""
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)
        options = [
            app_commands.Choice(name=t("periods.all", lang=lang), value="all"),
            app_commands.Choice(name=t("periods.today", lang=lang), value="today"),
            app_commands.Choice(name=t("periods.7days", lang=lang), value="7days"),
            app_commands.Choice(name=t("periods.30days", lang=lang), value="30days"),
        ]
        return [op for op in options if current.lower() in op.name.lower() or current.lower() in op.value.lower()][:25]

    @app_commands.command(
        name="attendance",
        description=app_commands.locale_str("commands.attendance.description"),
    )
    @app_commands.describe(
        user=app_commands.locale_str("commands.attendance.param.user.description"),
        period=app_commands.locale_str("commands.attendance.param.period.description"),
    )
    @app_commands.autocomplete(period=period_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def attendance(
        self, interaction: discord.Interaction, user: discord.Member | None = None, period: str = "all"
    ) -> None:
        """Slash command processor for tracking analytics outputs."""
        guild_data = await self.db.get_guild(interaction.guild.id)
        if not guild_data:
            lang_err = resolve_lang(locale=interaction.locale, ephemeral=True)
            return await interaction.response.send_message(
                t("common.unconfigured_guild_short", lang=lang_err), ephemeral=True
            )

        is_ephemeral = user is not None
        lang = resolve_lang(locale=interaction.locale, guild_lang=guild_data.language, ephemeral=is_ephemeral)

        if not await self.bot.has_access(interaction.user, interaction.guild) and interaction.user != user:
            role = interaction.guild.get_role(guild_data.master_role_id) if guild_data else None
            role_name = role.name if role else "Master"
            desc = t("common.permission_denied_desc", lang=lang, role=role_name)
            return await send_error_embed(
                self.embed_colors, interaction, t("common.permission_denied", lang=lang), desc
            )

        tz = ZoneInfo(guild_data.timezone)

        if period in ["all", "today", "7days", "30days"]:
            label_period = get_period_label(period, lang=lang)
            target_dates = filter_dates_by_period(period, tz)
        else:
            validated_date = parse_custom_date(period)
            if not validated_date:
                desc = t("attendance.invalid_date_desc", lang=lang)
                return await send_error_embed(
                    self.embed_colors, interaction, t("attendance.invalid_date_title", lang=lang), desc
                )

            if validated_date > datetime.now(tz).date():
                return await send_error_embed(
                    self.embed_colors,
                    interaction,
                    t("attendance.future_date_title", lang=lang),
                    t("attendance.future_date_desc", lang=lang),
                    "warning",
                )

            period = "custom"
            date_fmt = validated_date.strftime("%d/%m/%Y")
            label_period = get_period_label("custom", lang=lang, date_str=date_fmt)
            target_dates = [validated_date]

        await interaction.response.defer(ephemeral=is_ephemeral)

        if user is None:
            await process_general_report(self, interaction, label_period, period, target_dates, guild_data)
        else:
            await process_individual_report(self, interaction, user, label_period, period, target_dates)

    @app_commands.command(name="ranking", description=app_commands.locale_str("commands.ranking.description"))
    async def ranking(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        lang = resolve_lang(locale=interaction.locale, ephemeral=True)

        leaderboard = await self.db.get_ranking(interaction.guild.id)
        embed = create_base_embed(
            self.embed_colors,
            t("ranking.title", lang=lang),
            t("ranking.description", lang=lang),
            "success",
        )

        podium_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        checkins_lbl = t("ranking.checkins_suffix", lang=lang)
        ranking_lines = [
            f"{podium_emojis.get(pos, '🔹')} `{pos:02d}#` **{nick}** — `{qty} {checkins_lbl}`"
            for pos, (nick, qty) in enumerate(leaderboard, start=1)
        ]
        ranking_text = "\n".join(ranking_lines) if ranking_lines else t("ranking.no_data", lang=lang)

        embed.add_field(name=t("ranking.field_placement", lang=lang), value=truncate_text(ranking_text), inline=False)
        embed.set_footer(text=t("ranking.footer", lang=lang))
        await interaction.followup.send(embed=embed, ephemeral=True)
