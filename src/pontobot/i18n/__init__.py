# i18n/__init__.py
from .manager import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TranslationManager,
    get_locale_str,
    resolve_lang,
    t,
    translation_manager,
)
from .translator import PontoBotTranslator

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "PontoBotTranslator",
    "TranslationManager",
    "get_locale_str",
    "resolve_lang",
    "t",
    "translation_manager",
]
