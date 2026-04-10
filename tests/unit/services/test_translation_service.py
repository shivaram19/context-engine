"""
Unit tests for TranslationService — language detection and translation caching.

Tests verify:
- Hindi detection works correctly
- Hinglish (mixed Devanagari + English) detected as Hindi
- Translation results are cached (API called only once for same input)
- Translation failures degrade gracefully (return original text)
"""

from unittest.mock import patch, MagicMock
from services.translation_service import TranslationService
import pytest


def test_detect_hindi():
    """Pure Hindi text should be detected as 'hi'."""
    svc = TranslationService()
    result = svc.detect("हमारी leave policy क्या है?")
    assert result == "hi"


def test_detect_english():
    """English text should be detected as 'en'."""
    svc = TranslationService()
    result = svc.detect("what is our leave policy?")
    assert result == "en"


def test_hinglish_detected_as_hindi():
    """Mixed Hindi (Devanagari) + English should be detected as Hindi (Hinglish override)."""
    svc = TranslationService()
    # This text has >15% Devanagari characters mixed with English
    hinglish_text = "हमारी team के लिए यह better है"
    result = svc.detect(hinglish_text)
    assert result == "hi"


def test_translation_cached():
    """Same Hindi query translated twice should call GoogleTranslator only once."""
    svc = TranslationService()
    hindi_query = "हमारी leave policy क्या है?"

    with patch('services.translation_service.GoogleTranslator') as MockTranslator, \
         patch.object(svc, 'is_hinglish', return_value=False):
        # Setup mock to return translation
        mock_instance = MagicMock()
        mock_instance.translate.return_value = "What is our leave policy?"
        MockTranslator.return_value = mock_instance

        # First call — should call GoogleTranslator
        result1 = svc.to_english(hindi_query, "hi")
        assert result1 == "What is our leave policy?"

        # Second call (same query) — should use cache, not call GoogleTranslator again
        result2 = svc.to_english(hindi_query, "hi")
        assert result2 == "What is our leave policy?"

        # GoogleTranslator.translate() called only once despite two to_english() calls
        # (The second call is served from @lru_cache)
        assert mock_instance.translate.call_count == 1


def test_translation_failure_returns_original():
    """When GoogleTranslator fails, to_english should return original text (no crash)."""
    svc = TranslationService()
    hindi_query = "हमारी leave policy क्या है?"

    with patch('services.translation_service.GoogleTranslator') as MockTranslator:
        # Setup mock to raise exception
        mock_instance = MagicMock()
        mock_instance.translate.side_effect = Exception("API down")
        MockTranslator.return_value = mock_instance

        # Should return original text, not raise
        result = svc.to_english(hindi_query, "hi")
        assert result == hindi_query  # original text returned
