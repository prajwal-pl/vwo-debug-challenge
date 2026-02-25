# Financial Document Analyzer

A multi-agent AI system that analyzes financial documents (PDFs) using [CrewAI](https://docs.crewai.com/) and Google Gemini. Upload a financial report, and four specialized AI agents collaborate to verify, analyze, assess risk, and generate investment insights.

## Architecture

```
Client ──POST /analyze──▸ FastAPI ──▸ Redis Queue ──▸ Celery Worker
                  │                                       │
            returns task_id                         runs 4 CrewAI agents
                                                          │
Client ──GET /status/{id}──▸ FastAPI ◂── result ──── Redis Backend
```

**Agents** (defined in `agents.py`):

| Agent | Role |
|-------|------|
| `verifier` | Validates document authenticity and classifies document type |
| `financial_analyst` | Extracts key financial metrics, trends, and performance data |
| `investment_advisor` | Generates balanced, data-backed investment recommendations |
| `risk_assessor` | Evaluates risks using VaR, stress-testing, and mitigation frameworks |

**Tech Stack**: Python 3.12, FastAPI, CrewAI 0.130.0, Celery 5.6, Redis, SQLite, Google Gemini (gemini-2.5-flash via litellm), LangChain Community (PDF loading)

---

## Setup & Installation

### Prerequisites

- Python 3.12+
- Redis server (`sudo apt install redis-server`)
- A [Google Gemini API key](https://aistudio.google.com/apikey)
- (Optional) A [Serper API key](https://serper.dev/) for web search tool

### Install

```bash
# Clone and enter project directory
cd financial-document-analyzer-debug

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file or export directly:

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export SERPER_API_KEY="your-serper-api-key"   # optional
export REDIS_URL="redis://localhost:6379/0"   # default if not set
export DB_PATH="financial_analyzer.db"       # default if not set
```

---

## How to Run

### Quick Start (recommended)

```bash
chmod +x start.sh stop.sh test.sh

# Start all services (Redis, Celery worker, FastAPI)
./start.sh

# Stop all services
./stop.sh
```

### Manual Start

```bash
# 1. Start Redis
redis-server --daemonize yes

# 2. Activate venv and start Celery worker
source venv/bin/activate
celery -A tasks_worker worker --loglevel=info --concurrency=2 &

# 3. Start FastAPI
fastapi dev main.py
```

---

## API Documentation

Interactive Swagger docs are available at `http://localhost:8000/docs` when the server is running.

### `GET /`

Health check.

**Response:**
```json
{ "message": "Financial Document Analyzer API is running" }
```

### `POST /analyze`

Submit a PDF document for analysis. Returns immediately with a `task_id`.

**Request** (multipart/form-data):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF document to analyze |
| `query` | string | No | Analysis prompt (default: "Analyze this financial document for investment insights") |
| `user_id` | integer | No | Associate analysis with a user (must exist in DB) |

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@data/TSLA-Q2-2025-Update.pdf" \
  -F "query=What are the key financial risks?" \
  -F "user_id=1"
```

**Response:**
```json
{
  "status": "queued",
  "task_id": "abc123-def456-...",
  "analysis_id": 1,
  "message": "Document submitted for analysis. Poll /status/{task_id} for results."
}
```

### `GET /status/{task_id}`

Poll the analysis status. Returns the result when complete.

**Response (processing):**
```json
{
  "task_id": "abc123-def456-...",
  "status": "processing",
  "message": "Running..."
}
```

**Response (success):**
```json
{
  "task_id": "abc123-def456-...",
  "status": "success",
  "query": "What are the key financial risks?",
  "analysis": "## Financial Analysis Report\n..."
}
```

**Response (failed):**
```json
{
  "task_id": "abc123-def456-...",
  "status": "failed",
  "error": "Error description"
}
```

**Possible status values:** `pending`, `processing`, `retrying`, `success`, `failed`

### `GET /analyses`

List past analyses with optional filters and pagination.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `user_id` | int | — | Filter by user |
| `status` | string | — | Filter by status (`queued`, `processing`, `success`, `failed`) |
| `limit` | int | 20 | Max results (1–100) |
| `offset` | int | 0 | Pagination offset |

```bash
curl -s "http://localhost:8000/analyses?user_id=1&status=success&limit=5"
```

**Response:**
```json
{
  "count": 1,
  "analyses": [
    {
      "id": 1,
      "task_id": "abc123-...",
      "user_id": 1,
      "filename": "TSLA-Q2-2025-Update.pdf",
      "file_size": 9489744,
      "query": "Analyze revenue trends",
      "status": "success",
      "analysis": "## Financial Analysis Report\n...",
      "error": null,
      "created_at": "2026-02-25 09:59:54",
      "completed_at": "2026-02-25 10:03:12"
    }
  ]
}
```

### `GET /analyses/stats`

Get aggregate analysis statistics, optionally filtered by user.

```bash
curl -s http://localhost:8000/analyses/stats
curl -s "http://localhost:8000/analyses/stats?user_id=1"
```

**Response:**
```json
{
  "total": 10,
  "succeeded": 7,
  "failed": 1,
  "in_progress": 2,
  "total_bytes_processed": 94897440
}
```

### `GET /analyses/{task_id}`

Get a specific analysis record by its Celery task ID.

```bash
curl -s http://localhost:8000/analyses/abc123-def456-...
```

### `DELETE /analyses/{task_id}`

Delete a specific analysis record.

```bash
curl -s -X DELETE http://localhost:8000/analyses/abc123-def456-...
```

**Response:**
```json
{ "message": "Analysis deleted", "task_id": "abc123-def456-..." }
```

### `POST /users`

Create a new user.

**Request** (multipart/form-data):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username |
| `email` | string | No | Email address (unique if provided) |

```bash
curl -s -X POST http://localhost:8000/users -F "username=alice" -F "email=alice@example.com"
```

**Response:**
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "created_at": "2026-02-25 09:59:23"
}
```

### `GET /users`

List all users with pagination.

```bash
curl -s "http://localhost:8000/users?limit=10"
```

### `GET /users/{user_id}`

Get user details including their recent analyses and stats.

```bash
curl -s http://localhost:8000/users/1
```

**Response:**
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "created_at": "2026-02-25 09:59:23",
  "analyses": [ ... ],
  "stats": {
    "total": 3,
    "succeeded": 2,
    "failed": 0,
    "in_progress": 1,
    "total_bytes_processed": 28469232
  }
}
```

---

## CLI Scripts

### `start.sh`

Launches all services in the correct order:
1. Starts Redis (or detects if already running)
2. Activates the Python virtual environment
3. Starts a Celery worker in the background (logs to `/tmp/celery_worker.log`)
4. Starts FastAPI dev server in the foreground
5. Traps `Ctrl+C` to shut down the Celery worker on exit

### `stop.sh`

Stops all services gracefully:
- Kills any process on port 8000 (FastAPI)
- Stops Celery worker via saved PID file (with `pkill` fallback)
- Shuts down Redis

### `test.sh`

Automated test runner with multiple modes:

```bash
./test.sh              # Quick smoke tests (health + submit + concurrent)
./test.sh submit       # Submit a document and get the task_id
./test.sh status <id>  # Check status of a specific task
./test.sh full         # End-to-end: submit → poll every 15s → print result
./test.sh concurrent   # Submit 3 documents simultaneously
```

---

## Project Structure

```
├── main.py                 # FastAPI app — all API endpoints
├── db.py                   # SQLite database module (schema, CRUD operations)
├── agents.py               # 4 CrewAI agents with Gemini LLM configuration
├── task.py                 # 4 CrewAI task definitions
├── tools.py                # PDF reader tool (@tool) and SerperDevTool
├── celery_app.py           # Celery + Redis configuration
├── tasks_worker.py         # Celery task — runs CrewAI crew with retry logic
├── requirements.txt        # Pinned dependencies
├── financial_analyzer.db   # SQLite database (auto-created on startup)
├── start.sh                # Launch all services
├── stop.sh                 # Stop all services
├── test.sh                 # API test runner
├── data/                   # Uploaded PDFs (auto-created)
└── outputs/                # Output directory
```

---

## Bugs Found & Fixed

35 bugs were identified and fixed across all project files. They are categorized below.

### Dependency Conflicts (7 bugs) — `requirements.txt`

| # | Bug | Fix |
|---|-----|-----|
| 1 | `google-api-core==2.10.0` conflicted with `google-ai-generativelanguage` | Unpinned — let pip resolve compatible version |
| 2 | `opentelemetry-instrumentation==0.46b0` incompatible with `opentelemetry-api>=1.30.0` required by crewai | Unpinned |
| 3 | `pydantic_core==2.8.0` mismatched with `pydantic==2.6.1` (needs `pydantic-core==2.16.2`) | Unpinned |
| 4 | `openai==1.30.5` too old for `litellm 1.72.0` (needs `>=1.68.2`) | Unpinned |
| 5 | `protobuf==4.25.3` conflicted between google packages (`<5.0`) and opentelemetry (`>=5.0`) | Unpinned |
| 6 | `crewai-tools==0.76.0` incompatible with `crewai==0.130.0` (missing `crewai.rag` module) | Downgraded to `crewai-tools==0.47.1` |
| 7 | `embedchain` missing, required at import time by `crewai-tools==0.47.1` | Added `embedchain` to dependencies |

### Import Path Errors (8 bugs) — `agents.py`, `tools.py`, `task.py`

| # | File | Bug | Fix |
|---|------|-----|-----|
| 8 | `agents.py` | `from crewai.agents import Agent` — wrong submodule | `from crewai import Agent` |
| 9 | `agents.py` | `LLM` class not imported | Added `LLM` to crewai import |
| 10 | `agents.py` | `from tools import FinancialDocumentTool` — class no longer exists | `from tools import read_data_tool` |
| 11 | `tools.py` | `from crewai_tools.tools.serper_dev_tool import SerperDevTool` — wrong path | `from crewai_tools import SerperDevTool` |
| 12 | `tools.py` | `from crewai_tools import tools` — invalid import | Removed |
| 13 | `tools.py` | `from langchain.document_loaders import PyPDFLoader` — deprecated path | `from langchain_community.document_loaders import PyPDFLoader` |
| 14 | `task.py` | `from tools import FinancialDocumentTool` — class no longer exists | `from tools import read_data_tool` |
| 15 | `task.py` | `tools=[FinancialDocumentTool.read_data_tool]` on all 4 tasks | `tools=[read_data_tool]` |

### Tool Definition Errors (4 bugs) — `tools.py`

| # | Bug | Fix |
|---|-----|-----|
| 16 | `read_data_tool` was a class method, not a proper crewai tool | Refactored to standalone function with `@tool("Read Financial Document")` decorator |
| 17 | Missing `self` parameter in class method | Fixed by converting to standalone function |
| 18 | Function was `async` but crewai tools must be synchronous | Removed `async` keyword |
| 19 | Inconsistent indentation (docstring at 8-space, body at 4-space) | Fixed to consistent 4-space indent |

### LLM Configuration Errors (2 bugs) — `agents.py`

| # | Bug | Fix |
|---|-----|-----|
| 20 | `llm = llm` — self-referencing assignment | `llm = LLM(model="gemini/gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY"))` |
| 21 | `tool=[...]` (singular) on agent | `tools=[...]` (plural keyword) |

### Agent/Task Content Issues (8 bugs) — `agents.py`, `task.py`

| # | Bug | Fix |
|---|-----|-----|
| 22 | `financial_analyst` had unprofessional/harmful goal and backstory | Replaced with data-driven analysis prompts |
| 23 | `verifier` had unprofessional/harmful goal and backstory | Replaced with document verification and compliance prompts |
| 24 | `investment_advisor` had unprofessional/harmful goal and backstory | Replaced with balanced, SEC-compliant analysis prompts |
| 25 | `risk_assessor` had unprofessional/harmful goal and backstory | Replaced with risk management framework prompts (VaR, stress testing) |
| 26 | `analyze_financial_document` task had harmful description/expected_output | Rewritten for data-driven financial analysis |
| 27 | `investment_analysis` task had harmful description/expected_output | Rewritten for balanced, data-backed recommendations |
| 28 | `risk_assessment` task had harmful description/expected_output | Rewritten for proper risk evaluation with mitigation strategies |
| 29 | `verification` task had harmful description/expected_output | Rewritten for document classification and validation |

### Configuration & Architectural Bugs (6 bugs) — `agents.py`, `main.py`, `task.py`

| # | Bug | Fix |
|---|-----|-----|
| 30 | `max_iter=1` on all agents — only 1 iteration means agents can't reason | Changed to `max_iter=15` |
| 31 | `max_rpm=1` on all agents — 1 request/min makes agents unusable | Changed to `max_rpm=10` |
| 32 | `Crew` only included `financial_analyst` agent, ignoring other 3 | Added all 4 agents to the Crew |
| 33 | `Crew` only included 1 task, ignoring other 3 | Added all 4 tasks to the Crew |
| 34 | `file_path` not passed to crew inputs — agents didn't know which file to read | Added `file_path` to crew `inputs` dict |
| 35 | `async def analyze_financial_document(...)` endpoint name shadowed the imported task | Renamed to `analyze_document_endpoint` |

---

## Bonus Features

### 1. Queue Worker Model (Celery + Redis)

The original implementation ran CrewAI agents synchronously inside the FastAPI request handler, blocking the server for minutes per request. This was replaced with a **Celery + Redis** async task queue:

- **Non-blocking**: `POST /analyze` returns a `task_id` in ~100ms instead of blocking for 2-5 minutes
- **Concurrent**: Multiple documents can be analyzed simultaneously
- **Retry logic**: Gemini free-tier rate limits (5 req/min) are handled with exponential backoff (60s → 120s → 240s, up to 3 retries)
- **File cleanup**: Uploaded PDFs are automatically deleted after processing (success or failure)
- **Result persistence**: Analysis results are stored in Redis for 1 hour

| File | Purpose |
|------|---------|
| `celery_app.py` | Celery configuration — Redis as broker and result backend, `task_acks_late=True` for reliability |
| `tasks_worker.py` | Celery task wrapping the CrewAI crew execution with rate-limit retry and file cleanup |

### 2. Database Integration (SQLite)

Added a local SQLite database for persistent storage of analysis results and user data. Unlike Redis (which expires results after 1 hour), the database provides permanent history.

**Database Schema:**

```
┌──────────────┐         ┌────────────────────┐
│    users     │         │     analyses       │
├──────────────┤         ├────────────────────┤
│ id (PK)      │◄───┐    │ id (PK)            │
│ username     │    └────│ user_id (FK, null)  │
│ email        │         │ task_id (unique)    │
│ created_at   │         │ filename            │
└──────────────┘         │ file_size           │
                         │ query               │
                         │ status              │
                         │ analysis            │
                         │ error               │
                         │ created_at          │
                         │ completed_at        │
                         └────────────────────┘
```

**Key Features:**
- **Persistent history**: All analyses are stored permanently (not just 1 hour like Redis)
- **User tracking**: Optionally associate analyses with users via `user_id`
- **Aggregate stats**: `GET /analyses/stats` returns success/failure counts and total bytes processed
- **Filtering & pagination**: Query by user, status, with `limit`/`offset`
- **WAL mode**: SQLite uses Write-Ahead Logging for concurrent read access from FastAPI and Celery
- **Foreign keys**: User-analysis relationship with `ON DELETE SET NULL`
- **Zero dependencies**: Uses Python's built-in `sqlite3` module — no extra packages
- **Dual-write**: Both the Celery worker and the `/status` endpoint sync results to the DB

| File | Purpose |
|------|---------|
| `db.py` | Database module — schema creation, connection management, all CRUD operations |

---

## Notes

- **Gemini free tier** is limited to 5 requests/minute. With 4 agents, a single analysis can trigger rate limits. The Celery worker retries automatically with exponential backoff.
- **PDF files** uploaded via the API are saved to `data/` and cleaned up after analysis completes.
- The `SERPER_API_KEY` is optional — the web search tool will simply not return results without it.
- **SQLite database** (`financial_analyzer.db`) is auto-created on first startup. Delete it to reset all stored data.
- **User accounts** are lightweight (username + optional email) with no authentication — intended for tracking, not security.
