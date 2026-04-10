"""
Failover LLM adapter (decorator pattern).
Implements LLMProvider by wrapping primary and fallback adapters.
Tries primary → on ANY exception, falls back to secondary → on exception, returns error message.
This adapter NEVER raises — it is the last line of defense.
"""

import logging

from domain.models import Chunk
from ports.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class FailoverLLMAdapter(LLMProvider):
    """
    Wraps two LLMProvider adapters (primary and fallback).
    Ensures generation always returns a response, never raises.
    Used in production as the top-level LLM provider.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        """
        Initialize with primary and fallback adapters.

        Args:
            primary: First LLM to try (e.g., Gemini)
            fallback: Second LLM if primary fails (e.g., Claude Haiku)
        """
        self._primary = primary
        self._fallback = fallback

    def generate(
        self,
        query: str,
        context_chunks: list[Chunk],
        response_language: str,
        company_name: str = "your company",
    ) -> str:
        """
        Try primary LLM. On any exception, try fallback.
        Never raise. Return error message if both fail.
        """
        # Try primary
        try:
            return self._primary.generate(
                query=query,
                context_chunks=context_chunks,
                response_language=response_language,
                company_name=company_name,
            )
        except Exception as e:
            logger.warning(
                f"[FailoverLLMAdapter] primary failed ({type(e).__name__}: {e}), trying fallback"
            )

        # Try fallback
        try:
            return self._fallback.generate(
                query=query,
                context_chunks=context_chunks,
                response_language=response_language,
                company_name=company_name,
            )
        except Exception as e:
            logger.error(
                f"[FailoverLLMAdapter] both primary and fallback failed ({type(e).__name__}: {e})"
            )

        # Both failed — return hardcoded error message (no more retries)
        return "I'm currently unable to process your request. Our systems are experiencing issues. Please try again shortly."
