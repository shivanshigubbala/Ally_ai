# Ally AI — Architecture

This document describes the current architecture of the repository as of
Phase 0 (documentation lock). It reflects implemented code and wiring only —
no planned or future features are described as implemented.

## Overall System

High-level flow:

Frontend (Next.js UI)
↓
Backend (FastAPI)
↓
Database (Postgres + pgvector)
↓
AI Agents (in-backend graphs)
↓
Knowledge Bases (embedded passages in `knowledge_chunks`)
↓
Documents (PDF reports generated to `backend/reports/`)
↓
Notifications (WebSocket domain events)

All agent execution and orchestration runs inside the FastAPI backend. The
frontend communicates primarily over a WebSocket endpoint for conversational
flows; report assets are served over standard HTTP endpoints.

## Current User Flow

The implemented user flow (what currently exists in code):

1. Registration / session: demo sessions are identified by a `user_id` (no
   persistent auth implemented).
2. Receptionist (Ally) greets the user and collects symptoms using the
   routing graph (`backend/graphs/routing_graph.py`).
3. Doctor selection: receptionist logic (in-memory local_store) suggests a
   doctor and available slots; user selects a slot via a `select` event.
4. Consultation: selected doctor graph (General Physician by default)
   performs a turn-based consultation. The doctor may stream `text_delta`
   events for progressive responses.
5. Summary / lab recommendation: after questioning the doctor may emit a
   `lab_notification` event. If accepted, a stubbed report generation path can
   create a PDF and emit `report_ready`.

This flow is implemented using a WebSocket protocol and Pydantic models under
`backend/models/session_state.py` and is orchestrated by `backend/ws/router.py`.

## AI Agent Architecture

Agents are implemented as code graphs that run inside the backend process.

- Receptionist
  - Location: `backend/graphs/routing_graph.py`.
  - Purpose: collect chief complaint and symptoms, present slots, route to
    a doctor agent.
  - Data consumed: user messages, `local_store` department/slot data.
  - Data produced: slot proposals (`slot_select`), selected doctor events.

- General Physician
  - Location: `backend/general_physician/agent.py`.
  - Purpose: perform focused clinical questioning using retrieval-augmented
    grounding. The system prompt enforces that the agent must ground
    assertions in retrieved passages.
  - Data consumed: user turns, retrieved passages from `knowledge_chunks`,
    conversation history from `messages` table.
  - Data produced: streaming or full-text assistant messages, `lab_notification`,
    persisted message records.

- Cardiology
  - Location: `backend/cardiology/agent.py` (wired via specialties registry).
  - Status: agent exists and is registered; runs cardiology consultation graph.


How they communicate

- Agents call the NVIDIA NIM client in `backend/llm/nvidia_client.py` for
  model interactions. The backend emits WebSocket envelope messages to the
  frontend; events are routed in `backend/ws/router.py`.

## Backend Architecture

- Services: small service modules exist under `backend/services/` (e.g.
  `local_store.py` for demo departments/slots).
- Routers: `backend/ws/router.py` provides WebSocket dispatch. Other HTTP
  endpoints live in `backend/main.py`.
- Specialty dispatch: `backend/specialties/dispatcher.py` provides a single
  canonical entry point that resolves a consultation context to a specialty
  implementation. It reads the department from the consultation context, asks
  `backend/specialties/registry.py` for the matching specialty, and returns the
  resolved specialty instance.
- Registry flow: the registry owns all department-to-specialty mappings. The
  current registrations cover General Physician and Cardiology. Unknown
  departments raise a registry error and do not fall back automatically.
- Resolution lifecycle: appointment/consultation context -> dispatcher ->
  registry -> specialty instance -> specialty run method. This keeps routing
  logic centralized and ensures new departments can be onboarded by adapter
  creation plus registration only.
- Models: Pydantic session and message shapes are in
  `backend/models/session_state.py` and the persistence layer for RAG and
  messages is in `backend/db/pgvector_tracker.py`.
- Utilities: ingest utilities (`backend/ingest/`) for PDF extraction,
  chunking, and embedding upload.
- Configuration: environment variables control LLM and DB endpoints; see
  `.env.example` and `README.md`.

Data flow summary

- Ingest pipeline: PDFs -> `backend/ingest/extract_pdf.py` -> pages jsonl ->
  chunker -> chunks jsonl -> `backend/ingest/embed_store.py` -> inserts into
  `knowledge_chunks` (pgvector).
- Runtime: user WebSocket -> agent graph -> LLM calls -> responses + optional
  retriever hits inserted into prompts -> persisted messages + client events.

## Frontend Architecture

- Pages: `frontend/app` contains app routes and pages.
- Components: UI components grouped under `frontend/components`.
- State management: the frontend holds transient UI state and connects to the
  backend via WebSocket for conversational state. There is no backend-backed
  authentication/state beyond the `user_id` used for sessions.
- API flow: UI opens WebSocket to `/ws/{user_id}` and listens for domain
  events and streaming deltas; HTTP endpoints are used for report downloads.

## Database

Entities implemented (existing tables and interactions):

- `users` — demo user records (managed via tracker functions in code).
- `messages` — persisted conversation turns (user and assistant).
- `knowledge_chunks` — embedded passages used by the retriever for RAG.

Relationships

- `messages` are associated with a `user_id` and form the conversation history
  for that session. `knowledge_chunks` are external to user sessions and used
  only for retrieval; there is no direct FK relationship in code other than
  lookup by similarity.

Do not attempt any schema changes during Phase 0.

## Docker

Containers and services in `docker-compose.yml` (dev composition):

- `postgres` — Postgres with `pgvector` extension; stores RAG embeddings and
  messages.
- `backend` — FastAPI service container (optional; local Python run supported).

## Patient Registration (Phase 1B Revision)

Implemented elements:

- Backend helpers in `backend/general_physician/db/pgvector_tracker.py`:
  - `create_patient(...)` — generates a stable patient id (`PAT-<YEAR>-XXXXXX`)
    and persists the profile into the `users` table with minimal identity JSON.
  - Migration helpers used for demo client-side ids were removed to keep the
    registration flow simple and deterministic.
- REST endpoint: `POST /register` (implemented in
  `backend/general_physician/main.py`) — validates required identity fields
  (including consent), creates the patient record, creates an initial
  session (session id is a distinct UUID-based id), and returns `patient_id`
  and `session_id` to the client.
- Frontend: `frontend/app/signup/page.tsx` posts only identity information to
  `/register`. On success the frontend initializes the chat flow and opens
  Ally directly; transient session identifiers are stored in `sessionStorage`.

Notes and constraints:

- Only minimal DB changes were made (no schema redesign). The existing
  `users`, `sessions`, `messages`, and `uploaded_files` tables are reused.
- The registration flow intentionally does not implement authentication,
  login, or authorization — session handling and security are planned for
  a later phase.
- `appointment` — Go reference appointment service used in examples.

Volumes: Postgres data volume is defined in compose; see the compose file for
exact names.

Startup flow (what repository documents):

1. Start Postgres.
2. Optionally run ingest scripts to populate `knowledge_chunks`.
3. Start backend (docker or local Python) and connect front-end or CLI.

## Current RAG Flow

- Extraction: `backend/ingest/extract_pdf.py` extracts pages into a JSONL.
- Chunking: `backend/ingest/chunker.py` produces paragraph-aware chunks.
- Embedding: `backend/ingest/embed_store.py` calls NVIDIA embedding model and
  inserts vectors into `knowledge_chunks`.
- Retrieval: `backend/rag/retriever.py` performs cosine search returning top-N
  passages to inject into doctor prompts.

## Current Knowledge Base Flow

- Knowledge source files live in `knowledge/`; the canonical example is the
  WHO manual under `knowledge/general_physician/who_dcm_vol2.pdf`.
- The ingest scripts are manual, file-driven utilities that produce JSONL
  artifacts and upload embeddings to Postgres/pgvector.

## Current Appointment Flow

- Appointment/bookings are simulated using demo data in
  `backend/services/local_store.py` and a reference Go appointment service in
  `services/appointment/` (used by compose in examples). The receptionist
  proposes slots from the in-memory store and the frontend simulates
  selection via WebSocket `select` events.

## Current Notification Flow

- Notifications between backend and client are implemented as WebSocket
  domain events (`slot_select`, `lab_notification`, `report_ready`). The
  backend emits these events from agent graphs and the frontend listens and
  updates UI accordingly.

## Shared Notification Framework

- The backend now exposes a canonical internal notification object in
  `backend/models/notification.py`.
- It is intentionally separate from user-facing messaging and is persisted as
  a reusable object for downstream modules rather than emitted over the
  WebSocket transport.
- Persistence helpers live in `backend/general_physician/db/pgvector_tracker.py`
  and support creating, listing, and marking notifications as read without
  changing the underlying database shape beyond adding a `notifications`
  table used by the existing Postgres connection layer.
- The workflow is currently: accepted lab request -> create persisted
  notification -> stop. No delivery path is implemented yet.

- WebSocket payloads: the existing `doctor_ready` event now includes `consultation_status` and department metadata for the appointment panel.

## Patient Timeline & Longitudinal History

- The backend now exposes a canonical patient timeline in
  `backend/models/timeline.py`.
- The timeline is anchored to the patient as the root entity and stores a
  chronological history of completed consultations rather than chat memory.
- Persistence helpers in `backend/general_physician/db/pgvector_tracker.py`
  support creating and reading the timeline and appending consultation-derived
  history entries without changing the consultation context model.
- The ownership model is patient -> timeline -> history entries -> consultations -> reports/notifications.
- Future departments can append to the same timeline using the same helper.

## Current Limitations (honest list)

- Basic authentication only (email lookup/registration with patient ID flow; no passwords, JWT tokens, or secure session cookies).
- Lab service integration is stubbed; Go service is integrated for booking, but report generation relies on best-effort microservice webhooks and stubs.
- The system is experimental and prompts/guardrails are not clinically validated.

---

This file reflects the current system architecture and has been updated to reflect active routing and persistence features.
