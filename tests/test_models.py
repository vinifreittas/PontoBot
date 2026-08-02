from datetime import date, datetime

from pontobot.database.models import Guild, Member, Metadata, User


class TestModels:
    async def test_guild_creation(self):
        guild = await Guild.create(
            guild_id=1,
            master_role_id=101,
            special_role_id=102,
            clock_channel_id=10,
            timezone="America/Sao_Paulo",
            language="pt-br",
        )
        assert guild.guild_id == 1
        assert guild.master_role_id == 101
        assert guild.special_role_id == 102
        assert guild.language == "pt-br"

    async def test_user_member_relationship(self):
        guild = await Guild.create(
            guild_id=1,
            master_role_id=101,
            special_role_id=102,
            clock_channel_id=10,
            timezone="UTC",
            language="en",
        )
        user = await User.create(user_id=100, username="test_user")
        member = await Member.create(user=user, guild=guild, nick="Nick", registered_at=date.today())

        assert member.user_id == user.user_id
        assert member.guild_id == guild.guild_id

    async def test_metadata_storage(self):
        guild = await Guild.create(
            guild_id=1,
            master_role_id=101,
            special_role_id=102,
            clock_channel_id=10,
            timezone="UTC",
            language="en",
        )
        now = datetime.now()
        meta = await Metadata.create(guild=guild, key="last_verification", value=now)
        assert meta.key == "last_verification"
        assert meta.value == now

    async def test_safe_datetime_field_returns_datetime(self):
        """SafeDateTimeField must return proper datetime objects and support datetime operations."""
        from pontobot.database.models import Attendance

        guild = await Guild.create(
            guild_id=10,
            master_role_id=101,
            special_role_id=102,
            clock_channel_id=1,
            timezone="UTC",
            language="en",
        )
        user = await User.create(user_id=1, username="test")
        member = await Member.create(user=user, guild=guild, nick="test", registered_at=date.today())
        now = datetime.now()
        att = await Attendance.create(member=member, date=now.date(), checked_in_at=now)

        att_from_db = await Attendance.get(id=att.id)
        assert isinstance(att_from_db.checked_in_at, datetime)
