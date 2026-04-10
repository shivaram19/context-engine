"""
Query service — take a user query, return a cited answer.

Single responsibility: orchestrate the RAG pipeline (detect language → translate → embed → retrieve → filter → generate → cite).

Pipeline:
  1. Detect language
  2. Translate to English if needed (for embedding)
  3. Embed the (English) query
  4. Hybrid retrieve from VectorStore
  5. Permission filter
  6. Generate response in original language via LLM
  7. Return QueryResult with citations and latency breakdown

Zero imports from adapters/ or infra/.
"""

import logging
import time

from domain.models import QueryResult
from ports.embedding_provider import EmbeddingProvider
from ports.llm_provider import LLMProvider
from ports.vector_store import VectorStore
from services.permission_service import PermissionService
from services.translation_service import TranslationService

logger = logging.getLogger(__name__)


class QueryService:
    """
    Single responsibility: take a user query, return a cited answer.

    Dependencies injected via constructor (Dependency Inversion Principle).
    All dependencies are ports (abstractions), never concrete adapters.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        llm_provider: LLMProvider,
        permission_service: PermissionService,
        translation_service: TranslationService,
    ):
        """Initialize with port dependencies."""
        self._embed = embedding_provider
        self._store = vector_store
        self._llm = llm_provider
        self._perms = permission_service
        self._translate = translation_service

    def query(
        self,
        user_id: str,
        org_id: str,
        query_text: str,
        company_name: str = "your company",
    ) -> QueryResult:
        """
        Process a user query and return a cited answer.

        Args:
            user_id: User ID (for permissions)
            org_id: Organization ID (for tenant isolation)
            query_text: User's query in any language
            company_name: Company name for LLM context

        Returns:
            QueryResult with answer, citations, language, and latency breakdown
        """
        timings = {}
        t0 = time.monotonic()
        logger.debug(f"[QueryService] Starting query for org_id={org_id}, user_id={user_id}")

        try:
            # 1. Detect language (uses TranslationService for Hinglish override)
            detected_lang = self._translate.detect(query_text)
            timings["detect_ms"] = int((time.monotonic() - t0) * 1000)
            logger.debug(f"[QueryService] Language detected: {detected_lang} in {timings['detect_ms']}ms")

            # 2. Translate to English for embedding (English embeddings are best quality)
            t1 = time.monotonic()
            query_for_embedding = query_text
            if detected_lang != "en":
                query_for_embedding = self._translate.to_english(query_text, detected_lang)
                logger.debug(f"[QueryService] Translated query: {query_for_embedding}")
            timings["translate_ms"] = int((time.monotonic() - t1) * 1000)
            logger.debug(f"[QueryService] Translation done in {timings['translate_ms']}ms")

            # 3. Embed
            t2 = time.monotonic()
            embedding = self._embed.embed([query_for_embedding])[0]
            timings["embed_ms"] = int((time.monotonic() - t2) * 1000)
            logger.debug(f"[QueryService] Embedding generated in {timings['embed_ms']}ms, dim={len(embedding)}")

            # 4. Retrieve (hybrid: vector + BM25 fused via RRF)
            t3 = time.monotonic()
            logger.info(f"[QueryService] 🔍 Retrieving chunks with org_id={org_id}, top_k=8")
            chunks = self._store.query(
                embedding=embedding,
                query_text=query_for_embedding,
                org_id=org_id,
                top_k=8,
            )
            timings["retrieve_ms"] = int((time.monotonic() - t3) * 1000)
            logger.info(f"[QueryService] 📦 Retrieved {len(chunks)} chunks in {timings['retrieve_ms']}ms")

            # Log chunk details for debugging
            if chunks:
                for idx, chunk in enumerate(chunks[:3]):  # Log first 3
                    logger.debug(f"  Chunk {idx}: org_id={chunk.org_id}, doc_id={chunk.document_id}, score={chunk.authority_score}")

            # 5. Permission filter
            allowed_chunks = self._perms.filter(user_id, org_id, chunks)
            logger.info(f"[QueryService] 🔐 After permission filter: {len(allowed_chunks)}/{len(chunks)} chunks allowed")

            if not allowed_chunks:
                logger.info("[QueryService] No chunks found after filtering")
                return QueryResult(
                    answer="I couldn't find information about that in your knowledge base.",
                    citations=[],
                    response_language=detected_lang,
                    latency_ms=timings,
                )

            # 6. Generate
            t4 = time.monotonic()
            try:
                answer = self._llm.generate(
                    query=query_text,  # original language query
                    context_chunks=allowed_chunks,
                    response_language=detected_lang,
                    company_name=company_name,
                )
                logger.debug(f"[QueryService] LLM generation successful")
            except Exception as e:
                logger.error(f"[QueryService] LLM generation failed: {e}", exc_info=True)
                answer = "I encountered an error generating a response. Please try again."
            timings["generate_ms"] = int((time.monotonic() - t4) * 1000)
            logger.debug(f"[QueryService] Generation done in {timings['generate_ms']}ms")

            # 7. Build citations
            citations = [
                {
                    "title": c.source_url.split("/")[-1],
                    "url": c.source_url,
                    "source_type": c.source_type.value,
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in allowed_chunks[:3]  # top 3 citations only
            ]

            logger.info(
                f"[QueryService] query processed in {(time.monotonic()-t0)*1000:.0f}ms "
                f"(detect={timings['detect_ms']}ms, translate={timings['translate_ms']}ms, "
                f"embed={timings['embed_ms']}ms, retrieve={timings['retrieve_ms']}ms, "
                f"generate={timings['generate_ms']}ms)"
            )

            return QueryResult(
                answer=answer,
                citations=citations,
                response_language=detected_lang,
                latency_ms=timings,
            )

        except Exception as e:
            logger.error(f"[QueryService] Unexpected error in query pipeline: {e}", exc_info=True)
            # Initialize timings with defaults to ensure latency_ms is never undefined
            if not timings:
                timings = {
                    "detect_ms": 0,
                    "translate_ms": 0,
                    "embed_ms": 0,
                    "retrieve_ms": 0,
                    "generate_ms": 0,
                }
            return QueryResult(
                answer=f"An error occurred: {str(e)}",
                citations=[],
                response_language="en",
                latency_ms=timings,
            )
