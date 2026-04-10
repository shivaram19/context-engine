"""
Gemini LLM provider adapter.
Implements LLMProvider port using Google's Gemini 2.0 Flash model.
"""

import logging
from datetime import datetime

import google.generativeai as genai
from google.api_core import exceptions

from domain.models import Chunk
from ports.llm_provider import LLMProvider
from adapters.outbound._prompt_templates import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class GeminiLLMAdapter(LLMProvider):
    """
    Implements LLMProvider using Google's Gemini 2.0 Flash.
    Temperature: 0.1 (factual, low creativity)
    Max tokens: 512
    """

    MODEL = "gemini-2.0-flash"
    MAX_TOKENS = 512
    TEMPERATURE = 0.1

    def __init__(self, api_key: str):
        """Initialize Gemini client."""
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(self.MODEL)

    def generate(
        self,
        query: str,
        context_chunks: list[Chunk],
        response_language: str,
        company_name: str = "your company",
    ) -> str:
        """
        Generate an answer using Gemini.
        Catches rate limit errors separately from other errors.
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
            response = self._model.generate_content(
                [system, user_message],
                generation_config=genai.types.GenerationConfig(
                    temperature=self.TEMPERATURE,
                    max_output_tokens=self.MAX_TOKENS,
                ),
            )

            return response.text

        except Exception as e:
            # Raise exception so failover adapter can try next provider
            logger.error(f"[GeminiLLMAdapter] generate failed: {e}")
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
