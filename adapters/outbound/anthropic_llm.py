"""
Anthropic LLM provider adapter.
Implements LLMProvider port using Claude Haiku (fallback model).
"""

import logging
from datetime import datetime

import anthropic

from domain.models import Chunk
from ports.llm_provider import LLMProvider
from adapters.outbound._prompt_templates import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class AnthropicLLMAdapter(LLMProvider):
    """
    Implements LLMProvider using Claude Haiku.
    Used as fallback when primary LLM (Gemini) is unavailable.
    Max tokens: 512
    """

    MODEL = "claude-haiku-4-5-20251001"
    MAX_TOKENS = 512

    def __init__(self, api_key: str):
        """Initialize Anthropic client."""
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        query: str,
        context_chunks: list[Chunk],
        response_language: str,
        company_name: str = "your company",
    ) -> str:
        """
        Generate an answer using Claude Haiku.
        """
        try:
            # Format context
            context_text = self._format_context(context_chunks)

            # Build system prompt
            system = SYSTEM_PROMPT.format(
                company_name=company_name,
                response_language=response_language,
            )

            # Build user message
            user_message = f"Context:\n{context_text}\n\nQuestion: {query}\nAnswer:"

            # Call API
            message = self._client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )

            return message.content[0].text

        except Exception as e:
            # Raise exception so failover adapter can try next provider
            logger.error(f"[AnthropicLLMAdapter] generate failed: {e}")
            raise

    def _format_context(self, chunks: list[Chunk]) -> str:
        """Format chunks into readable context."""
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            # Handle both datetime objects and ISO strings for updated_at
            if isinstance(chunk.updated_at, datetime):
                date_str = chunk.updated_at.strftime('%B %Y')
            else:
                # Try to parse as ISO string
                try:
                    dt = datetime.fromisoformat(str(chunk.updated_at))
                    date_str = dt.strftime('%B %Y')
                except (ValueError, TypeError):
                    date_str = str(chunk.updated_at)

            formatted.append(
                f"[{i}] Source: {chunk.source_url}\n"
                f"Date: {date_str}\n"
                f"Content: {chunk.content_text[:800]}\n"
            )
        return "\n---\n".join(formatted)
