# i18n/translator.py
import logging

import discord
from discord import app_commands

from .manager import get_locale_str, translation_manager

logger = logging.getLogger(__name__)


class PontoBotTranslator(app_commands.Translator):
    """Custom Discord app_commands Translator for native slash command UI localization."""

    async def load(self) -> None:
        """Called when the translator is loaded into the bot tree."""
        logger.info("🌐 PontoBotTranslator loaded.")

    async def unload(self) -> None:
        """Called when the translator is unloaded from the bot tree."""
        logger.info("🌐 PontoBotTranslator unloaded.")

    async def translate(
        self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContextTypes
    ) -> str | None:
        """Translates command names, descriptions, parameters, and choice labels."""
        lang_str = get_locale_str(locale)
        msg_str = str(string)

        translated = translation_manager.t(msg_str, lang=lang_str)
        if translated != msg_str:
            return translated

        location = getattr(context, "location", None)
        data = getattr(context, "data", None)

        if location == app_commands.TranslationContextLocation.command_name and hasattr(data, "name"):
            key = f"commands.{data.name}.name"
            val = translation_manager.t(key, lang=lang_str)
            return val if val != key else None

        if location == app_commands.TranslationContextLocation.command_description and hasattr(data, "name"):
            key = f"commands.{data.name}.description"
            val = translation_manager.t(key, lang=lang_str)
            return val if val != key else None

        if location == app_commands.TranslationContextLocation.parameter_name and hasattr(data, "name"):
            cmd_name = getattr(getattr(data, "command", None), "name", "")
            if cmd_name:
                key = f"commands.{cmd_name}.param.{data.name}.name"
                val = translation_manager.t(key, lang=lang_str)
                return val if val != key else None

        if location == app_commands.TranslationContextLocation.parameter_description and hasattr(data, "name"):
            cmd_name = getattr(getattr(data, "command", None), "name", "")
            if cmd_name:
                key = f"commands.{cmd_name}.param.{data.name}.description"
                val = translation_manager.t(key, lang=lang_str)
                return val if val != key else None

        return None
