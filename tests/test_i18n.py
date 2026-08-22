# tests/test_i18n.py
from unittest.mock import MagicMock

import discord
import pytest
from discord import app_commands

from pontobot.i18n import PontoBotTranslator, get_locale_str, resolve_lang, t


def test_get_locale_str():
    assert get_locale_str(discord.Locale.brazil_portuguese) == "pt-br"
    assert get_locale_str(discord.Locale.american_english) == "en"
    assert get_locale_str(discord.Locale.japanese) == "en"
    assert get_locale_str("pt-br") == "pt-br"
    assert get_locale_str("pt_BR") == "pt-br"
    assert get_locale_str(None) == "en"


def test_resolve_lang():
    # Ephemeral uses locale if present
    assert resolve_lang(locale=discord.Locale.brazil_portuguese, guild_lang="en", ephemeral=True) == "pt-br"
    # Non-ephemeral uses guild_lang
    assert resolve_lang(locale=discord.Locale.brazil_portuguese, guild_lang="en", ephemeral=False) == "en"
    assert resolve_lang(locale=discord.Locale.american_english, guild_lang="pt-br", ephemeral=False) == "pt-br"
    # Fallback to locale if no guild_lang
    assert resolve_lang(locale=discord.Locale.brazil_portuguese, guild_lang=None, ephemeral=False) == "pt-br"
    # Fallback to en
    assert resolve_lang(locale=None, guild_lang=None, ephemeral=False) == "en"


def test_t_function():
    # English lookup
    assert t("common.unexpected_error", lang="en") == "❌ An unexpected error occurred."
    # Portuguese lookup
    assert t("common.unexpected_error", lang="pt-br") == "❌ Ocorreu um erro inesperado."
    # Formatting
    assert (
        t("common.permission_denied_desc", lang="en", role="Admin")
        == "You need the `Admin` role to perform this action."
    )
    assert (
        t("common.permission_denied_desc", lang="pt-br", role="Admin")
        == "Você precisa do cargo `Admin` para realizar esta ação."
    )
    # Missing key fallback to key itself
    assert t("non_existent_key.sub", lang="pt-br") == "non_existent_key.sub"


@pytest.mark.asyncio
async def test_translator():
    translator = PontoBotTranslator()
    await translator.load()

    # 1. Test key lookup
    res_pt = await translator.translate(
        app_commands.locale_str("commands.attendance.description"),
        discord.Locale.brazil_portuguese,
        None,
    )
    assert res_pt == "Visualiza registros de presença e relatórios filtrados por usuário, período ou visão geral."

    # 2. Test command_name context
    ctx_cmd = MagicMock()
    ctx_cmd.location = app_commands.TranslationContextLocation.command_name
    ctx_cmd.data.name = "attendance"
    res_cmd_name = await translator.translate(
        app_commands.locale_str("attendance"),
        discord.Locale.brazil_portuguese,
        ctx_cmd,
    )
    assert res_cmd_name == "relatorio"

    # 3. Test parameter_description context
    ctx_param = MagicMock()
    ctx_param.location = app_commands.TranslationContextLocation.parameter_description
    ctx_param.data.name = "user"
    ctx_param.data.command.name = "attendance"
    res_param_desc = await translator.translate(
        app_commands.locale_str("Select a specific user (Optional)."),
        discord.Locale.brazil_portuguese,
        ctx_param,
    )
    assert res_param_desc == "Selecione um usuário específico (Opcional)."

    await translator.unload()
