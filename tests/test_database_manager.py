from datetime import UTC, date, datetime

import pytest

from pontobot.database.manager import DatabaseManager

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db():
    instance = DatabaseManager(":memory:")
    await instance.add_guild(1, 101, 102, 100, "UTC", "en")
    return instance


@pytest.fixture
async def member(db):
    return await db.ensure_member(1, 42, "user", "Nick", date.today())


# ---------------------------------------------------------------------------
# SafeDateTimeField — DB round-trip (pure unit tests are in test_models.py)
# ---------------------------------------------------------------------------


async def test_safe_datetime_field_round_trip_from_database():
    """SafeDateTimeField must survive a full write → read cycle via SQLite."""
    from pontobot.database.models import Attendance, Guild, Member, User

    await Guild.create(
        guild_id=99, master_role_id=1, special_role_id=2, clock_channel_id=3, timezone="UTC", language="en"
    )
    user = await User.create(user_id=1, username="test")
    m = await Member.create(user=user, guild_id=99, nick="test", registered_at=date.today())
    now = datetime.now(UTC)
    att = await Attendance.create(member=m, date=now.date(), checked_in_at=now)
    att_from_db = await Attendance.get(id=att.id)
    assert isinstance(att_from_db.checked_in_at, datetime)


# ---------------------------------------------------------------------------
# Guild management
# ---------------------------------------------------------------------------


class TestGuildManagement:
    async def test_add_and_get_guild(self):
        inst = DatabaseManager(":memory:")
        await inst.add_guild(123, 101, 102, 456, "America/Sao_Paulo", "pt-br")
        guild = await inst.get_guild(123)
        assert guild is not None and guild.guild_id == 123
        assert guild.master_role_id == 101 and guild.timezone == "America/Sao_Paulo"

    async def test_reconfigure_existing_guild(self):
        inst = DatabaseManager(":memory:")
        await inst.add_guild(123, 101, 102, 456, "America/Sao_Paulo", "pt-br")
        await inst.add_guild(123, 999, 888, 777, "Europe/London", "en")
        guild = await inst.get_guild(123)
        assert guild.master_role_id == 999 and guild.clock_channel_id == 777
        assert guild.timezone == "Europe/London" and guild.language == "en"

    async def test_get_nonexistent_guild_returns_none(self):
        assert await DatabaseManager(":memory:").get_guild(999) is None


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------


class TestMemberManagement:
    async def test_ensure_member_creates_user_and_member(self, db):
        m = await db.ensure_member(1, 99, "testuser", "TestNick", date.today())
        assert m is not None and m.nick == "TestNick"

    async def test_get_guild_members(self, db):
        await db.ensure_member(1, 10, "user1", "Nick1", date.today())
        await db.ensure_member(1, 11, "user2", "Nick2", date.today())
        members = await db.get_guild_members(1)
        assert {m.user.user_id for m in members} == {10, 11}

    async def test_ensure_member_updates_username_on_change(self, db):
        """Regression: username change must not create a duplicate User row."""
        from pontobot.database.models import User

        await db.ensure_member(1, 42, "old_name", "Nick1", date.today())
        await db.ensure_member(1, 42, "new_name", "Nick2", date.today())
        assert await User.all().count() == 1
        assert (await User.get(user_id=42)).username == "new_name"
        assert (await db.get_member(1, 42)).nick == "Nick2"


# ---------------------------------------------------------------------------
# Attendance — registration & duplicate prevention
# ---------------------------------------------------------------------------


async def test_register_attendance_prevents_duplicates(db, member):
    now = datetime.now(UTC)
    assert await db.register_attendance(member, now) is True
    assert await db.register_attendance(member, now) is False


# ---------------------------------------------------------------------------
# get_attendance_for_period — bulk fetch (avoids N+1 in reports)
# ---------------------------------------------------------------------------


class TestGetAttendanceForPeriod:
    async def test_returns_empty_dict_when_no_records(self, db):
        assert await db.get_attendance_for_period(1) == {}

    async def test_returns_all_records_without_filter(self, db, member):
        day1 = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        day2 = datetime(2026, 6, 2, 9, 0, tzinfo=UTC)
        await db.register_attendance(member, day1)
        await db.register_attendance(member, day2)
        result = await db.get_attendance_for_period(1)
        assert len(result) == 2
        assert result[day1.date()][42] == day1 and result[day2.date()][42] == day2

    async def test_filters_by_target_dates(self, db, member):
        day1 = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        day2 = datetime(2026, 6, 2, 9, 0, tzinfo=UTC)
        day3 = datetime(2026, 6, 3, 9, 0, tzinfo=UTC)
        for d in (day1, day2, day3):
            await db.register_attendance(member, d)
        result = await db.get_attendance_for_period(1, target_dates=[day1.date(), day3.date()])
        assert len(result) == 2 and day2.date() not in result

    async def test_groups_multiple_users_on_same_day(self, db):
        ma = await db.ensure_member(1, 10, "alice", "Alice", date.today())
        mb = await db.ensure_member(1, 20, "bob", "Bob", date.today())
        t_a, t_b = datetime(2026, 7, 15, 8, 30, tzinfo=UTC), datetime(2026, 7, 15, 9, 45, tzinfo=UTC)
        await db.register_attendance(ma, t_a)
        await db.register_attendance(mb, t_b)
        day_map = (await db.get_attendance_for_period(1))[t_a.date()]
        assert day_map[10] == t_a and day_map[20] == t_b

    async def test_isolated_to_guild(self, db):
        """Records from another guild must not leak into the result."""
        await db.add_guild(2, 201, 202, 200, "UTC", "en")
        m1 = await db.ensure_member(1, 10, "alice", "Alice", date.today())
        m2 = await db.ensure_member(2, 20, "bob", "Bob", date.today())
        await db.register_attendance(m1, datetime(2026, 7, 1, 9, 0, tzinfo=UTC))
        await db.register_attendance(m2, datetime(2026, 7, 1, 10, 0, tzinfo=UTC))
        day_map = (await db.get_attendance_for_period(1))[date(2026, 7, 1)]
        assert 10 in day_map and 20 not in day_map


# ---------------------------------------------------------------------------
# get_user_statistics
# ---------------------------------------------------------------------------


class TestUserStatistics:
    async def test_returns_zeros_for_nonexistent_member(self, db):
        assert await db.get_user_statistics(1, 999, "all", []) == (0, 0)

    async def test_counts_match_registered_attendances(self, db):
        m = await db.ensure_member(1, 42, "user", "Nick", date(2026, 5, 1))
        day1 = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        day2 = datetime(2026, 6, 2, 9, 0, tzinfo=UTC)
        await db.register_attendance(m, day1)
        await db.register_attendance(m, day2)
        assert await db.get_user_statistics(1, 42, "all", []) == (2, 2)

    async def test_filters_by_target_dates(self, db):
        m = await db.ensure_member(1, 42, "user", "Nick", date(2026, 6, 1))
        day1 = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        day2 = datetime(2026, 6, 2, 9, 0, tzinfo=UTC)
        await db.register_attendance(m, day1)
        await db.register_attendance(m, day2)
        total, attended = await db.get_user_statistics(1, 42, "monthly", [day1.date()])
        assert total == 1 and attended == 1


# ---------------------------------------------------------------------------
# get_ranking
# ---------------------------------------------------------------------------


class TestRanking:
    async def test_ranking_ordered_by_attendance_desc(self, db):
        alice = await db.ensure_member(1, 10, "alice", "Alice", date.today())
        bob = await db.ensure_member(1, 20, "bob", "Bob", date.today())
        await db.register_attendance(alice, datetime(2026, 6, 1, 9, 0, tzinfo=UTC))
        await db.register_attendance(alice, datetime(2026, 6, 2, 9, 0, tzinfo=UTC))
        await db.register_attendance(bob, datetime(2026, 6, 1, 10, 0, tzinfo=UTC))
        ranking = await db.get_ranking(1)
        assert ranking[0] == ("Alice", 2) and ranking[1] == ("Bob", 1)

    async def test_empty_guild_returns_empty_ranking(self, db):
        assert await db.get_ranking(1) == []


# ---------------------------------------------------------------------------
# Metadata — last verification
# ---------------------------------------------------------------------------


class TestLastVerification:
    async def test_get_returns_none_when_not_set(self, db):
        assert await db.get_last_verification(1) is None

    async def test_set_and_get_round_trip(self, db):
        now = datetime.now(UTC)
        await db.set_last_verification(1, now)
        assert isinstance(await db.get_last_verification(1), datetime)

    async def test_set_is_idempotent(self, db):
        """Calling set_last_verification twice must update, not duplicate."""
        from pontobot.database.models import Metadata

        await db.set_last_verification(1, datetime(2026, 6, 1, 12, 0, tzinfo=UTC))
        await db.set_last_verification(1, datetime(2026, 7, 1, 12, 0, tzinfo=UTC))
        assert await Metadata.filter(guild_id=1, key="last_verification").count() == 1
