"""Unit tests for custom ORM fields defined in database/models.py.

These tests exercise SafeDateTimeField in isolation — no database required.
"""

from datetime import UTC, datetime

from pontobot.database.models import SafeDateTimeField


class TestSafeDateTimeField:
    def test_returns_none_for_none(self):
        field = SafeDateTimeField()
        assert field.to_python_value(None) is None

    def test_passthrough_for_datetime(self):
        field = SafeDateTimeField()
        now = datetime.now(UTC)
        assert field.to_python_value(now) is now

    def test_parses_iso_string(self):
        field = SafeDateTimeField()
        result = field.to_python_value("2026-06-01T09:00:00+00:00")
        assert isinstance(result, datetime)
        assert result.year == 2026

    def test_returns_none_for_invalid_string(self):
        field = SafeDateTimeField()
        assert field.to_python_value("not-a-date") is None
