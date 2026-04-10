# Vision for Context Engine

## The Problem

10–200 person SMEs in emerging markets lose productivity searching for answers:
- "What was our leave policy again?"
- "Did we build something like this before?"
- "Who knows the customer's technical stack?"

Employees ask colleagues, miss deadlines, and duplicate work. Knowledge lives in:
- Google Drive (scattered docs)
- GitHub (PRs, code comments)
- WhatsApp (tribal knowledge)
- Slack (ephemeral)
- Notion (when it's updated)

**There is no single source of truth.**

---

## The Solution

**Context Engine** — an AI assistant that answers from your actual knowledge sources, in your language, with citations.

**Today (Phase 1 — MVP):**
```
Employee (WhatsApp)
    ↓
Context Engine
    ↓ (retrieves)
    ├─ Google Drive docs
    └─ GitHub code/PRs
    ↓ (augments)
    ├─ Semantically chunks
    ├─ Embeds with OpenAI
    ├─ Scores by authority
    ↓ (generates)
    ├─ Gemini 2.0 Flash answer
    ├─ With citations
    └─ In English or Hindi
```

Multi-tenant, RLS-enforced, ~5 second latency.

---

## The Vision: Global, Multilingual, All Sources

### Phase 1 (NOW) ✅
**Goal:** Prove PMF with 3 customers, Indian market.

**Scope:**
- Python 3.11 + FastAPI + Supabase + Qdrant
- Google Drive + GitHub connectors
- WhatsApp + REST APIs
- English + Hindi (detection + translation)
- Multi-tenant RLS isolation
- Job queue (Postgres-based)

**Success metrics:**
- 3 paying customers
- <5s query latency
- 0 data leaks (RLS holds)
- >80% answer relevance (manual eval)

---

### Phase 2 (After 3 Customers)
**Goal:** Scale to 10 customers, add Polish.

**Features:**
- **Notion connector** — structured databases as context
- **Slack connector** — channel history ingestion
- **Better chunking** — adaptive chunk size by document type
- **Admin dashboard** — org stats, ingestion monitoring, cost tracking
- **Billing** — Razorpay integration, usage-based pricing
- **Analytics** — Google Sheets webhook, query trends
- **Tamil + Marathi + Bengali support** — full regional coverage for India

**Deployment:**
- Migrate from Render (Singapore) → DigitalOcean Bangalore
- CDN for assets (BunnyCDN or Cloudflare)
- Observability: Sentry → cloud logs, custom dashboards

**Success metrics:**
- 10 customers, $500 MRR
- <10 concurrent users supported
- Admin dashboard adoption >90%

---

### Phase 3 (After $1K MRR)
**Goal:** Expand beyond India, add enterprise features.

**Features:**
- **Fine-grained permissions** — "only Sales sees pipeline docs"
- **Conflict resolution engine** — automatic merging of outdated chunks
- **Jira + Confluence connectors** — enterprise software teams
- **Multilingual support** — Spanish, Portuguese, French, Arabic
- **Real-time connectors** — Slack, Jira webhooks (not polling)
- **Web UI** — prettier than current HTML+HTMX
- **MCP server** — integrate into Claude.ai, Claude Desktop, other agents
- **Prompt templates** — org-specific prompt engineering

**Expansion:**
- Southeast Asia (Thai, Vietnamese)
- Latin America (Spanish, Portuguese)
- Africa (Swahili, Yoruba)

**Success metrics:**
- $5K MRR, 50+ customers
- <2s latency (caching layer)
- MCP integration adoption

---

### Phase 4+ (Long Term)
**Goal:** The connective layer for all knowledge in every org.

**Possibilities:**
- **Self-hosted option** — for enterprise data privacy
- **Custom LLM fine-tuning** — per-org knowledge distillation
- **GraphQL API** — for advanced integrations
- **Mobile apps** — native iOS/Android
- **Voice interface** — audio in, audio out
- **Document collaboration** — edit answers inline, sync back to source
- **Org structure aware** — departments, teams, access rules
- **Cost optimization** — batch embeddings, cheaper models for simple queries
- **Audit trail** — who asked what, when, for compliance

**Philosophy:**
- Always keep the core simple (never become a DB)
- Focus on retrieval quality > ML complexity
- Respect user privacy by default
- Support offline-first for unreliable networks

---

## Why This Matters

### For SMEs
- **Stop searching.** Ask in WhatsApp, get an answer with context.
- **Scale without hiring.** Junior staff can self-serve complex questions.
- **Avoid redundant work.** Know what's been built before.
- **Stay compliant.** Audit trail of decisions and sources.

### For Emerging Markets
- **No SaaS gatekeeping.** Build on open, swappable components.
- **Cost per query** will be <$0.001 (OpenAI embedding: $0.00002/1K, Gemini: $0.00005/1K).
- **Regional languages first-class.** Not translations of English UIs.
- **Network resilient.** Works with Qdrant + Postgres, no vendor lock-in.

### For Us
- Wedge into Indian SME market with <200 headcount per customer
- Predictable MRR (per-query + per-user pricing)
- Defensible moat: better chunking, better authority scoring, better Hindi understanding
- Expansion path: Southeast Asia → Latin America → Africa → Global

---

## Technical Principles

### Simplicity Over Sophistication
- Postgres job queue, not Celery
- RLS, not schema-per-tenant
- REST, not gRPC (at MVP)
- Plain HTML+HTMX, not React (until we need it)

### Swappability
- Any LLM: drop in new `LLMProvider`
- Any vector store: implement `VectorStore`
- Any connector: extend `ConnectorPort`
- Any embedding model: swap in `EmbeddingProvider`

### Safety First
- RLS enforced at database layer (trust nothing in code)
- Fallback LLM if primary fails
- Query audit log (every question, every source)
- Type hints + mypy on all code

### Customer Feedback Loop
- Weekly usage analytics pushed to Sheets
- Direct Slack/WhatsApp feedback channel
- Rapid iteration on chunking, scoring, language support
- Customers see themselves in the product

---

## Market Opportunity

**TAM (India only):**
- ~20M SMEs with 10–200 employees
- ~30% have digitized operations (6M)
- ~10% would pay for AI assistant (600K)
- At $50/month average = **$300M TAM**

**Addressable (Phase 1):**
- Bangalore + Mumbai tech SMEs
- 500 companies × $100/month = $5K/month
- Path to 5K customers (deep vertical focus) = $500K MRR

**Global (Phase 3+):**
- Similar SAM in Southeast Asia, LATAM, Africa
- Potential for $10M+ ARR at scale

---

## How to Contribute

This vision is only achievable with community:
- **Report bugs** → small PRs that ship fast
- **Build connectors** → Jira, Notion, Slack, Airtable
- **Improve multilingual** → Hindi, Tamil, Marathi, regional benchmarks
- **Suggest features** → we listen, but Phase 1 is locked
- **Deploy locally** → find bugs, give feedback, help SMEs test

See `CONTRIBUTING.md` for onboarding.

---

## Staying True to Values

As we grow, we will NOT:
- ❌ Become a general-purpose chatbot (we're not OpenAI)
- ❌ Add fine-grained permissions at cost of simplicity (Phase 1 is all-or-nothing per org)
- ❌ Require proprietary embeddings or LLMs (OpenAI/Gemini/Anthropic always pluggable)
- ❌ Centralize data (customers keep their sources, we only index + query)
- ❌ Squeeze SMEs (pricing will always be transparent, per-query, under 0.1 cent)

---

## Join Us

We're hiring engineers in India and globally (remote OK) for:
- Backend (Python, FastAPI, Postgres optimization)
- DevOps (Kubernetes, monitoring, DigitalOcean)
- ML/NLP (multilingual embeddings, ranking, chunking strategies)
- Product (understanding SME workflows, usability)

Or just contribute code. Either way, **let's build knowledge assistants for the world.** 🚀

---

**Last updated:** April 2026  
**Next review:** After 3 customers (Phase 2 kickoff)
