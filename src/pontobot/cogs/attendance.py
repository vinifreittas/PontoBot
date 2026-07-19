# cogs/attendance.py
import logging
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from pontobot import PontoBot

logger = logging.getLogger(__name__)


class Attendance(commands.Cog):
    """Cog responsible for managing user attendance records and synchronization."""

    MAX_EMBED_CHARS = 1020

    def __init__(self, bot: "PontoBot"):
        self.bot = bot
        self.db = self.bot.db
        self.embed_colors = self.bot.embed_colors

        self.period_days: dict[str, int] = {"today": 1, "7days": 7, "30days": 30}
        self.labels: dict[str, str] = {
            "all": "Full History",
            "today": "Today",
            "7days": "Last 7 days",
            "30days": "Last 30 days",
            "custom": "Specific Day",
        }

    # -------------------------- Helper Functions --------------------------

    async def _get_tz(self, guild_id: int) -> ZoneInfo:
        """Returns the ZoneInfo for a guild, falling back to the default."""
        guild_data = await self.db.get_guild(guild_id)
        return ZoneInfo(guild_data.timezone)

    def _filter_dates_by_period(self, period: str, tz: ZoneInfo) -> list[date]:
        """Calculates a list of targeted dates based on the defined period window."""
        if period not in self.period_days:
            return []
        today_dt = datetime.now(tz)
        return [(today_dt - timedelta(days=i)).date() for i in range(self.period_days[period])]

    def _parse_custom_date(self, date_str: str) -> date | None:
        """Validates and parses a custom date string into a date object."""
        try:
            return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
        except ValueError:
            return None

    @classmethod
    def _truncate_text(cls, text: str) -> str:
        """Safely truncates string contents to respect strict Discord API limits."""
        return f"{text[: cls.MAX_EMBED_CHARS]}..." if len(text) > cls.MAX_EMBED_CHARS else text

    def _create_base_embed(
        self, title: str, description: str, color_key: str, timestamp: datetime | None = None
    ) -> discord.Embed:
        """Helper to create a unified standard embed structure."""
        return discord.Embed(
            title=title, description=description, color=self.embed_colors[color_key], timestamp=timestamp
        )

    async def _send_error_embed(
        self, interaction: discord.Interaction, title: str, desc: str, color_key: str = "error"
    ) -> None:
        """Standard helper to respond with error or warning messages quickly."""
        embed = self._create_base_embed(title, desc, color_key)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------- Lifecycle Events --------------------------

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Executed ONLY when the bot starts up. Synchronizes past history for existing guilds."""
        logger.info("🔄 Bot started. Running post-offline recovery routine...")
        for guild in self.bot.guilds:
            if guild_data := await self.db.get_guild(guild.id):
                await self._post_offline_recovery_routine(guild, guild_data)
        logger.info("✅ Initial sync scan completed.")

    @commands.Cog.listener()
    async def on_guild_setup(self, guild: discord.Guild) -> None:
        """Executed ONLY when a new guild completes /setup. Performs guild onboarding."""
        logger.info(f"⚡ First-time setup detected for guild: {guild.name} ({guild.id})")
        if guild_data := await self.db.get_guild(guild.id):
            await self._first_time_guild_onboarding(guild, guild_data)

    # -------------------------- Sync Routines --------------------------

    async def _post_offline_recovery_routine(self, guild: discord.Guild, guild_data) -> None:
        """Routine for legacy servers: handles time elapsed while the bot was offline."""
        channel = self.bot.get_channel(guild_data.clock_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        server_members: set[int] = {member.id for member in guild.members}
        try:
            await self._remove_absent_users(guild.id, server_members)
            await self._sync_offline_checkins(guild, channel, server_members, guild_data)
        except Exception as e:
            logger.error(f"❌ Error during recovery for guild {guild.id}: {e}", exc_info=True)

    async def _first_time_guild_onboarding(self, guild: discord.Guild, guild_data) -> None:
        """Routine for new servers: populates the database from scratch without error reports."""
        try:
            logger.info(f"📥 Populating initial database records for guild: {guild.name}")

            tz = ZoneInfo(guild_data.timezone)
            await self.db.set_last_verification(guild.id, datetime.now(tz))
            logger.info(f"✅ Onboarding successfully completed for {guild.name}.")
        except Exception as e:
            logger.error(f"❌ Error during onboarding for guild {guild.id}: {e}", exc_info=True)

    async def _remove_absent_users(self, guild_id: int, server_members: set[int]) -> None:
        logger.info("🧹 Starting database cleanup for left server members...")
        db_members = await self.db.get_last_verification(guild_id)
        removed = [m for m in db_members if m.user.user_id not in server_members]

        for member in removed:
            await self.db.remove_member(guild_id, member.user.user_id)
            logger.info(f"🗑️ Member {member.nick} ({member.user.user_id}) removed from guild {guild_id}.")

        logger.info(f"✅ Cleanup finished. {len(removed)} member(s) removed.")

    async def _sync_offline_checkins(
        self, guild: discord.Guild, channel: discord.TextChannel, server_members: set[int], guild_data
    ) -> None:
        logger.info("🔎 Scanning text history for missed '!ponto' commands...")
        tz = ZoneInfo(guild_data.timezone)
        since_when = await self.db.get_last_verification(guild.id) or (datetime.now(tz) - timedelta(days=7))

        new_records = 0
        report_details = []

        async for msg in channel.history(after=since_when, limit=300, oldest_first=True):
            if msg.author.bot or msg.content.strip().lower() != "!ponto" or msg.author.id not in server_members:
                continue

            member = await self.db.ensure_member(
                guild.id, msg.author.id, msg.author.name, msg.author.display_name, msg.created_at.date()
            )
            if await self.db.register_attendance(member, msg.created_at):
                new_records += 1
                formatted_time = msg.created_at.astimezone(tz).strftime("%d/%m/%Y at %H:%M:%S")
                report_details.append(f"⏰ {msg.author.mention} (`{msg.author.display_name}`) — {formatted_time}")

        if new_records > 0:
            report_embed = discord.Embed(
                title="📥 Offline Synchronization Report",
                description="I noticed some team members checked in while I was unavailable:",
                color=self.embed_colors["info"],
                timestamp=datetime.now(tz),
            ).add_field(
                name=f"📋 Recovered Records ({new_records})",
                value=self._truncate_text("\n".join(report_details)),
                inline=False,
            )
            try:
                await channel.send(embed=report_embed)
            except discord.Forbidden:
                logger.error("❌ Insufficient permissions to dispatch offline reports to the tracking channel.")

        await self.db.set_last_verification(guild.id, datetime.now(tz))
        logger.info(f"✅ Sync finalized: {new_records} skipped records recovered.")

    # -------------------------- Commands --------------------------

    @commands.command(name="checkin")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def checkin(self, ctx: commands.Context) -> None:
        """Text alternative method to record presence parameters."""
        guild_data = await self.db.get_guild(ctx.guild.id)
        if not guild_data:
            return await ctx.message.reply("⚠️ This server has not been configured yet.", delete_after=10)

        if ctx.channel.id != guild_data.clock_channel_id:
            embed = self._create_base_embed(
                "⛔ Incorrect Channel",
                "This command can only be used in the dedicated attendance tracking channel.",
                "error",
            )
            return await ctx.message.reply(embed=embed, delete_after=10)

        tz = ZoneInfo(guild_data.timezone)
        now = datetime.now(tz)

        member = await self.db.ensure_member(
            ctx.guild.id, ctx.author.id, ctx.author.name, ctx.author.display_name, ctx.message.created_at.date()
        )
        if not await self.db.register_attendance(member, now):
            embed = self._create_base_embed(
                "⚠️ Duplicate Record", f"Hello {ctx.author.mention}, you have already checked in today!", "warning"
            )
            return await ctx.message.reply(embed=embed, delete_after=10)

        await self.db.set_last_verification(ctx.guild.id, now)

        success_embed = discord.Embed(
            title="✅ Attendance Confirmed!", color=self.embed_colors["success"], timestamp=now
        )
        success_embed.set_thumbnail(url=ctx.author.display_avatar.url)
        success_embed.set_footer(text="Electronic Attendance Tracking")

        fields = [
            ("👤 Team Member", ctx.author.mention),
            ("🏷️ Nickname", ctx.author.display_name),
            ("📅 Date", now.strftime("%d/%m/%Y")),
            ("⏰ Time", now.strftime("%H:%M:%S")),
        ]
        for name, value in fields:
            success_embed.add_field(name=name, value=value, inline=True)

        await ctx.message.reply(embed=success_embed)

    async def period_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Provides dynamic suggestions for the period argument."""
        options = [
            app_commands.Choice(name="All (Full History)", value="all"),
            app_commands.Choice(name="Today", value="today"),
            app_commands.Choice(name="Last 7 days", value="7days"),
            app_commands.Choice(name="Last 30 days", value="30days"),
        ]
        return [op for op in options if current.lower() in op.name.lower() or current.lower() in op.value.lower()][:25]

    @app_commands.command(
        name="attendance",
        description="View attendance records and reports filtered by user, period, or global overview.",
    )
    @app_commands.describe(
        user="Select a specific user (Optional).",
        period="Choose a period from the list or type a specific date formatted as DD/MM/YYYY.",
    )
    @app_commands.autocomplete(period=period_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def attendance(
        self, interaction: discord.Interaction, user: discord.Member | None = None, period: str = "all"
    ) -> None:
        """Slash command processor for tracking analytics outputs."""
        guild_data = await self.db.get_guild(interaction.guild.id)
        if not guild_data:
            return await interaction.response.send_message("⚠️ This server has not been configured yet.", ephemeral=True)

        if not await self.bot.has_access(interaction.user, interaction.guild) and interaction.user != user:
            desc = f"You need the `{guild_data.master_role_name}` role to view other members' attendance."
            return await self._send_error_embed(interaction, "⛔ Permission Denied", desc)

        tz = ZoneInfo(guild_data.timezone)

        if period in ["all", "today", "7days", "30days"]:
            label_period = self.labels[period]
            target_dates = self._filter_dates_by_period(period, tz)
        else:
            validated_date = self._parse_custom_date(period)
            if not validated_date:
                desc = "Please use the standard date format: **DD/MM/YYYY**.\n*Example: 23/06/2026*"
                return await self._send_error_embed(interaction, "❌ Invalid Date Format", desc)

            if validated_date > datetime.now(tz).date():
                return await self._send_error_embed(
                    interaction,
                    "⏳ Future Date",
                    "You cannot look up attendance statistics for future dates.",
                    "warning",
                )

            period = "custom"
            label_period = f"Specific Day ({validated_date.strftime('%d/%m/%Y')})"
            target_dates = [validated_date]

        if user is None:
            await self._process_general_report(interaction, label_period, period, target_dates, guild_data)
        else:
            await self._process_individual_report(interaction, user, label_period, period, target_dates)

    async def _process_general_report(
        self, interaction: discord.Interaction, label: str, period: str, dates: list[date], guild_data
    ) -> None:
        """Internal processor for general global logs output."""
        all_members = await self.db.get_guild_members(interaction.guild.id)

        # If it's 'all', fetch all distinct days from the DB. Otherwise, use the calendar 'dates' list.
        if period == "all":
            days_to_check = await self.db.get_day_attendance(interaction.guild.id, period, dates)
        else:
            days_to_check = dates

        embed = self._create_base_embed(
            "📋 General Attendance Report",
            f"🗓️ **Filter:** {label}\n*Displaying attendance status organized by day.*",
            "info",
        )
        special_role_name = guild_data.special_role_name if guild_data else None

        if not all_members or not days_to_check:
            embed.description += "\n\n*No logs or eligible users found for this period.*"
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        guild = interaction.guild
        for day in sorted(days_to_check, reverse=True):
            present, absent = [], []
            # Get check-ins for this specific day (returns a dict of {user_id: time_str})
            day_attendance = await self.db.get_day_attendance(interaction.guild.id, day)

            for member_db in all_members:
                uid = member_db.user.user_id
                nick = member_db.nick or member_db.user.username
                discord_member = guild.get_member(uid) if guild else None

                # Ensure we are comparing date to date to prevent TypeErrors
                registration_date = (
                    member_db.registered_at
                    if isinstance(member_db.registered_at, date)
                    else member_db.registered_at.date()
                )

                if (
                    discord_member
                    and special_role_name
                    and any(role.name == special_role_name for role in discord_member.roles)
                ):
                    present.append(f"✅ **{nick}** (`Exempt/Special`)")
                elif uid in day_attendance:
                    present.append(f"✅ **{nick}** (`{day_attendance[uid].strftime('%H:%M')}`)")
                elif day >= registration_date:
                    # Now it safely catches absences for any day after their registration
                    absent.append(f"❌ {nick}")

            present_text = "\n".join(present) if present else "*No one checked in*"
            absent_text = "\n".join(absent) if absent else "*No absences*"
            field_value = f"**Present:**\n{present_text}\n\n**Absent:**\n{absent_text}\n"

            embed.add_field(
                name=f"📅 Date: {day.strftime('%m/%d/%Y')}", value=self._truncate_text(field_value), inline=False
            )

        await interaction.response.send_message(embed=embed)

    async def _process_individual_report(
        self, interaction: discord.Interaction, user: discord.Member, label: str, period: str, dates: list[date]
    ) -> None:
        """Internal processor for single target user performance profiles."""
        total_days, checkins = await self.db.get_user_statistics(interaction.guild.id, user.id, period, dates)
        absences = max(0, total_days - checkins)
        rate = (checkins / total_days * 100) if total_days else 0.0

        embed = self._create_base_embed(
            "📊 Detailed Attendance Statistics", f"👤 **User:** {user.mention}\n🗓️ **Window:** {label}", "info"
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="✅ Days Present", value=f"`{checkins} days`", inline=True)
        embed.add_field(name="❌ Days Absent", value=f"`{absences} days`", inline=True)
        embed.add_field(name="📈 Attendance Rate", value=f"`{rate:.1f}% presence`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ranking", description="Displays the global attendance leaderboard.")
    async def ranking(self, interaction: discord.Interaction) -> None:
        leaderboard = await self.db.get_ranking(interaction.guild.id)
        embed = self._create_base_embed(
            "🏆 Honor Roll — Attendance Ranking", "List of the most engaged team members checking in.", "success"
        )

        podium_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        ranking_lines = [
            f"{podium_emojis.get(pos, '🔹')} `{pos:02d}#` **{nick}** — `{qty} check-ins`"
            for pos, (nick, qty) in enumerate(leaderboard, start=1)
        ]
        ranking_text = "\n".join(ranking_lines) if ranking_lines else "*No data recorded yet.*"

        embed.add_field(name="Leaderboard Placement", value=self._truncate_text(ranking_text), inline=False)
        embed.set_footer(text="Updated in real-time")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: "PontoBot"):
    await bot.add_cog(Attendance(bot))
