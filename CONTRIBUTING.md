# Contributing to Context Engine

Thank you for your interest in contributing to Context Engine! We're building an AI-native knowledge assistant for SMEs worldwide, and we'd love your help.

## Our Values

We believe in:
- **Simplicity** — KISS principle. Code must be explainable to a junior in 5 minutes.
- **Isolation** — SOLID architecture. Each component does one thing well.
- **Pragmatism** — YAGNI. We build what customers need, not what we imagine they might.
- **Inclusivity** — Knowledge assistants for emerging markets in all languages.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Local Setup

```bash
# Clone the repo
git clone https://github.com/shivaram19/context-engine.git
cd context-engine

# Copy env template and fill in your credentials
cp .env.example .env

# Start services (Supabase, Qdrant, Postgres)
docker-compose up

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run RLS safety tests (CRITICAL)
pytest tests/integration/test_rls.py -v
```

---

## Architecture Rules (Non-Negotiable)

Read `CLAUDE.md` for full context. TL;DR:

### The Hexagonal Rule
```
domain/ → Pure Python, zero external imports
services/ → Orchestration, depends only on ports, never on adapters
ports/ → Abstract interfaces (ABCs)
adapters/ → Concrete implementations (FastAPI, OpenAI, Qdrant, etc.)
infra/ → DI, middleware, database, config
```

**If you see `from adapters.` inside `domain/` or `services/`, it's a bug. Fix it immediately.**

### Multi-Tenancy via RLS
Every table has `org_id UUID NOT NULL`.
Every query **MUST** set `SET LOCAL app.current_org_id = $org_id` before executing.

Your PR must include an RLS isolation test:
```python
# Insert as org_a, query as org_b → assert len(results) == 0
```

### Tech Stack (Final — Do Not Debate)
- **Language:** Python 3.11+
- **Web:** FastAPI
- **DB:** Supabase + raw SQL (RLS requires it)
- **Vector:** Qdrant Cloud
- **Embeddings:** OpenAI text-embedding-3-small
- **LLM:** Gemini 2.0 Flash (primary), Claude Haiku (fallback)
- **Chunking:** chonkie (via ChunkingService)
- **Queue:** Postgres + SELECT FOR UPDATE SKIP LOCKED

Don't propose alternatives. We've decided these based on cost, multilingual support, and multi-tenant safety.

---

## Before You Code

### 1. Check the Phase
We're in **PHASE 1**. See `CLAUDE.md` for what's in/out:

**In Phase 1:**
- Core ingestion + querying
- Google Drive + GitHub connectors
- WhatsApp + REST interfaces
- Multi-tenant RLS

**NOT in Phase 1:**
- Admin dashboard (not yet)
- Notion/Slack/Jira (Phase 2+)
- Fine-grained permissions (Phase 3+)
- Self-hosted LLM (never — use managed APIs)
- Knowledge graphs (too early)

### 2. Claim an Issue
- Check existing GitHub issues
- Comment "I'll take this" to claim
- If no issue exists, **open one first** and discuss approach
- PRs without prior discussion risk being closed

### 3. Design First (for non-trivial changes)
- New connector? Design the `ConnectorPort` implementation
- New LLM? Show how it fits the failover pattern
- Schema change? Include RLS policy design

---

## Code Standards

### File Organization
```python
# 1. Imports (stdlib → ports → types → functions)
from abc import ABC, abstractmethod
from typing import Optional
from domain.models import Document
from ports.vector_store import VectorStore

# 2. Type hints everywhere
def query(self, text: str, org_id: str) -> list[Chunk]:
    pass

# 3. Docstrings only for non-obvious logic
class ChunkingService:
    """Split documents into retrievable chunks."""
    
    def chunk(self, doc: Document, strategy: str = "semantic") -> list[Chunk]:
        """Strategy: 'semantic' uses sentence boundaries; 'fixed' uses token count."""
        pass
```

### Naming
- **Services:** `XyzService` (e.g., `QueryService`)
- **Adapters:** `XyzAdapter` or `XyzProvider` (e.g., `GeminiLLM`)
- **Ports:** `XyzPort` (e.g., `EmbeddingProvider`)
- **Functions:** snake_case
- **Classes:** PascalCase

### Testing
Every feature needs:
1. **Unit test** — mock all ports, test business logic
2. **Integration test** — real DB + Qdrant, no mocks
3. **RLS test** — verify cross-org isolation

```bash
# Before submitting
pytest tests/unit -v
pytest tests/integration -v
pytest tests/integration/test_rls.py -v  # CRITICAL
```

### No Debugging Code
- Remove `print()` statements before commit
- Remove `# TODO`, `# FIXME` comments (use GitHub issues)
- No commented-out code (git history keeps it)

---

## PR Checklist

- [ ] Follows hexagonal architecture (no imports between layers)
- [ ] All tests pass: `pytest tests/ -v`
- [ ] RLS isolation test passes: `pytest tests/integration/test_rls.py -v`
- [ ] Type hints on all public functions
- [ ] No secrets in code (`.env.example` has placeholders only)
- [ ] Commit message follows pattern: `category: description`
  - Examples: `feat: add GitHub connector`, `fix: RLS policy null-safety`, `docs: update setup guide`
- [ ] One-line entry added to `CHANGELOG.md`

---

## Commit Messages

Be specific. Future-you will thank you.

```
✅ feat: add GitHub PR enrichment to authority scoring
  - PRs from verified repos now score 0.95 (vs 0.9 default)
  - Added gh_verified_repos table for org configuration
  - Integration test added for cross-org isolation

❌ update github connector
  - Made a change to scoring
```

---

## Common Contribution Patterns

### Adding a New Connector
1. Create `adapters/connectors/xyz.py` implementing `ConnectorPort`
2. Add to `Container` in `infra/container.py`
3. Unit test in `tests/unit/connectors/test_xyz.py`
4. Integration test for RLS isolation
5. Entry in `CHANGELOG.md`

### Adding LLM Support
1. Create `adapters/outbound/xyz_llm.py` implementing `LLMProvider`
2. Add to `FailoverLLM` in `adapters/outbound/failover_llm.py`
3. Unit test response format
4. Benchmark latency vs Gemini

### Schema Changes
1. Create migration: `migrations/NNN_description.sql` with RLS policies
2. Update `domain/models.py` and `services/` as needed
3. Migration test (run locally, verify RLS)
4. Backward-compatible (no dropping columns in Phase 1)

---

## Getting Help

- **Architecture questions?** Read `CLAUDE.md` first
- **Stuck on a test?** Ask in the GitHub issue
- **Design feedback?** Comment on your PR early
- **Deployment issues?** Ask maintainers (we handle Render/DigitalOcean)

---

## Review Process

1. We review within 48 hours
2. Feedback is always constructive
3. We prioritize:
   - Correctness > elegance
   - RLS safety > performance (for Phase 1)
   - Clear code > clever code

If your PR is closed, it's not rejection — we may have shipped it differently or prioritized other work. **Reopen or rework anytime.**

---

## Recognition

Contributors are listed in `CONTRIBUTORS.md`. We also shout out major contributions in release notes.

---

## Code of Conduct

- Be respectful (English, Hindi, or any language)
- No spam, harassment, or discrimination
- Assume good intent
- Disagree on ideas, not people

---

**Thank you for helping build knowledge assistants for emerging markets! 🚀**
