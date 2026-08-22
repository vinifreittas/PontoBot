# cogs/attendance/helpers.py
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import discord

from pontobot.i18n import resolve_lang, t
from pontobot.utils.embeds import create_base_embed, truncate_text

from .views import DAYS_PER_PAGE, PaginationView

logger = logging.getLogger(__name__)

PERIOD_DAYS: dict[str, int] = {"today": 1, "7days": 7, "30days": 30}


def get_period_label(period: str, lang: str = "en", date_str: str | None = None) -> str:
    """Returns localized string label for date filter period."""
    if period == "custom" and date_str:
        return t("periods.custom", lang=lang, date=date_str)
    return t(f"periods.{period}", lang=lang)


def filter_dates_by_period(period: str, tz: ZoneInfo) -> list[date]:
    """Calculates a list of targeted dates based on the defined period window."""
    if period not in PERIOD_DAYS:
        return []
    today_dt = datetime.now(tz)
    return [(today_dt - timedelta(days=i)).date() for i in range(PERIOD_DAYS[period])]


def parse_custom_date(date_str: str) -> date | None:
    """Validates and parses a custom date string into a date object."""
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


async def post_offline_recovery_routine(bot, guild: discord.Guild, guild_data) -> None:
    """Routine for legacy servers: handles time elapsed while the bot was offline."""
    channel = bot.get_channel(guild_data.clock_channel_id)
    if not isinstance(channel, discord.TextChannel):
        return

    server_members: set[int] = {member.id for member in guild.members}
    try:
        await remove_absent_users(bot.db, guild.id, server_members)
        await sync_offline_checkins(bot, guild, channel, server_members, guild_data)
    except Exception as e:
        logger.exception("❌ Error during recovery for guild %s: %s", guild.id, e)


async def first_time_guild_onboarding(db, guild: discord.Guild, guild_data) -> None:
    """Routine for new servers: populates the database from scratch without error reports."""
    try:
        logger.info("📥 Populating initial database records for guild: %s", guild.name)
        tz = ZoneInfo(guild_data.timezone)
        await db.set_last_verification(guild.id, datetime.now(tz))
        logger.info("✅ Onboarding successfully completed for %s.", guild.name)
    except Exception as e:
        logger.exception("❌ Error during onboarding for guild %s: %s", guild.id, e)


async def remove_absent_users(db, guild_id: int, server_members: set[int]) -> None:
    logger.info("🧹 Starting database cleanup for left server members...")
    db_members = await db.get_guild_members(guild_id)
    removed = [m for m in db_members if m.user.user_id not in server_members]

    for member in removed:
        await db.remove_member(guild_id, member.user.user_id)
        logger.info("🗑️ Member %s (%s) removed from guild %s.", member.nick, member.user.user_id, guild_id)

    logger.info("✅ Cleanup finished. %d member(s) removed.", len(removed))


async def sync_offline_checkins(
    bot, guild: discord.Guild, channel: discord.TextChannel, server_members: set[int], guild_data
) -> None:
    logger.info("🔎 Scanning text history for missed '!ponto' commands...")
    tz = ZoneInfo(guild_data.timezone)
    lang = guild_data.language
    since_when = await bot.db.get_last_verification(guild.id) or (datetime.now(tz) - timedelta(days=7))

    new_records = 0
    report_details = []

    async for msg in channel.history(after=since_when, limit=300, oldest_first=True):
        if msg.author.bot or msg.content.strip().lower() != "!ponto" or msg.author.id not in server_members:
            continue

        member = await bot.db.ensure_member(
            guild.id, msg.author.id, msg.author.name, msg.author.display_name, msg.created_at.date()
        )
        if await bot.db.register_attendance(member, msg.created_at):
            new_records += 1
            date_str = msg.created_at.astimezone(tz).strftime("%d/%m/%Y")
            time_str = msg.created_at.astimezone(tz).strftime("%H:%M:%S")
            formatted_time = t("offline_sync.time_format", lang=lang, date=date_str, time=time_str)
            report_details.append(f"⏰ {msg.author.mention} (`{msg.author.display_name}`) — {formatted_time}")

    if new_records > 0:
        report_embed = discord.Embed(
            title=t("offline_sync.title", lang=lang),
            description=t("offline_sync.description", lang=lang),
            color=bot.embed_colors["info"],
            timestamp=datetime.now(tz),
        ).add_field(
            name=t("offline_sync.field_recovered", lang=lang, count=new_records),
            value=truncate_text("\n".join(report_details)),
            inline=False,
        )
        try:
            await channel.send(embed=report_embed)
        except discord.Forbidden:
            logger.error("❌ Insufficient permissions to dispatch offline reports to the tracking channel.")

    await bot.db.set_last_verification(guild.id, datetime.now(tz))
    logger.info("✅ Sync finalized: %d skipped records recovered.", new_records)


async def process_general_report(
    cog, interaction: discord.Interaction, label: str, period: str, dates: list[date], guild_data
) -> None:
    """Internal processor for general global logs output."""
    lang = resolve_lang(
        locale=interaction.locale, guild_lang=guild_data.language if guild_data else None, ephemeral=False
    )
    all_members = await cog.db.get_guild_members(interaction.guild.id)

    if period == "all":
        days_to_check = await cog.db.get_days_with_clock_in(interaction.guild.id, period, dates)
    else:
        days_to_check = dates

    special_role_id = guild_data.special_role_id if guild_data else None

    if not all_members or not days_to_check:
        embed = create_base_embed(
            cog.embed_colors,
            t("attendance.general_report_title", lang=lang),
            t("attendance.general_report_empty", lang=lang, filter=label),
            "info",
        )
        return await interaction.followup.send(embed=embed, ephemeral=False)

    batch_target = list(days_to_check) if period != "all" else None
    all_attendance = await cog.db.get_attendance_for_period(interaction.guild.id, batch_target)

    sorted_days = sorted(days_to_check, reverse=True)
    day_chunks = [sorted_days[i : i + DAYS_PER_PAGE] for i in range(0, len(sorted_days), DAYS_PER_PAGE)]
    total_pages = len(day_chunks)

    guild = interaction.guild
    pages: list[discord.Embed] = []

    for page_idx, chunk in enumerate(day_chunks, start=1):
        embed = create_base_embed(
            cog.embed_colors,
            t("attendance.general_report_title", lang=lang),
            t("attendance.general_report_filter", lang=lang, filter=label),
            "info",
        )
        for day in chunk:
            present, absent = [], []
            day_attendance = all_attendance.get(day, {})

            for member_db in all_members:
                uid = member_db.user.user_id
                nick = member_db.nick or member_db.user.username
                discord_member = guild.get_member(uid) if guild else None

                registration_date = (
                    member_db.registered_at
                    if isinstance(member_db.registered_at, date)
                    else member_db.registered_at.date()
                )

                if (
                    discord_member
                    and special_role_id
                    and any(role.id == special_role_id for role in discord_member.roles)
                ):
                    present.append(f"✅ **{nick}** (`{t('attendance.exempt_special', lang=lang)}`)")
                elif uid in day_attendance:
                    present.append(f"✅ **{nick}** (`{day_attendance[uid].strftime('%H:%M')}`)")
                elif day >= registration_date:
                    absent.append(f"❌ {nick}")

            present_text = "\n".join(present) if present else t("attendance.no_checkins", lang=lang)
            absent_text = "\n".join(absent) if absent else t("attendance.no_absences", lang=lang)
            field_value = (
                f"{t('attendance.present_header', lang=lang)}\n{present_text}\n\n"
                f"{t('attendance.absent_header', lang=lang)}\n{absent_text}\n"
            )

            date_field_title = t("attendance.field_date_title", lang=lang, date=day.strftime("%d/%m/%Y"))
            embed.add_field(name=date_field_title, value=truncate_text(field_value), inline=False)

        embed.set_footer(text=t("attendance.page_footer", lang=lang, current=page_idx, total=total_pages))
        pages.append(embed)

    if total_pages > 1:
        view = PaginationView(pages, owner_id=interaction.user.id)
        await interaction.followup.send(embed=pages[0], view=view)
    else:
        await interaction.followup.send(embed=pages[0])


async def process_individual_report(
    cog, interaction: discord.Interaction, user: discord.Member, label: str, period: str, dates: list[date]
) -> None:
    """Internal processor for single target user performance profiles."""
    lang = resolve_lang(locale=interaction.locale, ephemeral=True)
    total_days, checkins = await cog.db.get_user_statistics(interaction.guild.id, user.id, period, dates)
    absences = max(0, total_days - checkins)
    rate = (checkins / total_days * 100) if total_days else 0.0

    embed = create_base_embed(
        cog.embed_colors,
        t("attendance.user_report_title", lang=lang),
        t("attendance.user_report_header", lang=lang, user=user.mention, filter=label),
        "info",
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(
        name=t("attendance.days_present", lang=lang),
        value=f"`{checkins} {t('attendance.days_suffix', lang=lang)}`",
        inline=True,
    )
    embed.add_field(
        name=t("attendance.days_absent", lang=lang),
        value=f"`{absences} {t('attendance.days_suffix', lang=lang)}`",
        inline=True,
    )
    embed.add_field(
        name=t("attendance.attendance_rate", lang=lang),
        value=f"`{rate:.1f}% {t('attendance.presence_suffix', lang=lang)}`",
        inline=False,
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
