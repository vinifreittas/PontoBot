# database/models.py
from datetime import datetime

from dateutil.parser import isoparse
from tortoise import fields
from tortoise.models import Model

# ----------------------------------------------------------------------
# CUSTOM FIELDS
# ----------------------------------------------------------------------


class SafeDateTimeField(fields.TextField):
    """Custom field to safely parse SQLite ISO timestamps into Python datetime objects."""

    def to_python_value(self, value: any) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return isoparse(value.strip())
            except (ValueError, TypeError):
                return None

        return super().to_python_value(value)


# ----------------------------------------------------------------------
# TABLES
# ----------------------------------------------------------------------


class Guild(Model):
    guild_id = fields.BigIntField(pk=True)
    master_role_name = fields.CharField(max_length=255, null=False)
    special_role_name = fields.CharField(max_length=255, null=False)
    clock_channel_id = fields.BigIntField(null=False)
    timezone = fields.CharField(max_length=100, null=False)

    class Meta:
        table = "guilds"


class User(Model):
    user_id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=255, null=False)

    class Meta:
        table = "users"


class Member(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="guild_memberships", on_delete=fields.CASCADE)
    guild = fields.ForeignKeyField("models.Guild", related_name="guild_members", on_delete=fields.CASCADE)

    nick = fields.CharField(max_length=255, null=False)
    registered_at = fields.DateField(auto_now_add=False)

    class Meta:
        table = "members"
        unique_together = (("user", "guild"),)


class Attendance(Model):
    id = fields.IntField(pk=True)
    date = fields.DateField(null=False)
    member = fields.ForeignKeyField("models.Member", related_name="attendances", on_delete=fields.CASCADE)
    checked_in_at = SafeDateTimeField(null=False)

    class Meta:
        table = "attendances"
        unique_together = (("date", "member"),)


class Metadata(Model):
    guild = fields.ForeignKeyField("models.Guild", related_name="metadata", on_delete=fields.CASCADE)
    key = fields.CharField(max_length=255, null=False)
    value = SafeDateTimeField(null=False)

    class Meta:
        table = "metadata"
        unique_together = (("guild", "key"),)
