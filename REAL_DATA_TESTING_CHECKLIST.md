# ✅ Real Data Testing — Complete Setup

## What You Now Have

### 1. **Unit Tests** (All Passing ✅)
```bash
pytest tests/unit -v
# 28 unit tests covering:
# - ChunkingService (8 tests)
# - QueryService (6 tests)
# - IngestionService (4 tests)
# - GeminiLLM (3 tests)
# - QdrantAdapter (4 tests)
# - E2E endpoints (3 tests)
```

### 2. **Real Data Scripts** (Ready to Use)

```bash
# Step 1: Configure your data sources
python scripts/setup_data_sources.py
# → Creates config.data_sources.json

# Step 2: Ingest your real data
python scripts/test_with_real_data.py
# → Fetches from GitHub/Google Drive
# → Indexes into Qdrant
# → Runs test queries

# Step 3: Ask questions interactively
python scripts/interactive_query.py
# → REPL for asking questions
# → See real answers + citations
# → Test in English/Hindi
```

### 3. **Documentation**
- `TESTING_WITH_REAL_DATA.md` — Complete guide
- `CLAUDE.md` — Architecture principles
- `.env.example` — All API keys configured

---

## Your Checklist

### ✅ Prerequisites (You have these)
- [ ] Google Drive API credentials in `.env`
- [ ] GitHub Personal Access Token in `.env`
- [ ] OpenAI API key in `.env`
- [ ] Gemini API key in `.env`
- [ ] Supabase credentials in `.env`
- [ ] Qdrant Cloud instance running

### 🚀 To Test with Real Data

#### Option A: Quick Test (10 minutes)
```bash
# 1. Run interactive test with GitHub repo
python scripts/test_with_real_data.py

# 2. Ask questions
python scripts/interactive_query.py

# 3. See real answers from YOUR data
```

#### Option B: Full Setup (30 minutes)
```bash
# 1. Configure your data sources
python scripts/setup_data_sources.py

# 2. Add Google Drive folder IDs (optional)
# 3. Add GitHub repository names

# 4. Run full ingestion
python scripts/test_with_real_data.py

# 5. Test with web UI
uvicorn infra.main:app --reload
# Visit http://localhost:8000/chat
```

#### Option C: Development Mode (Continuous)
```bash
# Terminal 1: Watch for changes
uvicorn infra.main:app --reload

# Terminal 2: Ask questions
python scripts/interactive_query.py

# Terminal 3: Monitor logs
tail -f .logs/*.log
```

---

## What Gets Tested

### Real Data Sources
- **GitHub**: Your actual repositories
- **Google Drive**: Your documents/policies
- **Qdrant**: Real vector embeddings
- **LLM**: Real Gemini/Claude responses

### Real Validation
✅ Chunking strategy works with your code/docs
✅ Embeddings are meaningful
✅ Retrieval finds relevant chunks
✅ LLM gives useful answers
✅ Citations point to real sources
✅ Latency is acceptable
✅ System handles errors gracefully

### Realistic Scenarios
- "What does our API do?" → Finds answer in code
- "हमारी छुट्टी नीति क्या है?" → Hindi question, English answer
- "How do we authenticate?" → Multiple citations
- "Unknown topic?" → Graceful fallback

---

## Key Differences from Unit Tests

| Aspect | Unit Tests | Real Data Tests |
|--------|-----------|-----------------|
| Data | Mock objects | Your actual files |
| API Calls | Mocked | Real (GitHub, Google Drive) |
| Embeddings | Fake vectors | Real OpenAI embeddings |
| Vector DB | Mocked | Real Qdrant instance |
| LLM | Mocked responses | Real Gemini/Claude |
| Latency | Instant | Real (200-500ms) |
| Citations | Made up | Actual source files |
| **Confidence** | Good code coverage | **Real working proof** |

---

## Files You'll Create

```
config.data_sources.json     ← Your data source configuration
.logs/                       ← Logs from real runs
Qdrant cloud/chunks/        ← Your real embeddings
```

---

## Commands Reference

```bash
# Unit tests (what we just did)
pytest tests/ -v

# Real data workflows
python scripts/setup_data_sources.py      # Configure
python scripts/test_with_real_data.py     # Ingest + test
python scripts/interactive_query.py       # Ask questions

# Web UI
uvicorn infra.main:app --reload
# → http://localhost:8000/chat

# REST API
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"what is our policy?","org_id":"your-org"}'
```

---

## What Happens When You Run Tests

### `test_with_real_data.py`
```
📁 STEP 1: Fetching from Google Drive...
   (OAuth required)

🐙 STEP 2: Fetching from GitHub...
   ✅ Connected as: your-username
   📊 Fetched 42 documents
   
   • schema.py
   • api.py
   • models.py
   (and 39 more)

🔄 STEP 3: Ingesting documents...
   ⏳ Chunking 42 documents...
   ⏳ Embedding 156 chunks...
   ⏳ Storing in Qdrant...
   ✅ Indexed 156 chunks

💬 STEP 4: Testing queries...
   
   Q: What are the main functions?
   A: The codebase contains several main functions
      including API endpoints for user management,
      document retrieval, and query processing...
   
   Citations: 3
   Total latency: 234ms
```

### `interactive_query.py`
```
💬 Context Engine — Interactive Query Tester

🤔 Question (EN): How do we handle errors?

⏳ Thinking...

✅ Answer:
Error handling uses try-catch blocks...

📚 Sources:
  1. error_handling.py
  2. middleware.py
  3. main.py

⏱️ Latency: 156ms
```

---

## Success Criteria

✅ You can run: `python scripts/test_with_real_data.py`
✅ It fetches from your GitHub repos
✅ It chunks and embeds documents
✅ It stores in Qdrant
✅ It runs test queries
✅ You see real answers with citations

Then:
✅ Run: `python scripts/interactive_query.py`
✅ Ask questions about your codebase
✅ Get answers with source citations
✅ See realistic latency (200-500ms)

---

## Next: Tell Me When Ready

Once you're ready to test with real data:

1. ✅ Make sure `.env` has your credentials
2. ✅ Run: `python scripts/setup_data_sources.py`
3. ✅ Add your GitHub repo/Google Drive folder
4. ✅ Run: `python scripts/test_with_real_data.py`
5. ✅ Report what you see!

**Then we can:**
- Debug any issues with real data
- Optimize chunking for your document types
- Fine-tune LLM prompts for your use case
- Test with your actual team

---

**You're now ready for REAL-WORLD testing! 🚀**
