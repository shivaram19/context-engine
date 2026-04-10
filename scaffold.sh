#!/bin/bash
# scaffold.sh — run this once in your project root
# Creates the entire folder structure and empty __init__.py files
# Usage: chmod +x scaffold.sh && ./scaffold.sh

set -e

echo "🏗️  Scaffolding context-engine project structure..."

# Core directories
mkdir -p domain
mkdir -p ports
mkdir -p services
mkdir -p adapters/inbound
mkdir -p adapters/outbound
mkdir -p adapters/connectors
mkdir -p infra
mkdir -p migrations
mkdir -p tests/unit/services
mkdir -p tests/unit/adapters
mkdir -p tests/unit/connectors
mkdir -p tests/integration
mkdir -p scripts
mkdir -p .claude/skills

# __init__.py for all Python packages
touch domain/__init__.py
touch ports/__init__.py
touch services/__init__.py
touch adapters/__init__.py
touch adapters/inbound/__init__.py
touch adapters/outbound/__init__.py
touch adapters/connectors/__init__.py
touch infra/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/unit/services/__init__.py
touch tests/unit/adapters/__init__.py
touch tests/unit/connectors/__init__.py
touch tests/integration/__init__.py

# Stub files — Claude Code fills these in
touch domain/models.py
touch ports/vector_store.py
touch ports/embedding_provider.py
touch ports/llm_provider.py
touch ports/connector_port.py
touch ports/document_parser.py
touch services/query_service.py
touch services/ingestion_service.py
touch services/chunking_service.py
touch services/permission_service.py
touch services/translation_service.py
touch adapters/inbound/rest_router.py
touch adapters/inbound/whatsapp_handler.py
touch adapters/outbound/qdrant_adapter.py
touch adapters/outbound/openai_embed_adapter.py
touch adapters/outbound/gemini_llm.py
touch adapters/outbound/anthropic_llm.py
touch adapters/outbound/failover_llm.py
touch adapters/outbound/unstructured_parser.py
touch adapters/connectors/google_drive.py
touch adapters/connectors/github.py
touch infra/container.py
touch infra/tenant_middleware.py
touch infra/job_queue.py
touch infra/config.py
touch infra/database.py
touch scripts/ingest.py
touch scripts/query.py
touch scripts/demo.py
touch scripts/seed_demo_data.py
touch tests/integration/test_rls_chunks.py
touch tests/integration/test_rls_queries.py
touch tests/unit/services/test_query_service.py
touch tests/unit/services/test_ingestion_service.py
touch tests/unit/services/test_chunking_service.py
touch tests/unit/connectors/test_google_drive.py
touch tests/unit/connectors/test_github.py
touch tests/unit/adapters/test_gemini_llm.py
touch tests/unit/adapters/test_qdrant_adapter.py

# Config files
cat > .env.example << 'EOF'
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=chunks

# LLM
GOOGLE_AI_API_KEY=your-gemini-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Embeddings
OPENAI_API_KEY=your-openai-api-key

# WhatsApp (friend's WATI)
WATI_API_URL=https://live-server.wati.io
WATI_API_KEY=your-wati-api-key
WATI_PHONE_NUMBER=+91XXXXXXXXXX

# Google Drive OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# GitHub
GITHUB_PAT=your-personal-access-token

# App
APP_SECRET_KEY=generate-with-openssl-rand-hex-32
ENVIRONMENT=development
SENTRY_DSN=your-sentry-dsn-optional
EOF

cat > requirements.txt << 'EOF'
# Web
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
httpx==0.27.0

# Database
supabase==2.7.0
psycopg[binary,pool]==3.2.0
asyncpg==0.29.0

# Vector DB
qdrant-client==1.11.0

# LLM & Embeddings
anthropic==0.34.0
google-generativeai==0.8.0
openai==1.45.0

# RAG
llama-index-core==0.11.0
llama-index-readers-google==0.3.0
chonkie==0.3.0
unstructured[pdf,docx]==0.15.0

# Language
langdetect==1.0.9
deep-translator==1.11.4

# Connectors
google-api-python-client==2.145.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
PyGithub==2.4.0

# Utils
python-dotenv==1.0.1
pydantic==2.9.0
pydantic-settings==2.5.0

# Testing
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-mock==3.14.0

# Monitoring
sentry-sdk[fastapi]==2.14.0
EOF

cat > docker-compose.yml << 'EOF'
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - .:/app
    command: uvicorn infra.main:app --reload --host 0.0.0.0 --port 8000
    depends_on:
      - worker

  worker:
    build: .
    env_file: .env
    volumes:
      - .:/app
    command: python infra/job_queue.py

EOF

cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
EOF

cat > pytest.ini << 'EOF'
[pytest]
asyncio_mode = auto
testpaths = tests
markers =
    integration: marks tests as integration (require real DB/APIs)
    unit: marks tests as unit (all external dependencies mocked)
EOF

cat > CHANGELOG.md << 'EOF'
# Changelog

## [Unreleased]
- Initial project scaffold
EOF

echo ""
echo "✅ Project structure created successfully!"
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env && fill in your API keys"
echo "  2. pip install -r requirements.txt"
echo "  3. Open in Claude Code: claude"
echo "  4. Claude Code will read CLAUDE.md automatically"
echo "  5. First command: ask Claude Code to implement domain/models.py"
echo ""
echo "Folder structure:"
find . -type f -name "*.py" | grep -v __pycache__ | sort
