# Testing Context Engine with Your Real Data

You now have **3 ways** to test the system with your actual knowledge sources:

---

## 🚀 Quick Start (5 minutes)

### 1️⃣ Set Up Your Data Sources

```bash
python scripts/setup_data_sources.py
```

This interactive wizard will ask you:
- Which Google Drive folders to index
- Which GitHub repositories to fetch
- What to exclude (node_modules, .env, etc.)

Creates: `config.data_sources.json`

---

### 2️⃣ Ingest Your Data

```bash
python scripts/test_with_real_data.py
```

This script will:
- ✅ Connect to your GitHub repos
- ✅ Fetch and chunk documents
- ✅ Embed chunks with OpenAI
- ✅ Store in Qdrant
- ✅ Run 3 test queries (English + Hindi)
- ✅ Show you performance metrics

**Output:**
```
📁 STEP 1: Fetching from Google Drive...
🐙 STEP 2: Fetching from GitHub...
   Fetched 42 documents from GitHub
   • api.py (main API implementation)
   • schema.py (database schemas)
   ...

🔄 STEP 3: Ingesting documents...
   ✅ Indexed 156 chunks into Qdrant

💬 STEP 4: Testing queries...
   🇬🇧 Q: What are the main functions in this codebase?
       A: The codebase provides several main functions...
       📚 Citations: 3
       ⏱️ 234ms to generate
```

---

### 3️⃣ Ask Questions (Interactive Mode)

```bash
python scripts/interactive_query.py
```

Now you can **ask questions in real-time** against your knowledge base:

```
🤔 Question (EN): What is the API authentication method?

⏳ Thinking...

✅ Answer:
The API uses JWT token-based authentication via Supabase.
The JWT is validated in the TenantContextMiddleware...

📚 Sources:
  1. rest_router.py
     https://github.com/your-repo/blob/main/adapters/inbound/rest_router.py

⏱️ Performance:
  • Detect: 1ms
  • Translate: 0ms
  • Embed: 18ms
  • Retrieve: 42ms
  • Generate: 156ms
  • Total: 217ms
```

You can also:
- Type `lang hi` to switch to Hindi
- Type `exit` to quit

---

## 📋 What You'll Test

### Google Drive
- Documents from specific folders
- PDFs, DOCs, Markdown files
- Automatically chunked by semantic boundaries

### GitHub
- Code from your repositories
- Issues, PRs, discussions
- Smart code chunking (by function/class)
- Only public repos (no secrets!)

### Real Data Validation
✅ Actual embeddings from OpenAI
✅ Real retrieval from Qdrant
✅ Real LLM responses from Gemini/Claude
✅ Real latency measurements
✅ Real citations with source URLs

---

## 🔧 Configuration

### Your .env File
Make sure these are set in `.env`:

```bash
# LLM
GOOGLE_AI_API_KEY=your-key  # Gemini
ANTHROPIC_API_KEY=your-key  # Claude (fallback)

# Embeddings
OPENAI_API_KEY=your-key

# GitHub
GITHUB_PAT=your-token

# Vector DB
QDRANT_URL=https://...
QDRANT_API_KEY=...
QDRANT_COLLECTION=chunks

# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
```

### Your Data Sources Config
Edit `config.data_sources.json` (created by setup wizard):

```json
{
  "organization": {
    "id": "shivaramgoud-org",
    "name": "Your Organization"
  },
  "google_drive": {
    "enabled": true,
    "folders": [
      {"id": "1a2b3c4d5e6f...", "name": "HR Policies"}
    ]
  },
  "github": {
    "enabled": true,
    "repositories": ["your-org/repo1", "your-org/repo2"],
    "exclude_paths": [".git", "node_modules", ".env"]
  }
}
```

---

## 📊 What You're Actually Testing

| Component | Test Type | Data |
|-----------|-----------|------|
| **Connectors** | Real API calls | Your Google Drive, GitHub |
| **Chunking** | Real documents | Your files/code |
| **Embedding** | Real OpenAI API | Your document chunks |
| **Vector Store** | Real Qdrant Cloud | Your embeddings |
| **LLM** | Real Gemini/Claude | Your question + context |
| **Retrieval** | Hybrid search | Your knowledge base |
| **Response** | Real answer | Your organization's knowledge |

---

## 🎯 Example Workflows

### Scenario 1: Test Your GitHub Repo
```bash
# Edit config.data_sources.json
# Add your repo: "your-org/my-api"

python scripts/test_with_real_data.py
# Your code gets indexed...

python scripts/interactive_query.py
# Ask questions like:
# "What does the payment module do?"
# "How is error handling implemented?"
# "What are the main dependencies?"
```

### Scenario 2: Test Your HR Policies (Google Drive)
```bash
# Setup wizard asks for Google Drive folder ID
# You authenticate at: http://localhost:8000/auth/google

python scripts/test_with_real_data.py
# Your documents get indexed...

python scripts/interactive_query.py
# Ask questions like:
# "What's our leave policy?"
# "हमारी leave policy क्या है?" (in Hindi!)
# "How many sick days do we get?"
```

### Scenario 3: Production-Like Test
```bash
# Setup both GitHub AND Google Drive
python scripts/setup_data_sources.py

# Ingest everything
python scripts/test_with_real_data.py

# Run the web UI
uvicorn infra.main:app --reload
# Visit http://localhost:8000/chat
```

---

## 🐛 Troubleshooting

### "GitHub API rate limited"
→ Wait 1 hour or upgrade your GitHub token

### "Qdrant connection failed"
→ Check `QDRANT_URL` and `QDRANT_API_KEY` in `.env`

### "No documents fetched"
→ Check folder IDs and repository names in config

### "Slow generation"
→ Normal on first query, uses real LLM API (not mocks)

### "Empty responses"
→ Might mean documents weren't chunked well
→ Try different queries or check document format

---

## 📈 What to Expect

- **First run**: 30-60 seconds (fetching + embedding)
- **Queries**: 200-500ms each (real LLM latency)
- **Citations**: Actual source files with line references
- **Accuracy**: Depends on your document quality

---

## 🔐 Security Notes

✅ Your credentials stay in `.env` (never committed)
✅ GitHub repos indexed are public-only
✅ Data stored in Qdrant (your cloud account)
✅ Queries logged to your database
✅ No data sent to third parties except:
   - OpenAI (embeddings)
   - Gemini (generation)

---

## 🎬 Next Steps

After testing with real data:

1. **Fine-tune**: Add more documents, test different queries
2. **Deploy**: Set up on a server with your team
3. **Monitor**: Check query logs and performance
4. **Expand**: Add more data sources (Slack, Notion, Jira)

---

## 📞 Commands Summary

```bash
# Setup
python scripts/setup_data_sources.py

# Test with real data
python scripts/test_with_real_data.py

# Interactive queries
python scripts/interactive_query.py

# Run web UI
uvicorn infra.main:app --reload

# Check logs
tail -f .logs/context-engine.log
```

---

**Now you're testing with REAL data, not mocks! 🚀**
