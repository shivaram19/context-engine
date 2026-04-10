"""
OpenAI LLM provider adapter.
Implements LLMProvider port using OpenAI's GPT models.
"""

import logging
from datetime import datetime

from openai import OpenAI

from domain.models import Chunk
from ports.llm_provider import LLMProvider
from adapters.outbound._prompt_templates import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class OpenAILLMAdapter(LLMProvider):
    """
    Implements LLMProvider using OpenAI's GPT models.
    Temperature: 0.1 (factual, low creativity)
    Max tokens: 512
    """

    MODEL = "gpt-4o-mini"  # Cost-effective, multilingual
    MAX_TOKENS = 512
    TEMPERATURE = 0.1

    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        self._client = OpenAI(api_key=api_key)

    def generate(
        self,
        query: str,
        context_chunks: list[Chunk],
        response_language: str,
        company_name: str = "your company",
    ) -> str:
        """
        Generate an answer using OpenAI.
        """
        try:
            # Format context
            context_text = self._format_context(context_chunks)

            # Build system prompt
            system = SYSTEM_PROMPT.format(
                company_name=company_name,
                response_language=response_language,
            )

            # Call API
            response = self._client.chat.completions.create(
                model=self.MODEL,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": f"Context:\n{context_text}\n\nQuestion: {query}\nAnswer:",
                    }
                ],
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"[OpenAILLMAdapter] generate failed: {e}")
            return "I encountered an error generating a response. Please try again."

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
