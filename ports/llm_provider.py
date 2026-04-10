"""LLM provider port interface."""

from abc import ABC, abstractmethod
from domain.models import Chunk


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(
        self,
        query: str,
        context_chunks: list[Chunk],
        response_language: str,
        company_name: str = "your company",
    ) -> str:
        """Generate an answer based on query and context chunks."""
        ...
