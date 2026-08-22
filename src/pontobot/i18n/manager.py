# i18n/manager.py
import json
import logging
from pathlib import Path
from typing import Any

import discord

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "pt-br"}


def get_locale_str(locale: discord.Locale | str | None) -> str:
    """Converts a discord.Locale enum or raw locale string into a normalized language code."""
    if locale is None:
        return DEFAULT_LANGUAGE

    loc_str = str(locale.value if isinstance(locale, discord.Locale) else locale).lower().replace("_", "-")

    if loc_str.startswith("pt") or "portuguese" in loc_str:
        return "pt-br"
    return DEFAULT_LANGUAGE


def resolve_lang(
    locale: discord.Locale | str | None = None,
    guild_lang: str | None = None,
    ephemeral: bool = False,
) -> str:
    """Selects target language according to interaction scope (ephemeral vs public/text)."""
    if ephemeral and locale is not None:
        return get_locale_str(locale)

    if guild_lang:
        normalized = guild_lang.lower().replace("_", "-")
        if normalized in SUPPORTED_LANGUAGES:
            return normalized

    if locale is not None:
        return get_locale_str(locale)

    return DEFAULT_LANGUAGE


class TranslationManager:
    """Manager for loading locale translation files and retrieving interpolated text."""

    def __init__(self, locales_dir: Path | None = None):
        if locales_dir is None:
            locales_dir = Path(__file__).resolve().parent / "locales"

        self.locales_dir = locales_dir
        self.translations: dict[str, dict[str, Any]] = {}
        self.load_translations()

    def load_translations(self) -> None:
        """Loads all JSON files from the locales directory into memory."""
        self.translations.clear()
        if not self.locales_dir.exists():
            logger.warning("⚠️ Locales directory does not exist: %s", self.locales_dir)
            return

        for json_file in self.locales_dir.glob("*.json"):
            lang_code = json_file.stem.lower().replace("_", "-")
            try:
                with open(json_file, encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)
                logger.info("🌐 Loaded translation locale: %s", lang_code)
            except Exception as e:
                logger.error("❌ Failed to load locale %s: %s", json_file.name, e)

    def _get_nested(self, data: dict[str, Any], keys: list[str]) -> Any | None:
        curr = data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr

    def t(self, key: str, lang: str | discord.Locale = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
        """Translates a key into the target language with formatting kwargs."""
        lang_str = get_locale_str(lang) if isinstance(lang, (discord.Locale, str)) else DEFAULT_LANGUAGE
        keys = key.split(".")

        raw_template = None
        if lang_str in self.translations:
            raw_template = self._get_nested(self.translations[lang_str], keys)

        if raw_template is None and lang_str != DEFAULT_LANGUAGE and DEFAULT_LANGUAGE in self.translations:
            raw_template = self._get_nested(self.translations[DEFAULT_LANGUAGE], keys)

        if raw_template is None or not isinstance(raw_template, str):
            return key

        try:
            return raw_template.format(**kwargs)
        except (KeyError, ValueError, IndexError) as e:
            logger.warning("⚠️ Formatting error for key '%s' in lang '%s': %s", key, lang_str, e)
            return raw_template


translation_manager = TranslationManager()


def t(key: str, lang: str | discord.Locale = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """Global translation helper function."""
    return translation_manager.t(key, lang, **kwargs)
