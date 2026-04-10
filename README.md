# Context Engine

An AI-native organizational knowledge assistant for SMEs. Answer questions from Google Drive, GitHub, and beyond—in any language, with citations.

**Status:** Phase 1 (MVP) — actively seeking early customers and contributors.

---

## What It Does

Employees ask in WhatsApp (or REST API). The system:
1. Detects question language (English, Hindi, Tamil, etc.)
2. Searches Google Drive + GitHub for relevant documents/code
3. Chunks and embeds with OpenAI
4. Scores by authority (code > PR > doc > chat)
5. Generates answer with Gemini 2.0 Flash (Claude fallback)
6. Returns with citations

**Multi-tenant, RLS-isolated, fully typed, battle-tested for data safety.**

---

## Try It

### Quick Start (5 min)

```bash
# Clone and setup
git clone https://github.com/shivaram19/context-engine.git
cd context-engine

# Copy config
cp .env.example .env
# (Fill in your API keys: OpenAI, Gemini, Supabase, Qdrant, etc.)

# Start services
docker-compose up

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Test a query
python scripts/query.py --org-id test-org --query "what is our leave policy?"
```

See [SETUP_COMPLETE.md](SETUP_COMPLETE.md) for detailed setup.

---

## Architecture

**Hexagonal (Ports & Adapters):**
- `domain/` — Pure business logic, zero external imports
- `services/` — Orchestration (chunking, ingestion, queries, permissions)
- `ports/` — Abstract interfaces (pluggable LLMs, vector stores, connectors)
- `adapters/` — Implementations (Gemini, Claude, Qdrant, Google Drive, GitHub, WhatsApp)
- `infra/` — Infrastructure (RLS middleware, DI container, job queue)

**Multi-tenancy:**
- Every query sets `SET LOCAL app.current_org_id` before executing
- RLS policies enforce org isolation at database layer
- Zero risk of cross-org data leakage

See [CLAUDE.md](CLAUDE.md) for full architecture.

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | ML ecosystem, team skill |
| Web | FastAPI | Async, type-safe, fast |
| Database | Supabase (Postgres) + RLS | Multi-tenant by default |
| Vector DB | Qdrant Cloud | Best multi-tenant namespacing |
| Embeddings | OpenAI text-embedding-3-small | $0.02/1M tokens, 1536-dim, good multilingual |
| LLM | Gemini 2.0 Flash (primary) | Cost-optimized, multilingual |
| | Claude Haiku (fallback) | Reliability, fallback path |
| Chunking | chonkie + ChunkingService | RAG-native, strategy-based |
| Doc Parsing | Unstructured OSS | PDF, DOCX, HTML support |
| Queue | Postgres (SELECT FOR UPDATE) | KISS—no Celery at MVP |
| Auth | Supabase Auth | Handles JWT + org invites |
| Frontend | HTML + HTMX | No build step at MVP |
| Hosting | Render (dev), DigitalOcean (prod) | Speed + data residency path |

All choices are **final for Phase 1**. See [VISION.md](VISION.md) for evolution path.

---

## Roadmap

### Phase 1 (NOW) ✅
- [x] Core infrastructure + RLS + domain models
- [x] Ingestion pipeline (chunking, embedding, storage)
- [x] Google Drive connector
- [x] GitHub connector
- [x] QueryService (retrieval + generation + citations)
- [x] WhatsApp webhook handler
- [x] FastAPI REST endpoint
- [ ] 3 paying customers (in progress)

### Phase 2 (After 3 Customers)
- [ ] Notion + Slack connectors
- [ ] Hindi language support finalized
- [ ] Admin dashboard
- [ ] Billing integration (Razorpay)
- [ ] Migrate to DigitalOcean Bangalore

### Phase 3 (After $1K MRR)
- [ ] Fine-grained permissions
- [ ] Jira + Confluence connectors
- [ ] Full multilingual (Tamil, Marathi, Bengali, Spanish, Portuguese, etc.)
- [ ] MCP server for Claude.ai integration
- [ ] Web UI redesign

See [VISION.md](VISION.md) for detailed roadmap and long-term goals.

---

## Contributing

We're open to contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to set up locally
- Architecture rules (hexagonal, RLS, SOLID)
- Code standards and testing requirements
- How to claim an issue
- PR checklist

**All contributors are recognized in [CONTRIBUTORS.md](CONTRIBUTORS.md).**

### Quick Start for Contributors
```bash
# 1. Claim an issue (or open one to discuss first)
# 2. Read CLAUDE.md for architecture non-negotiables
# 3. Set up locally (see above)
# 4. Write code with tests
# 5. Ensure RLS isolation test passes: pytest tests/integration/test_rls.py -v
# 6. Submit PR with clear commit message
```

---

## Use Cases

**For Indian SMEs:**
- "What was our Q3 OKR?" → Searches Drive, cites doc
- "Have we built a subscription system?" → Searches GitHub, shows code
- "Who owns the customer DB?" → Searches Slack archive, names owner
- "What's in the new hire checklist?" → Cites policy doc, in Hindi

**For Tech Teams:**
- "How do we deploy to production?" → Cites runbook
- "What's our API rate limit?" → Cites PR discussion
- "Did we deprecate this endpoint?" → Cites code comment
- "Who reviewed the auth refactor?" → Cites PR

**For Distributed Teams:**
- Ask in WhatsApp, get answers in your language
- No need to search five tools
- Know *why* an answer is true (see the source)
- Reduce tribal knowledge, onboard faster

---

## License

MIT License. See [LICENSE](LICENSE) for details.

**Use freely. Modify freely. Contribute back if you find it useful.**

---

## Feedback & Support

- **Bug reports:** [GitHub Issues](https://github.com/shivaram19/context-engine/issues)
- **Feature requests:** [GitHub Discussions](https://github.com/shivaram19/context-engine/discussions)
- **Questions:** Open an issue with `[question]` tag
- **Security issues:** Email security@context-engine.io (non-public)

---

## Vision

We're building knowledge assistants for SMEs worldwide:
- Today: India, English + Hindi, Google Drive + GitHub
- Tomorrow: Southeast Asia, Latin America, Africa—all languages, all sources
- Future: The connective layer for organizational knowledge

See [VISION.md](VISION.md) for 5-year roadmap and market opportunity.

---

## Status

- **Phase:** 1 (MVP)
- **Stability:** Experimental (APIs may change)
- **Production Ready:** Yes (multi-tenant RLS tested)
- **Customers:** Seeking 3 early customers

**You could be customer #1.** Interested? Email shivaram@context-engine.io

---

## Thanks

Built with:
- Supabase for database + auth
- Qdrant for semantic search
- OpenAI for embeddings
- Google DeepMind for Gemini
- Anthropic for Claude fallback
- Open-source community (FastAPI, psycopg3, unstructured, chonkie)

And **you**, for considering contributing. 🚀
