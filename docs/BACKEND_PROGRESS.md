# Backend Progress Log

Working notes for the Ally AI Python backend. Intended as an evolving design
journal so anyone touching this code can understand why things are the way they
are.

---

## Current state (June 2026)

The Python backend is now the canonical runtime. The Go services in
`services/appointment/` and `services/lab/` are reference implementations kept
for parity but not exercised by the WebSocket flow.

The doctor is grounded in the WHO IMAI District Clinician Manual Vol. 2
(`knowledge/general_physician/who_dcm_vol2.pdf`) via pgvector retrieval, and
streams its responses token-by-token.

---

## Recent changes

### RAG pipeline over WHO DCM Vol. 2

**Files added**
- `backend/ingest/extract_pdf.py` - PyMuPDF page extractor.
- `backend/ingest/chunker.py` - ~400-word paragraph-aware chunker with 80-word overlap.
- `backend/ingest/embed_store.py` - NVIDIA `nv-embedqa-e5-v5` embedder, batches of 16,
  char-capped at 1200 per chunk to stay under the 512-token model limit.
- `backend/llm/embeddings.py` - shared embed client (`embed_passages`, `embed_query`).
- `backend/rag/retriever.py` - runtime retriever: takes last 3 user turns,
  embeds them as a query, pulls top-5 from pgvector, formats with
  `[Excerpt N - source p.X sim=Y]` headers, returns <=3500 chars.

**Files changed**
- `backend/db/pgvector_tracker.py` - added `knowledge_chunks` table
  (`vector(1024)`), plus `insert_knowledge_chunks`, `count_knowledge_chunks`,
  `search_knowledge`.
- `backend/llm/prompts.py` - added `DOCTOR_SYSTEM_PROMPT` with the strict
  grounding rule and `{rag_context}` injection.

**Why**: prior to this the doctor was free-form Llama 8B with no clinical
reference. It hallucinated differential diagnoses and asked inappropriate
questions (e.g. STIs for a fever/cough patient). Grounding in real WHO
guidelines constrains it.

**Tuning notes**
- `min_similarity=0.40` primary, with a one-shot fallback to `0.30` if the
  primary returns zero rows. Tuned from `0.20` to avoid noisy retrieved
  passages overwhelming the prompt.
- ~96 of 1123 chunks are skipped during ingest because they exceed 512 tokens
  (TOC/index pages). Acceptable.

### Grounding rule + relevance gate

**Files changed**
- `backend/llm/prompts.py` - `DOCTOR_SYSTEM_PROMPT` now includes:
  - `CRITICAL GROUNDING RULE` (only state facts supported by retrieved context)
  - `RELEVANCE CHECK` (skip excerpts unrelated to the patient's
    `{chief_complaint}`, even if no other excerpts are available)
- `backend/models/session_state.py` - added `chief_complaint: str` field on
  `DoctorState`.
- `backend/graphs/general_physician_agent.py`:
  - `session_init` captures `chief_complaint` once at session start (from the
    first user message; if empty, falls back to the most recent prior user
    message from the routing phase).
  - Both `session_init` and `questioning` pass `chief_complaint` into
    `DOCTOR_SYSTEM_PROMPT.format(...)`.

### Doctor streaming

**Files changed**
- `backend/llm/nvidia_client.py` - added `stream_chat()` that yields token
  chunks via `stream=True`. Logs time-to-first-token.
- `backend/graphs/general_physician_agent.py` - `session_init` and
  `questioning` now stream via `_stream_into_emit()`, which yields
  `text_delta` events to the WebSocket and falls back to non-streaming
  `chat()` on failure.
- `backend/models/session_state.py` - added `text_delta` to `WSEventType`.
- `chat_cli.py` - renders `text_delta` events in place using
  `print(..., end="", flush=True)`, and `break`s after the final `text` event
  so the outer loop prompts the user for next input.

### Crash isolation

**Files changed**
- `backend/graphs/general_physician_agent.py` - `session_init` and
  `questioning` wrap their LLM calls in `try/except`. On exception they log
  via `logger.exception(...)` and fall back to a safe reply; the exception
  never propagates to the WebSocket layer.
- `backend/ws/router.py` - per-message dispatch wrapped in `try/except`. On
  exception: log full traceback, send a graceful `text` event back to the
  client, `continue` the loop. Only `WebSocketDisconnect` closes the
  connection.

### CLI non-blocking I/O

**Files changed**
- `chat_cli.py` - replaced every blocking `input()` with
  `await asyncio.get_event_loop().run_in_executor(None, input, ...)`. Added
  `_drain_pending(ws)` to consume any buffered WS frames after each turn so
  the connection doesn't time out while the user is reading.

### Renamed Dr. Alex Rivera -> Dr. Shankar

**Files changed**
- `backend/graphs/routing_graph.py` (`GP_DOCTOR_NAME`).
- `backend/graphs/general_physician_agent.py` (`DOCTOR_NAME` from
  `backend.llm.prompts`).
- `backend/services/local_store.py` (seeded doctor).
- `chat_cli.py` (banner + prompt labels).

### Receptionist non-streaming LLM responses

The slot-confirm and booking-confirm prompts go through the LLM (not templates)
so the receptionist's tone matches the doctor's. Streaming is intentionally
**off** for the receptionist per design choice.

---

## Architectural decisions

### Why LangGraph `_NODE_FNS` table over the compiled graph

`routing_graph.py` looks like a LangGraph state machine, but `run_step` ignores
the compiled `_graph` edges and dispatches manually via the `_NODE_FNS` table.
This is intentional - it gives us tight control over loop termination
(`prev_node == current_node` detection) and avoids LangGraph's autosave
semantics fighting our state.

### Why dual imports (`backend.X` and `X`)

`backend/Dockerfile` puts `main.py` at `/app/main.py` so in-container import
names are `db`, `llm`, `rag`, `ws`, `graphs` (no `backend.` prefix). The
local-dev path (`$env:PYTHONPATH = "."`) makes `backend` the top-level
package. Every backend module uses the `try: from backend.X except: from X`
pattern so both paths work. **This pattern is mandatory for new modules.**

### Why a custom retriever instead of LangChain

The retriever is small (~80 lines) and bespoke: it formats excerpts with
provenance headers (`[Excerpt N - source p.X sim=Y]`) which the prompt relies
on for the doctor to cite / evaluate. LangChain's stock retrievers didn't fit.

### Why two routing graphs

`routing_graph.py` handles booking. `general_physician_agent.py` handles the
clinical consultation. They share `DoctorState`-style checkpoints via
LangGraph's `MemorySaver` keyed by user_id and appointment_id respectively.
They're separate because their state shapes are different.

---

## Known issues / sharp edges

### `intent_node` runs twice on the first WS connect

When the user first connects, `run_step` runs `GREETING` then
`INTENT_CLASSIFICATION`. INTENT_CLASSIFICATION doesn't emit anything (it waits
for symptoms), so the outer loop sees `prev_node == current_node` and breaks.
This is correct but the iteration count looks weird in logs (`iters=3`).

### `booking_node` doesn't re-read `pending_event`

`booking_node` reads `state.message_history` (last user message) instead of
`state.pending_event`. This means typing `s1` again in the BOOKING_CONFIRMATION
state produces a "didn't clearly confirm" reply because `s1` has no
confirm/cancel keywords. Could be tightened to also inspect `pending_event`.

### Streamed deltas can outpace a slow CLI

Even with `_drain_pending(ws)`, if the CLI blocks on stdin for >20s, the
WebSocket keepalive (default ~20s) can fire and close the connection. We
upgraded the CLI to use `run_in_executor` so this shouldn't happen anymore.
Watch for `received 1011 (internal error) keepalive ping timeout` in the
backend logs as a tell.

### 8B model on the free NIM tier

Llama 3.1 8B Instruct on `integrate.api.nvidia.com` has cold-start latency
(~0.5-2s time-to-first-token) and is rate-limited. For richer clinical
reasoning, swap to 70B via `NVIDIA_MODEL=meta/llama-3.1-70b-instruct` in
`.env`.

---

## Build / run / test cheat sheet

```powershell
# Cold start
cd C:\Users\ChinthalapudiBhargav\Downloads\ally_ai\Ally_ai
copy .env.example .env
# edit .env with NVIDIA_API_KEY
pip install -r backend\requirements.txt
docker compose up -d postgres

# (one-time) build the knowledge base
python -m backend.ingest.extract_pdf "knowledge/general_physician/who_dcm_vol2.pdf" "knowledge\_pages.jsonl"
python -m backend.ingest.chunker "knowledge\_pages.jsonl" "knowledge\_chunks.jsonl"
python -m backend.ingest.embed_store "knowledge\_chunks.jsonl" "general"
Remove-Item "knowledge\_pages.jsonl","knowledge\_chunks.jsonl"

# Run the backend
docker compose up -d --build
# or, for faster iteration:
$env:PYTHONPATH = "."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Chat
$env:PYTHONPATH = "."
python chat_cli.py

# Verify
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content
docker exec ally_ai-postgres-1 psql -U allyai -d allyai -c "SELECT COUNT(*) FROM knowledge_chunks;"
docker compose logs -f backend
```

---

## Things to revisit

- Specialist routing (the receptionist currently always books the GP).
- Persistent auth / session tokens (currently any user_id is accepted).
- Real lab test integration (the lab service is currently a Go stub).
- Streaming on the receptionist turns too, for consistency.
- Tighten `booking_node` to inspect `pending_event` for slot-confirm replies.
- Add a `report` view that consumes `report_ready` events and renders the
  lab results back to the user.