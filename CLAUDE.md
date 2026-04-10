# Context Engine — Claude Code Master Context

## What This Product Is

An AI-native organisational context engine for SMEs.
Employees ask questions via WhatsApp (or REST) in any language.
The system answers from connected knowledge sources (Google Drive, GitHub) with citations.

Target: Indian SMEs, 10–200 employees, English + Hindi on launch.
Vision: Global emerging markets, all languages, all knowledge sources.

---

## Non-Negotiable Engineering Principles

### SOLID
- **S** — Every class does ONE thing. `QueryService` queries. `ChunkingService` chunks. Never mix.
- **O** — New connectors, LLMs, or interfaces must NOT require changes to core domain logic.
- **L** — Any LLM, any vector DB, any connector must be swappable via config, not code change.
- **I** — Interfaces are narrow. WhatsApp adapter only needs `receive()` and `send()`. Nothing else.
- **D** — Core domain NEVER imports from infrastructure. Infrastructure imports from domain.

### DRY
- Chunking logic lives in ONE place: `ChunkingService`. Never anywhere else.
- Permission checking lives in ONE place: `PermissionService`. Never anywhere else.
- Tenant resolution lives in ONE place: `TenantContextMiddleware`. Never anywhere else.

### KISS
- If you cannot explain a component to a junior dev in 5 minutes, it is too complex.
- Postgres job queue before Celery. RLS before schema-per-tenant. REST before MCP at MVP.

### YAGNI
- Do not build what no paying customer has asked for.
- No knowledge graph at MVP. No custom conflict resolution engine at MVP. No self-hosted LLM at MVP.

---

## Architecture: Hexagonal (Ports and Adapters)

```
domain/          ← Pure Python. Zero external imports. Business logic only.
ports/           ← Abstract interfaces (ABCs). One file per port.
services/        ← Orchestration. Depends only on ports. Never on concrete adapters.
adapters/
  inbound/       ← FastAPI routes, WhatsApp webhook, Slack webhook
  outbound/      ← Qdrant, OpenAI, Anthropic, Postgres implementations
  connectors/    ← Google Drive, GitHub — implement ConnectorPort
infra/           ← Container (DI wiring), middleware, job queue, config
migrations/      ← SQL migration files, numbered sequentially
tests/
  unit/          ← Test domain and services only. Mock all ports.
  integration/   ← Test RLS, real DB, real Qdrant.
scripts/         ← One-off scripts: seed data, test ingestion, load test
```

### The Core Rule
`domain/` and `services/` MUST NOT import anything from `adapters/` or `infra/`.
If you see `from adapters.` inside `services/`, it is a violation. Fix it immediately.

---

## Tech Stack (Final Decisions — Do Not Debate These)

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | ML ecosystem, team skill |
| Web framework | FastAPI | Async, type-safe, fast |
| ORM / DB | Supabase + raw SQL + psycopg3 | RLS requires raw SQL for SET app.current_org_id |
| Vector DB | Qdrant Cloud (free tier → paid) | Best multi-tenant namespacing, hybrid search |
| Embeddings | `text-embedding-3-small` (OpenAI) | $0.02/1M tokens, 1536-dim, good Hindi |
| LLM | Gemini 2.0 Flash (primary), Claude Haiku (fallback) | Cost-optimised, multilingual |
| RAG framework | LlamaIndex (connectors + chunking utilities only) | Don't use LlamaIndex for retrieval logic — build that yourself |
| Chunking | `chonkie` library behind `ChunkingService` port | RAG-native, strategy-based |
| Doc parsing | `unstructured` OSS library | Handles PDF, DOCX, HTML |
| Language detect | `langdetect` (in-process, <1ms) | No API call needed |
| Translation | `deep-translator` (Google Translate free tier) | 500K chars/month free |
| Auth | Supabase Auth | Handles JWT, org invite flow |
| Job queue | Postgres-backed (SELECT FOR UPDATE SKIP LOCKED) | KISS — no Celery at MVP |
| WhatsApp | Friend's WhatsApp Business API (WATI-compatible webhook) | Already available |
| Hosting | Render Singapore (dev) → DigitalOcean Bangalore (prod) | Speed now, residency later |
| Error tracking | Sentry free tier | 5-minute setup |
| Frontend | Plain HTML + HTMX | No React build step at MVP |

---

## Database: Multi-Tenancy via Postgres RLS

Every table has `org_id UUID NOT NULL`.
Every query sets `SET LOCAL app.current_org_id = $org_id` before executing.
RLS policy pattern (COPY THIS EXACTLY — do not improvise):

```sql
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

CREATE POLICY {table}_isolation ON {table}
  USING (org_id = current_setting('app.current_org_id', true)::uuid);
```

The `true` in `current_setting(..., true)` is MANDATORY.
It makes missing context return NULL (safe: zero rows) not throw an error (unsafe: all rows).

**RLS test must pass before any feature is considered done:**
```python
# Insert data as org_a, query as org_b, assert len(results) == 0
```

---

## Core Domain Models (domain/models.py)

```python
# Pure dataclasses — zero imports except stdlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class SourceType(Enum):
    GOOGLE_DRIVE = "google_drive"
    GITHUB_PR = "github_pr"
    GITHUB_CODE = "github_code"
    SLACK = "slack"
    NOTION = "notion"

class Language(Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    MARATHI = "mr"
    BENGALI = "bn"

@dataclass
class Document:
    id: str
    org_id: str
    source_type: SourceType
    source_url: str
    title: str
    content: str
    authority_score: float  # 1.0=code, 0.9=pr, 0.7=doc, 0.5=chat
    updated_at: datetime
    language: Language = Language.ENGLISH

@dataclass
class Chunk:
    id: str
    document_id: str
    org_id: str
    content_text: str
    source_url: str
    source_type: SourceType
    authority_score: float
    updated_at: datetime
    is_stale: bool = False
    embedding: Optional[list[float]] = field(default=None, repr=False)

@dataclass
class QueryResult:
    answer: str
    citations: list[dict]  # [{title, url, source_type, updated_at}]
    response_language: str
    latency_ms: dict  # {detect_ms, translate_ms, embed_ms, retrieve_ms, generate_ms}
    error: Optional[str] = None
```

---

## Port Interfaces (ports/ directory)

Every adapter MUST implement its port. Never use a concrete adapter directly in services.

```python
# ports/vector_store.py
from abc import ABC, abstractmethod
from domain.models import Chunk

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> None: ...
    @abstractmethod
    def query(self, embedding: list[float], query_text: str,
              org_id: str, top_k: int = 10) -> list[Chunk]: ...
    @abstractmethod
    def mark_stale(self, document_id: str) -> None: ...

# ports/embedding_provider.py
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    @abstractmethod
    def dimensions(self) -> int: ...

# ports/llm_provider.py
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, query: str, context_chunks: list[Chunk],
                 response_language: str) -> str: ...

# ports/connector_port.py
class ConnectorPort(ABC):
    @abstractmethod
    def fetch_documents(self, org_id: str, since=None) -> list[Document]: ...
    @abstractmethod
    def source_type(self) -> SourceType: ...

# ports/document_parser.py
class DocumentParser(ABC):
    @abstractmethod
    def parse(self, raw_content: bytes, mime_type: str) -> str: ...
```

---

## LLM Prompt Template (do not change without testing)

```python
SYSTEM_PROMPT = """You are a knowledge assistant for {company_name}.
Answer questions based ONLY on the context provided below.
If the answer is not in the context, say: "I couldn't find information about that in your knowledge base."
Always cite the source document at the end of your answer.
Respond in {response_language}.
Be concise. Maximum 3 paragraphs."""

CONTEXT_BLOCK = """
Context:
{chunks_formatted}

Question: {query}
Answer:"""
```

---

## What Is Faked at MVP (do not build these)

- Admin dashboard: single HTML page with DB count queries
- Billing: manual Razorpay payment link
- Analytics: Google Sheet via gspread webhook
- Languages beyond Hindi+English: defer
- Fine-grained permissions: all org members see all org docs at MVP
- Conflict resolution engine: sort by `updated_at DESC`, use `authority_score` weight
- Self-hosted LLM: use managed APIs only
- Notion/Slack/Jira connectors: Google Drive + GitHub only at MVP

---

## Definition of Done (for any feature)

1. Unit test passes (mock all ports)
2. Integration test passes (real DB, RLS verified)
3. RLS tenant isolation test passes
4. No imports from `adapters/` inside `domain/` or `services/`
5. One-line description of what changed added to `CHANGELOG.md`

---

## Commands You Will Use Often

```bash
# Run all tests
pytest tests/ -v

# Run only RLS safety tests
pytest tests/integration/test_rls.py -v

# Trigger manual ingestion
python scripts/ingest.py --org-id $ORG_ID --source google_drive

# Start local dev
docker-compose up

# Run a test query
python scripts/query.py --org-id $ORG_ID --query "what is our leave policy?"
```

---

## Current Build Phase

**PHASE 1 (NOW):**
- [ ] Infrastructure + RLS + domain models + all port interfaces
- [ ] Ingestion pipeline (ChunkingService + EmbeddingProvider + VectorStore)
- [ ] Google Drive connector
- [ ] QueryService (hybrid retrieval + LLM generation + citations)
- [ ] WhatsApp webhook handler (inbound + outbound)
- [ ] FastAPI REST endpoint (same QueryService, different adapter)

**PHASE 2 (after first 3 customers):**
- [x] GitHub connector + PR enrichment
- Hindi language support
- Admin dashboard
- Production deploy to DigitalOcean Bangalore

**PHASE 3 (after $1K MRR):**
- Additional connectors (Notion, Slack, Jira)
- Full multilingual support (Tamil, Marathi, Bengali)
- MCP server for agent integration
- Fine-grained permissions