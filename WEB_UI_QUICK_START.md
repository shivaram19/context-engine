# 🎨 Web UI Quick Start

You now have a **beautiful web interface** for setting up and testing Context Engine with your real data!

---

## 🚀 Getting Started (3 Steps)

### Step 1: Start the Server

```bash
# From the project root
uvicorn infra.main:app --reload
```

Server starts at: `http://localhost:8000`

### Step 2: Go to Setup Wizard

```
http://localhost:8000/setup
```

You'll see a beautiful setup form with:
- 🏢 Organization name
- 🐙 GitHub repository selector
- 📁 Google Drive folder finder
- ✅ Test connection button

### Step 3: Configure Your Data Sources

**For GitHub:**
1. Enter repository name: `owner/repo` (e.g., `your-org/your-api`)
2. Click "+ Add"
3. Repeat for multiple repos
4. Click "🧪 Test Connection" to verify

**For Google Drive:**
1. Enter folder ID (found in URL or share dialog)
2. Give it a friendly name (optional)
3. Click "+ Add"
4. When you start ingestion, you'll be prompted to authenticate

### Step 4: Save & Test

Click **"✅ Save & Continue"** → You'll be taken to the test interface

---

## 💬 Testing Interface

```
http://localhost:8000/setup/test
```

### Left Panel: Control & Status
- 📊 **Configuration summary** — shows what you configured
- **Status indicators:**
  - GitHub Repos count
  - Google Drive folders count
  - Documents indexed
  - Chunks in Qdrant
  - Current status (Ready / Ingesting)

- **Buttons:**
  - 🚀 **Start Ingestion** — fetches and indexes your data
  - 🔄 **Refresh Status** — checks ingestion progress

### Right Panel: Query Testing
- 🇬🇧 **English / 🇮🇳 Hindi** — toggle language
- **Query input** — ask questions about your knowledge base
- **Real-time results:**
  - ✅ Answer with citations
  - 📚 Source files linked
  - ⏱️ Performance metrics
    - Detect: language detection time
    - Translate: translation time (if needed)
    - Embed: embedding generation time
    - Retrieve: vector search time
    - Generate: LLM response time
    - Total: end-to-end latency

---

## 📋 Example Workflows

### Workflow 1: Test Your GitHub Repo

```
1. Go to http://localhost:8000/setup
2. Enter organization name: "Your Company"
3. Add GitHub repo: "your-org/your-api"
4. Click "🧪 Test Connection" ✅ (shows document count)
5. Click "✅ Save & Continue"
6. Click "🚀 Start Ingestion"
7. Wait 2-5 minutes...
8. Ask: "What are the main functions in this codebase?"
9. See: Answer with citations + latency metrics
```

### Workflow 2: Test HR Policies (Google Drive)

```
1. Go to http://localhost:8000/setup
2. Enter organization name: "Acme Corp"
3. Enable "Index from Google Drive"
4. Get folder ID from:
   - Right-click folder → Share
   - Copy from URL: drive.google.com/drive/folders/[ID]
5. Add folder: "1a2b3c4d5e6f7g8h9i0j"
   Name: "HR Policies"
6. Click "✅ Save & Continue"
7. Click "🚀 Start Ingestion"
8. Authenticate with Google Drive (one-time)
9. Wait 2-5 minutes...
10. Ask: "हमारी leave policy क्या है?" (in Hindi!)
11. Get: Answer in English or Hindi + sources
```

### Workflow 3: Full Stack Test

```
1. Configure both GitHub + Google Drive
2. Start ingestion (indexes everything)
3. Test queries in multiple languages
4. Monitor performance metrics
5. Refine setup based on results
```

---

## 🎯 What You Can Do in the UI

### Setup (/setup)
✅ Add/remove GitHub repos easily
✅ Add/remove Google Drive folders
✅ Test GitHub connection before ingesting
✅ See what will be indexed
✅ No terminal needed!

### Testing (/setup/test)
✅ View live status of indexed data
✅ Ask questions in real-time
✅ Switch languages (English/Hindi)
✅ See detailed performance metrics
✅ View citations with links to sources
✅ Monitor latency at each stage

---

## 🔧 API Endpoints (Used by UI)

You don't need to use these directly, but they're available:

```bash
# Get setup form
GET /setup

# Save configuration
POST /setup/api/save-config
{
  "organization_name": "Your Company",
  "github_enabled": true,
  "github_repos": ["your-org/repo"],
  "google_drive_enabled": false,
  "google_drive_folders": []
}

# Test GitHub connection
POST /setup/api/test-github
{
  "repos": ["your-org/repo"]
}

# Get current configuration
GET /setup/api/config

# Start ingestion
POST /setup/api/start-ingestion

# Check ingestion status
GET /setup/api/ingestion-status

# Query (same as before)
POST /api/v1/query
{
  "query": "What does the API do?",
  "org_id": "your-org",
  "company_name": "Your Company"
}
```

---

## 🎨 UI Features

### Beautiful Design
- 📱 Responsive (works on phone/tablet)
- 🎨 Modern gradient background
- ✨ Smooth animations and transitions
- 🌗 Clean, intuitive interface

### Smart Forms
- Auto-load saved configuration
- Form validation before saving
- Real-time feedback
- Clear error messages

### Live Updates
- Status badges show ingestion progress
- Performance metrics update in real-time
- Citations as clickable links
- Latency breakdown by stage

### User-Friendly
- No terminal commands needed
- Visual indicators for everything
- Help text for each field
- One-click testing

---

## 📊 Example Results

When you ask a question:

```
Question: "What does our authentication system do?"

Answer:
✅ The authentication system uses JWT tokens via Supabase.
   Tokens are validated in the TenantContextMiddleware...

Sources:
📚 1. rest_router.py
      https://github.com/your-org/your-api/blob/main/adapters/inbound/rest_router.py

   2. main.py
      https://github.com/your-org/your-api/blob/main/infra/main.py

Performance:
⏱️ Detect: 1ms      (What language?)
⏱️ Translate: 0ms   (Need translation?)
⏱️ Embed: 18ms      (Convert to vector)
⏱️ Retrieve: 42ms   (Find relevant chunks)
⏱️ Generate: 156ms  (Generate answer with LLM)
⏱️ Total: 217ms
```

---

## 🚨 Troubleshooting

### "GitHub connection failed"
→ Check GitHub PAT in .env
→ Verify repository name format: `owner/repo`

### "No documents fetched"
→ Check that the repo exists and is public
→ Verify GitHub token has `repo` scope

### "Google Drive folder not found"
→ Double-check folder ID format
→ Make sure folder is shared with your account
→ May need OAuth authentication

### "Ingestion stuck"
→ Refresh the page
→ Check browser console for errors
→ Try with smaller repo first

### "Slow query responses"
→ Normal on first query (LLM cold start)
→ Check your internet connection
→ Verify OpenAI/Gemini API keys in .env

---

## 📝 Notes

- **All configuration saved** to `config.data_sources.json`
- **No data leaves your machine** except:
  - To OpenAI (embeddings)
  - To Gemini/Claude (generating answers)
  - To your Qdrant instance (storage)
- **Privacy**: GitHub repos must be public
- **GitHub rate limits**: 60 requests/hour unauthenticated, 5000 with token

---

## 🎬 Next Steps

1. **Start server:** `uvicorn infra.main:app --reload`
2. **Open setup:** http://localhost:8000/setup
3. **Add your repos** (GitHub + Google Drive)
4. **Start ingestion** and wait ⏳
5. **Ask questions** and see real answers! 🎉

---

**Enjoy testing your Context Engine! 🚀**
