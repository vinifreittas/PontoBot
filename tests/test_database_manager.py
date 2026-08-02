from datetime import date, datetime

from pontobot.database.manager import DatabaseManager, get_tortoise_config


class TestConfig:
    def test_get_tortoise_config_defaults(self):
        config = get_tortoise_config()
        assert config["connections"]["default"] == "sqlite://db.sqlite3"

    def test_get_tortoise_config_with_custom_path(self):
        config = get_tortoise_config("test.db")
        assert config["connections"]["default"] == "sqlite://test.db"

    def test_get_tortoise_config_memory(self):
        config = get_tortoise_config(":memory:")
        assert config["connections"]["default"] == "sqlite://:memory:"


class TestGuildManagement:
    async def test_add_and_get_guild(self):
        db = DatabaseManager(":memory:")
        await db.add_guild(123, 101, 102, 456, "America/Sao_Paulo", "pt-br")
        guild = await db.get_guild(123)
        assert guild is not None
        assert guild.guild_id == 123
        assert guild.master_role_id == 101
        assert guild.special_role_id == 102
        assert guild.timezone == "America/Sao_Paulo"

    async def test_reconfigure_existing_guild(self):
        db = DatabaseManager(":memory:")
        await db.add_guild(123, 101, 102, 456, "America/Sao_Paulo", "pt-br")
        # Reconfigure with new roles, channel, timezone, language
        await db.add_guild(123, 999, 888, 777, "Europe/London", "en")
        guild = await db.get_guild(123)
        assert guild is not None
        assert guild.master_role_id == 999
        assert guild.special_role_id == 888
        assert guild.clock_channel_id == 777
        assert guild.timezone == "Europe/London"
        assert guild.language == "en"

    async def test_get_nonexistent_guild_returns_none(self):
        db = DatabaseManager(":memory:")
        assert await db.get_guild(999) is None


class TestMemberManagement:
    async def test_ensure_member_creates_user_and_member(self):
        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        member = await db.ensure_member(1, 42, "testuser", "TestNick", date.today())
        assert member is not None
        assert member.nick == "TestNick"

    async def test_get_guild_members(self):
        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        await db.ensure_member(1, 42, "user1", "Nick1", date.today())
        await db.ensure_member(1, 43, "user2", "Nick2", date.today())

        members = await db.get_guild_members(1)
        assert len(members) == 2
        uids = {m.user.user_id for m in members}
        assert uids == {42, 43}

    async def test_ensure_member_updates_username_on_change(self):
        """Regression: ensure username changes don't create duplicate users."""
        from pontobot.database.models import User

        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        await db.ensure_member(1, 42, "old_name", "Nick1", date.today())
        await db.ensure_member(1, 42, "new_name", "Nick2", date.today())

        assert await User.all().count() == 1
        user = await User.get(user_id=42)
        assert user.username == "new_name"

        member = await db.get_member(1, 42)
        assert member.nick == "Nick2"


class TestAttendance:
    async def test_register_attendance_prevents_duplicates(self):
        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        member = await db.ensure_member(1, 42, "user", "Nick", date.today())
        now = datetime.now()
        assert await db.register_attendance(member, now) is True
        assert await db.register_attendance(member, now) is False


class TestGetAttendanceForPeriod:
    """Tests for get_attendance_for_period() — the N+1 fix for general reports."""

    async def test_returns_empty_dict_when_no_records(self):
        """Should return an empty dict when no attendance has been recorded."""
        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        result = await db.get_attendance_for_period(1)
        assert result == {}

    async def test_returns_all_records_without_filter(self):
        """Without target_dates, all historical records for the guild are returned."""
        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        member = await db.ensure_member(1, 42, "user", "Nick", date.today())

        day1 = datetime(2026, 6, 1, 9, 0)
        day2 = datetime(2026, 6, 2, 9, 0)
        await db.register_attendance(member, day1)
        await db.register_attendance(member, day2)

        result = await db.get_attendance_for_period(1)

        assert len(result) == 2
        assert day1.date() in result
        assert day2.date() in result
        assert result[day1.date()][42] == day1
        assert result[day2.date()][42] == day2

    async def test_filters_by_target_dates(self):
        """When target_dates is provided, only those dates are included in the result."""
        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        member = await db.ensure_member(1, 42, "user", "Nick", date.today())

        day1 = datetime(2026, 6, 1, 9, 0)
        day2 = datetime(2026, 6, 2, 9, 0)
        day3 = datetime(2026, 6, 3, 9, 0)
        await db.register_attendance(member, day1)
        await db.register_attendance(member, day2)
        await db.register_attendance(member, day3)

        # Only request records for day1 and day3 — day2 must be excluded
        result = await db.get_attendance_for_period(1, target_dates=[day1.date(), day3.date()])

        assert len(result) == 2
        assert day1.date() in result
        assert day3.date() in result
        assert day2.date() not in result

    async def test_groups_multiple_users_on_same_day(self):
        """Multiple users checking in on the same day should all appear under that date key."""
        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        member_a = await db.ensure_member(1, 10, "alice", "Alice", date.today())
        member_b = await db.ensure_member(1, 20, "bob", "Bob", date.today())

        checkin_time_a = datetime(2026, 7, 15, 8, 30)
        checkin_time_b = datetime(2026, 7, 15, 9, 45)
        await db.register_attendance(member_a, checkin_time_a)
        await db.register_attendance(member_b, checkin_time_b)

        result = await db.get_attendance_for_period(1)

        assert len(result) == 1
        day_map = result[checkin_time_a.date()]
        assert day_map[10] == checkin_time_a
        assert day_map[20] == checkin_time_b

    async def test_isolated_to_guild(self):
        """Records from a different guild must not leak into the result."""
        db = DatabaseManager(":memory:")
        await db.add_guild(1, 101, 102, 100, "UTC", "en")
        await db.add_guild(2, 201, 202, 200, "UTC", "en")

        member_g1 = await db.ensure_member(1, 10, "alice", "Alice", date.today())
        member_g2 = await db.ensure_member(2, 20, "bob", "Bob", date.today())

        await db.register_attendance(member_g1, datetime(2026, 7, 1, 9, 0))
        await db.register_attendance(member_g2, datetime(2026, 7, 1, 10, 0))

        result_g1 = await db.get_attendance_for_period(1)

        assert len(result_g1) == 1
        day_map = result_g1[date(2026, 7, 1)]
        assert 10 in day_map
        assert 20 not in day_map
