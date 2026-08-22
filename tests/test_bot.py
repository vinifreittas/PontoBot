from unittest.mock import AsyncMock, MagicMock

import pytest
from discord import app_commands

from pontobot.bot import PontoBot

# ---------------------------------------------------------------------------
# Startup configuration
# ---------------------------------------------------------------------------


def test_sync_on_startup_defaults_to_false():
    bot = PontoBot(db_path=":memory:")
    assert bot.sync_on_startup is False


def test_sync_on_startup_reads_env_var(monkeypatch):
    monkeypatch.setenv("SYNC_COMMANDS", "true")
    bot = PontoBot(db_path=":memory:")
    assert bot.sync_on_startup is True


# ---------------------------------------------------------------------------
# _is_configured interaction guard
# ---------------------------------------------------------------------------


async def test_is_configured_raises_on_dm():
    bot = PontoBot(db_path=":memory:")
    interaction = MagicMock()
    interaction.guild = None

    with pytest.raises(app_commands.CheckFailure, match="only be used within a server"):
        await bot._is_configured(interaction)


async def test_is_configured_mentions_setup_pontobot():
    bot = PontoBot(db_path=":memory:")
    interaction = MagicMock()
    interaction.guild = MagicMock()
    interaction.guild_id = 999
    interaction.command.name = "attendance"

    with pytest.raises(app_commands.CheckFailure, match="/setup_pontobot"):
        await bot._is_configured(interaction)


# ---------------------------------------------------------------------------
# has_access — permission checks
# ---------------------------------------------------------------------------


async def test_has_access_grants_administrator():
    bot = PontoBot(db_path=":memory:")
    guild = MagicMock()
    guild.id = 1
    guild.owner_id = 555

    member = MagicMock()
    member.id = 111
    member.guild_permissions.administrator = True

    assert await bot.has_access(member, guild) is True


async def test_has_access_grants_guild_owner():
    bot = PontoBot(db_path=":memory:")
    guild = MagicMock()
    guild.id = 1
    guild.owner_id = 555

    member = MagicMock()
    member.id = 555
    member.guild_permissions.administrator = False

    assert await bot.has_access(member, guild) is True


async def test_has_access_grants_manager_role(monkeypatch):
    """A member with the configured manager role must be granted access."""
    bot = PontoBot(db_path=":memory:")
    guild = MagicMock()
    guild.id = 1
    guild.owner_id = 999

    member = MagicMock()
    member.id = 10
    member.guild_permissions.administrator = False
    manager_role = MagicMock()
    manager_role.id = 777
    member.roles = [manager_role]

    # Stub the database lookup to return a guild config with master_role_id = 777
    db_guild = MagicMock()
    db_guild.master_role_id = 777
    bot.db.get_guild = AsyncMock(return_value=db_guild)

    assert await bot.has_access(member, guild) is True


async def test_has_access_denies_regular_member(monkeypatch):
    """A non-admin, non-owner member without the manager role must be denied."""
    bot = PontoBot(db_path=":memory:")
    guild = MagicMock()
    guild.id = 1
    guild.owner_id = 999

    member = MagicMock()
    member.id = 10
    member.guild_permissions.administrator = False
    member.roles = []

    db_guild = MagicMock()
    db_guild.master_role_id = 777
    bot.db.get_guild = AsyncMock(return_value=db_guild)

    assert await bot.has_access(member, guild) is False
