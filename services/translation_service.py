"""
Translation service — translate queries to English for embedding, responses back to original language.

Uses deep-translator GoogleTranslator with LRU caching.
Detects Hinglish and handles gracefully.
Never raises — returns original text if translation fails.
"""

import logging
import re
from functools import lru_cache
from typing import Optional

from deep_translator import GoogleTranslator
import langdetect

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translate text between languages.

    Caches translations to avoid redundant API calls (many users query same topics in Hindi).
    Detects Hinglish (English written with Devanagari script).
    Never raises — returns original text on error.
    """

    # LRU cache size: 500 unique (text, source_lang) pairs
    _CACHE_SIZE = 500

    # Devanagari character range (Hindi, Marathi, etc.)
    _DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")

    def detect(self, text: str) -> str:
        """
        Detect language of input text.

        Uses langdetect for fast in-process detection (<1ms).
        Handles Hinglish: if langdetect returns 'en' but text contains >15% Devanagari,
        treats it as Hindi (Hinglish is often misdetected as English).

        Args:
            text: Text to detect language for

        Returns:
            ISO 639-1 language code (en, hi, etc.), or 'en' if detection fails
        """
        try:
            detected = langdetect.detect(text)
            # Hinglish override: langdetect often returns 'en' for mixed Hindi-English
            if detected == "en" and self.is_hinglish(text):
                logger.debug("[TranslationService] Hinglish detected, returning 'hi'")
                return "hi"
            return detected
        except Exception as e:
            logger.debug(f"[TranslationService] Language detection failed: {e}. Defaulting to 'en'")
            return "en"

    def to_english(self, text: str, source_lang: str) -> str:
        """
        Translate text to English for embedding.

        Args:
            text: Text to translate
            source_lang: ISO 639-1 language code (en, hi, ta, mr, bn)

        Returns:
            English translation, or original text if translation fails
        """
        if not text or not text.strip():
            return text

        # No translation needed if already English
        if source_lang == "en":
            return text

        # Detect Hinglish (English with Devanagari)
        if source_lang == "hi" and self.is_hinglish(text):
            logger.debug("[TranslationService] Hinglish detected, skipping translation")
            return text

        # Translate (cached)
        try:
            translated = self._translate_cached(text, source_lang, "en")
            logger.debug(
                f"[TranslationService] translated {len(text)} chars from {source_lang} to en"
            )
            return translated
        except Exception as e:
            logger.warning(
                f"[TranslationService] translation failed ({source_lang}→en): {e}. Using original text."
            )
            return text

    def to_language(self, text: str, target_lang: str) -> str:
        """
        Translate response text back to user's language.

        Args:
            text: English text to translate
            target_lang: ISO 639-1 language code

        Returns:
            Translated text, or original if translation fails
        """
        if not text or not text.strip():
            return text

        # No translation needed if target is English
        if target_lang == "en":
            return text

        try:
            translated = self._translate_cached(text, "en", target_lang)
            logger.debug(f"[TranslationService] translated response to {target_lang}")
            return translated
        except Exception as e:
            logger.warning(
                f"[TranslationService] response translation failed (en→{target_lang}): {e}. "
                "Returning English."
            )
            return text

    @lru_cache(maxsize=_CACHE_SIZE)
    def _translate_cached(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Cached translation using deep-translator.

        Wrapped in a separate method to enable LRU caching on immutable args (strings).
        """
        translator = GoogleTranslator(source_language=source_lang, target_language=target_lang)
        return translator.translate(text)

    @staticmethod
    def is_hinglish(text: str) -> bool:
        """
        Detect Hinglish (English written with Devanagari characters).

        Returns True if >15% of text is Devanagari characters.
        """
        if not text:
            return False

        devanagari_chars = len(TranslationService._DEVANAGARI_PATTERN.findall(text))
        total_chars = len(text)

        percentage = (devanagari_chars / total_chars * 100) if total_chars > 0 else 0
        is_hinglish = percentage > 15

        if is_hinglish:
            logger.debug(
                f"[TranslationService] Hinglish detected: {percentage:.1f}% Devanagari chars"
            )

        return is_hinglish
