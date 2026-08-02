# database/manager.py
import logging
import os
from datetime import date, datetime, time
from pathlib import Path

from aerich import Command
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from tortoise.expressions import Q
from tortoise.functions import Count

from pontobot.database.models import Attendance, Guild, Member, Metadata, User

logger = logging.getLogger(__name__)


def get_tortoise_config(db_url: str | None = None) -> dict:
    """Builds Tortoise ORM configuration dictionary. Used by both runtime and Aerich CLI."""
    if not db_url:
        db_url = os.environ.get("DATABASE_URL", "sqlite://db.sqlite3")
    elif db_url == ":memory:":
        db_url = "sqlite://:memory:"
    elif not db_url.startswith("sqlite://"):
        db_url = f"sqlite://{db_url}"

    return {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["aerich.models", "pontobot.database.models"],
                "default_connection": "default",
            }
        },
    }


# Aerich reads this module-level constant
TORTOISE_ORM = get_tortoise_config()


class DatabaseManager:
    """Acts as a Data Access Layer (DAL) API for the rest of the application."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.config = get_tortoise_config(db_url=db_path)

    async def connect(self) -> None:
        """Initializes Tortoise ORM with centralized configurations."""
        try:
            await Tortoise.init(config=self.config)

            package_dir = Path(__file__).parent.resolve()
            migrations_path = str(package_dir / "migrations")

            command = Command(
                tortoise_config=self.config,
                app="models",
                location=migrations_path,
            )
            await command.init()

            try:
                await command.upgrade(run_in_transaction=True)
                logger.info("✅ Aerich upgraded or created the database with success.")
            except Exception as upgrade_err:
                logger.error("❌ Aerich failed to upgrade or create the database: %s", upgrade_err)
                raise

            logger.info("💾 Database connection via Tortoise ORM established.")
        except Exception as e:
            logger.error("❌ Structural error connecting to database: %s", e)
            raise

    async def disconnect(self) -> None:
        """Safely closes all open database connections."""
        try:
            await Tortoise.close_connections()
            logger.info("💾 Database connections closed.")
        except Exception as e:
            logger.warning("⚠️ Error closing database connections: %s", e)

    # ------- GUILD MANAGEMENT -------

    async def get_guild(self, guild_id: int) -> Guild | None:
        """Retrieves a specific guild from the database."""
        return await Guild.get_or_none(guild_id=guild_id)

    async def add_guild(
        self,
        guild_id: int,
        master_role_id: int,
        special_role_id: int,
        clock_channel_id: int,
        timezone: str,
        language: str,
    ) -> None:
        """Ensures a guild exists in the database, creating or updating it with given settings."""
        await Guild.update_or_create(
            guild_id=guild_id,
            defaults={
                "master_role_id": master_role_id,
                "special_role_id": special_role_id,
                "clock_channel_id": clock_channel_id,
                "timezone": timezone,
                "language": language,
            },
        )

    async def remove_guild(self, guild_id: int) -> None:
        """Removes a guild from the database."""
        await Guild.filter(guild_id=guild_id).delete()

    # ------- MEMBER MANAGEMENT -------

    async def ensure_member(
        self, guild_id: int, user_id: int, username: str, nickname: str, registration_date: date
    ) -> Member:
        """Ensures a user exists, and they are linked as a member."""
        user, _ = await User.update_or_create(
            user_id=user_id,
            defaults={"username": username},
        )

        member, _ = await Member.get_or_create(
            user=user, guild_id=guild_id, defaults={"nick": nickname, "registered_at": registration_date}
        )
        if member.nick != nickname:
            member.nick = nickname
            await member.save(update_fields=["nick"])
        return member

    async def remove_member(self, guild_id: int, user_id: int) -> None:
        """Removes a member relationship when they leave a specific server."""
        await Member.filter(guild_id=guild_id, user_id=user_id).delete()

    async def get_member(self, guild_id: int, user_id: int) -> Member | None:
        """Retrieves a specific member from a server."""
        return await Member.get_or_none(guild_id=guild_id, user_id=user_id)

    async def get_guild_members(self, guild_id: int) -> list[Member]:
        """Retrieves all members of a specific server."""
        return await Member.filter(guild_id=guild_id).prefetch_related("user")

    # ------- ATTENDANCE MANAGEMENT -------

    async def register_attendance(self, member: Member, date_time: datetime) -> bool:
        """Registers a member's daily attendance securely using Time and Date objects."""
        try:
            await Attendance.create(member=member, date=date_time.date(), checked_in_at=date_time)
            return True
        except IntegrityError:
            return False
        except Exception as e:
            logger.error("❌ Error registering attendance: %s", e)
            return False

    async def get_day_attendance(self, guild_id: int, day: date) -> dict[int, time]:
        """Returns a mapping of user IDs to check-in times for a specific guild and date."""
        attendance_records = await Attendance.filter(member__guild_id=guild_id, date=day).prefetch_related(
            "member__user"
        )

        return {a.member.user_id: a.checked_in_at for a in attendance_records}

    async def get_attendance_for_period(
        self, guild_id: int, target_dates: list[date] | None = None
    ) -> dict[date, dict[int, datetime]]:
        """Returns all attendance records for a guild grouped by date in a single query.

        Solves the N+1 problem in ``_process_general_report`` by fetching all rows
        up-front instead of issuing one query per day inside the rendering loop.

        Args:
            guild_id: The Discord guild ID to filter attendance records.
            target_dates: Optional list of specific dates to filter. When ``None``,
                all historical records for the guild are returned.

        Returns:
            A nested mapping ``{date: {user_id: checked_in_at}}`` where each key is
            a calendar date and its value is a dict mapping Discord user IDs to their
            check-in timestamp for that day.
        """
        query = Attendance.filter(member__guild_id=guild_id).prefetch_related("member__user")
        if target_dates:
            query = query.filter(date__in=target_dates)

        records = await query.all()

        result: dict[date, dict[int, datetime]] = {}
        for r in records:
            day_map = result.setdefault(r.date, {})
            day_map[r.member.user_id] = r.checked_in_at
        return result

    async def get_days_with_clock_in(self, guild_id: int, period: str, target_dates: list[date]) -> list[date]:
        """Returns all dates where at least one attendance occurred within a specific guild context."""
        base_query = Attendance.filter(member__guild_id=guild_id)

        if period != "all" and target_dates:
            base_query = base_query.filter(date__in=target_dates)

        return await base_query.distinct().values_list("date", flat=True)

    # ------- STATS & METADATA -------

    async def get_user_statistics(
        self, guild_id: int, user_id: int, period: str, target_dates: list[date]
    ) -> tuple[int, int]:
        """Calculates the total expected attendance days versus the specific user's attendance records."""
        member = await Member.get_or_none(guild_id=guild_id, user_id=user_id)
        if not member:
            return 0, 0

        # 1. Determine the total expected days for the requested time window
        if period != "all" and target_dates:
            valid_days = [d for d in target_dates if d >= member.registered_at]
            total_days = len(valid_days)
        else:
            total_days = (
                await Attendance.filter(member__guild_id=guild_id, date__gte=member.registered_at)
                .distinct()
                .values_list("date", flat=True)
            )
            total_days = len(total_days)

        # 2. Total attendances registered by this specific user
        user_filter = Q(member=member)
        if period != "all" and target_dates:
            user_filter &= Q(date__in=target_dates)

        user_total = await Attendance.filter(user_filter).count()

        return total_days, user_total

    async def get_ranking(self, guild_id: int, limit: int = 20) -> list[tuple[str, int]]:
        """Returns top users in a specific guild ranked by attendance count."""
        members_with_attendance = (
            await Member.filter(guild_id=guild_id)
            .annotate(qty=Count("attendances"))
            .order_by("-qty")
            .limit(limit)
            .select_related("user")
        )

        return [(m.nick or m.user.username, m.qty) for m in members_with_attendance]

    async def get_last_verification(self, guild_id: int) -> datetime | None:
        meta = await Metadata.get_or_none(guild_id=guild_id, key="last_verification")
        return meta.value if meta else None

    async def set_last_verification(self, guild_id: int, value: datetime) -> None:
        await Metadata.update_or_create(guild_id=guild_id, key="last_verification", defaults={"value": value})
