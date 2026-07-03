# Ally AI

Ally AI is a prototype hospital assistant demonstrating a receptionist and
doctor consultation flow driven by a routing graph and LLMs. It shows how a
lightweight virtual receptionist can collect symptoms, book appointments,
handoff to a focused doctor agent, and optionally recommend lab tests that
produce downloadable reports.

This repository includes a Next.js frontend, a FastAPI backend that runs the
routing/doctor graphs, and a small Go appointment service. The backend can
generate simple PDF lab reports to `backend/reports/` and serves them at
`/reports/{report_id}` so the frontend can offer downloads.

## What's wired up

- **Receptionist** (`backend/graphs/routing_graph.py`)
  Greets the patient, takes symptoms, books them with **Dr. Shankar** (GP),
  shows available slots, confirms the booking.
- **General Physician - Dr. Shankar** (`backend/graphs/general_physician_agent.py`)
  Asks one focused clinical question per turn for up to 10 turns, grounded in
  retrieved WHO excerpts. After 10 questions evaluates whether lab tests are
  warranted. Streams token-by-token so responses appear progressively.
- **RAG over WHO DCM Vol. 2** (`backend/rag/`, `backend/ingest/`)
  PDF at `knowledge/general_physician/who_dcm_vol2.pdf` is extracted, chunked
  (~400 words, 80-word overlap), embedded with NVIDIA `nv-embedqa-e5-v5`, and
  stored in the `knowledge_chunks` pgvector table. At each doctor turn the
  retriever pulls the top-5 most similar passages for the patient's chief
  complaint and injects them into the prompt.
- **Grounding guardrails** (`backend/llm/prompts.py`)
  The doctor system prompt includes a strict grounding rule: it may only state
  clinical facts, ask questions, or make recommendations supported by the
  retrieved context. If no retrieved excerpt relates to the chief complaint,
  it asks a general clarifying question instead of inventing.
- **Conversation memory** (`backend/db/pgvector_tracker.py`)
  Every user/assistant turn is persisted to the `messages` table; on the next
  visit the doctor sees prior context.
- **WebSocket chat** (`backend/ws/router.py`, `chat_cli.py`)
  FastAPI WebSocket at `/ws/{user_id}` driven by `chat_cli.py`. Supports
  `text`, `select`, `thinking` heartbeat, `text_delta` (streaming), and
  domain events (`slot_select`, `lab_notification`, `report_ready`).
- **Lab tests** (stubbed)
  On test recommendation the doctor emits `lab_notification`; the user accepts
  or rejects; a `report_ready` event closes the loop.
  Common general physician lab services in this project are Complete Blood Count
  (CBC) and Basic Metabolic Panel (BMP).

## Project structure

```
ally_ai/
├── chat_cli.py                       # interactive CLI client (WebSocket)
├── docker-compose.yml                # postgres (pgvector) + backend + appointment (Go)
├── .env.example                      # copy to .env; fill NVIDIA_API_KEY
├── backend/
│   ├── main.py                       # FastAPI app + /ws + /nv-test + /chat
│   ├── ws/router.py                  # WebSocket dispatcher
│   ├── graphs/
│   │   ├── routing_graph.py          # receptionist graph (LangGraph)
│   │   └── general_physician_agent.py # doctor graph with RAG + streaming
│   ├── rag/
│   │   └── retriever.py              # cosine search over knowledge_chunks
│   ├── ingest/
│   │   ├── extract_pdf.py            # PyMuPDF page extractor
│   │   ├── chunker.py                # ~400-word paragraph-aware chunker
│   │   └── embed_store.py            # nv-embedqa-e5-v5 -> pgvector
│   ├── llm/
│   │   ├── nvidia_client.py          # NVIDIA NIM chat + streaming
│   │   ├── embeddings.py             # NVIDIA NIM embeddings
│   │   └── prompts.py                # DOCTOR_SYSTEM_PROMPT with grounding rules
│   ├── db/pgvector_tracker.py        # pgvector: users, messages, knowledge_chunks
│   ├── services/local_store.py       # in-memory departments/doctors/slots
│   └── models/session_state.py       # Pydantic state shapes + WS envelope
├── knowledge/general_physician/
│   └── who_dcm_vol2.pdf              # WHO IMAI District Clinician Manual Vol. 2
├── services/                         # Go reference services (appointment, lab)
├── frontend/                         # Next.js UI (separate)
└── docs/                             # design + progress notes
```

## Quick start

### 1. Configure environment

```powershell
cd C:\Users\ChinthalapudiBhargav\Downloads\ally_ai\Ally_ai
copy .env.example .env
# Edit .env and paste your NVIDIA_API_KEY (required) and any other overrides
```

Required:
```env
NVIDIA_API_KEY=nvapi-...
```

Optional (defaults shown):
```env
NVIDIA_MODEL=meta/llama-3.1-8b-instruct   # swap to 70b for richer replies
NVIDIA_EMBED_MODEL=nvidia/nv-embedqa-e5-v5
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=allyai
POSTGRES_USER=allyai
POSTGRES_PASSWORD=allyai
```

### 2. Install Python deps

```powershell
pip install -r backend\requirements.txt
```

### 3. Start Postgres (pgvector)

```powershell
docker compose up -d postgres
```

### 4. (One-time) Build the RAG knowledge base

The PDF is already at `knowledge/general_physician/who_dcm_vol2.pdf`. To
populate `knowledge_chunks` in pgvector:

```powershell
python -m backend.ingest.extract_pdf "knowledge/general_physician/who_dcm_vol2.pdf" "knowledge\_pages.jsonl"
python -m backend.ingest.chunker "knowledge\_pages.jsonl" "knowledge\_chunks.jsonl"
python -m backend.ingest.embed_store "knowledge\_chunks.jsonl" "general"
Remove-Item "knowledge\_pages.jsonl","knowledge\_chunks.jsonl"
```

Expected: `inserted 1027 chunks for 'general'` (a few outliers exceed the
512-token embed limit and are skipped - typically TOC/index pages).

Verify:
```powershell
docker exec ally_ai-postgres-1 psql -U allyai -d allyai -c "SELECT COUNT(*) FROM knowledge_chunks;"
```

### 5. Start the backend

Two options - choose one:

**Option A - Full docker compose** (mirrors production):
```powershell
docker compose up -d --build
docker compose logs -f backend
```

**Option B - Local Python backend + Docker Postgres** (faster iteration):
```powershell
# terminal 1
docker compose up -d postgres
$env:PYTHONPATH = "."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# terminal 2
$env:PYTHONPATH = "."
python chat_cli.py
```

### 6. Chat

```powershell
$env:PYTHONPATH = "."
python chat_cli.py
```

Suggested test symptoms:
- *"fever, cough and difficulty breathing for 3 days, severe headache"*
- *"sharp chest pain on the left side when I breathe in, started yesterday"*
- *"watery diarrhea for 2 days with mild stomach cramps"*

## Configuration knobs

| Env var | Default | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | - | Required. NVIDIA NIM auth. |
| `NVIDIA_MODEL` | `meta/llama-3.1-8b-instruct` | Chat model. Use `meta/llama-3.1-70b-instruct` for richer replies (slower). |
| `NVIDIA_EMBED_MODEL` | `nvidia/nv-embedqa-e5-v5` | Embedding model. Asymmetric - requires `input_type` per request. |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | NIM endpoint. |

## WebSocket protocol (summary)

Server -> client `WSEvent` types:
- `text` - complete message (`{content, from?}`)
- `text_delta` - streaming token chunk (`{delta, from}`) - doctor turns only
- `thinking` - heartbeat so client knows the server is working (`{content}`)
- `doctor_select` / `slot_select` / `lab_notification` - domain events
- `report_ready` - session complete

Client -> server `ClientEvent` types:
- `text` - `{content}` (anything not a structured choice)
- `select` - `{target, id}` (slot) or `{target, decision}` (lab)

See `backend/models/session_state.py` for the Pydantic shapes.

## Known limitations / TODOs

- Specialist routing (cardiology / neuro / etc.) is a TODO - default is GP.
- Lab tests are stubbed - no real lab service integration.

## Checks and tests (Docker-only for CI-style checks)

This repo supports running tests locally (fast) and running Docker-based checks (CI-like).

- Run tests locally (recommended for development):

```powershell
make test
```

- Run checks inside Docker (reproducible image-based checks):

```powershell
make docker-checks
# or
docker compose -f docker-compose.checks.yml up --build --abort-on-container-exit --exit-code-from backend-checks
```

Notes:
- `docker-compose.checks.yml` builds the backend image (no host volume mounts) and runs the test suite, then exits with the test exit code.
- Use Docker only for checks to keep local iteration fast and simple.

- Streaming only on doctor turns; receptionist uses non-streaming `chat()`.
- No persistent auth - any user_id is accepted.

See `docs/BACKEND_PROGRESS.md` for the running changelog and design notes.