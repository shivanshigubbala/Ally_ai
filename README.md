# Ally AI

Ally AI is a research/prototype repository implementing a lightweight virtual
receptionist and doctor consultation flow driven by a FastAPI backend, a
Next.js frontend, and small reference services. The system demonstrates a
conversation routing graph, RAG-backed doctor agents, and simple lab report
generation for demonstration and experimentation only.

This repository is documentation-first for Phase 0. No production guarantees
are intended and several clinical features are intentionally stubbed.

## Project Overview

- Receptionist collects symptoms and routes users to a doctor agent.
- General Physician agent performs focused questioning with retrieval-augmented
  grounding and can recommend stubbed lab tests that generate downloadable
  PDF reports.
- Knowledge is stored as embeddings in Postgres with pgvector and used for RAG.

## Technology Stack

- Backend: Python (FastAPI)
- Frontend: Next.js (React, TypeScript)
- Database: PostgreSQL + pgvector
- Embeddings / LLM: NVIDIA NIM (configurable via env)
- Messaging: WebSocket-based chat (FastAPI)
- Orchestration: Docker Compose for dev and service composition

## Current Folder Structure (top-level)

- `backend/` — FastAPI app, graphs, RAG, ingest, models, and utilities
- `frontend/` — Next.js web UI (separate app inside the repo)
- `knowledge/` — source PDFs and knowledge for RAG (e.g. WHO manual)
- `services/` — reference Go services (appointment, lab)
- `docs/` — design notes and progress logs
- `docker-compose.yml` — compose for postgres, backend, appointment service
- `chat_cli.py` — minimal WebSocket CLI client for interactive sessions

## Backend Overview

- Entrypoint: `backend/main.py` (FastAPI app, HTTP and WebSocket endpoints)
- Graphs: `backend/graphs/` contains the receptionist routing graph and the
  general physician graph used to run agent flows.
- RAG: `backend/rag/` contains retriever logic; `backend/ingest/` contains PDF
  extraction, chunking, and embedding upload scripts.
- LLM integration: `backend/llm/` contains `nvidia_client.py`, `embeddings.py`,
  and `prompts.py` with grounding system prompts for doctor agents.
- Persistence: `backend/db/pgvector_tracker.py` tracks `users`, `messages`, and
  `knowledge_chunks` in Postgres/pgvector.
- In-memory services: `backend/services/local_store.py` contains demo
  departments, doctors, and slot data used by the receptionist flow.

## Frontend Overview

- Built with Next.js (app router). UI files live under `frontend/app`,
  components under `frontend/components`, and client code under `frontend/lib`.
- The frontend connects to the backend WebSocket at `/ws/{user_id}` to drive
  conversational flows and reacts to domain events (`slot_select`,
  `lab_notification`, `report_ready`).
- Authentication is not implemented; the UI assumes a session `user_id` for
  demonstration only.

## AI Agents

- Receptionist agent (routing graph) — located in
  `backend/graphs/routing_graph.py`. Collects symptoms and offers slots.
- General Physician agent — `backend/graphs/general_physician_agent.py`.
  Uses a retrieval step to inject relevant passages and applies grounding
  rules via `backend/llm/prompts.py`.
- Cardiology agent scaffolding exists under `backend/agents/` but is not the
  default routing target; specialist routing is not yet wired.

How agents communicate

- Agents run inside the backend process and emit WebSocket domain events to
  the client. The WebSocket protocol and Pydantic models are defined in
  `backend/models/session_state.py` and `backend/ws/router.py` implements
  dispatch.

Data consumed / produced

- Consume: user messages, selected slot decisions, retriever passages (from
  `knowledge_chunks`), and environment-configured LLMs.
- Produce: streaming or complete assistant messages, domain events
  (`slot_select`, `lab_notification`, `report_ready`), and persisted
  conversation messages.

## Current Departments

- General Physician (default)
- Cardiology (resolved through the shared specialty dispatcher and registry)

## Specialty Dispatcher and Registry

- The canonical dispatcher lives in `backend/specialties/dispatcher.py`.
- It accepts a consultation context, reads the selected department, asks the
  registry for the matching specialty implementation, and returns that
  specialty instance.
- The registry in `backend/specialties/registry.py` is now the single routing
  authority for specialty selection.
- General Physician and Cardiology are registered today; unknown departments
  fail gracefully with a registry error instead of auto-fallback.
- Adding a new department only requires creating an adapter and registering it
  in the registry; the dispatcher remains unchanged.

## Available APIs

- WebSocket chat: `/ws/{user_id}` — primary conversational interface.
- Report download: `/reports/{report_id}` — serves generated PDF reports
  produced by backend report generation to `backend/reports/`.
- Additional internal HTTP endpoints exist in `backend/main.py` for
  diagnostics and model testing; consult the file for details.

## Database Overview

- Postgres with `pgvector` extension stores:
  - `users` (demo user records handled by `pgvector_tracker`)
  - `messages` (conversation history persisted for session state)
  - `knowledge_chunks` (embedded RAG passages)
- See `backend/db/pgvector_tracker.py` for code that interacts with these
  tables. The repository does not include migration scripts beyond the
  `migrations/` folder and standard Alembic layout.

## Docker Overview

- `docker-compose.yml` composes the primary services used in local dev:
  - `postgres` (with pgvector)
  - `backend` (FastAPI Python service)
  - `appointment` (Go reference service)
- `docker-compose.checks.yml` is provided for CI-like checks and runs tests
  inside a reproducible image.
- Volumes: Postgres data volume is defined in the compose file for persistence
  between runs (see the compose file for exact names).

## Environment Variables

Required:
- `NVIDIA_API_KEY` — NVIDIA NIM API key used for LLM and embedding calls.

Common optional overrides (have defaults in code or `.env.example`):
- `NVIDIA_MODEL`, `NVIDIA_EMBED_MODEL`, `NVIDIA_BASE_URL`,
- `POSTGRES_*` connection variables

## Current Features

  responses, and grounding rules.

## Patient Registration (Phase 1B)
- A backend-backed patient registration endpoint `/register` was added. The
  endpoint validates required fields, generates a permanent `patient_id`,
  persists the patient profile in Postgres (`users` table), creates an
  initial session, and returns the `patient_id` and `session_id` to the
- Patient ID format: `PAT-<YEAR>-XXXXXX` (example: `PAT-2026-000001`). IDs are
- Frontend signup (`frontend/app/signup/page.tsx`) now calls the backend
## Patient Registration (Phase 1B Revision)

- The registration flow has been revised to make `Patient` the root identity
  and to remove any login or authentication steps. The intended flow is:

  Landing Page

  ↓

  Patient Registration

  ↓

  Patient Created

  ↓

  Session Initialized

  ↓

  Ally (Receptionist)

  ↓

  Doctor Selection

- No login, authentication, or dashboard is used. Registration is the only
  entry point.

- The backend `/register` endpoint now:
  - Accepts only identity fields (name, age, gender, phone, city, consent).
  - Generates an internal UUID-backed session id (distinct from the patient id).
  - Generates a human-readable `patient_id` of the form `PAT-<YEAR>-XXXXXX`.
  - Persists the patient record in Postgres (`users` table) and creates an
    initial `sessions` row linking the session to the patient.

- Frontend `signup` now posts only identity info, initializes the session,
  and opens the Ally conversation directly (no login). Session identifiers
  are stored transiently in `sessionStorage` (not permanent `localStorage`).
  registration API and stores the returned `patientId` in local storage.

## Current Limitations
  routing is to the General Physician.
- Lab services are stubbed and do not represent real lab integrations.
- No authentication or user management; sessions are identified by `user_id`
  for demonstration only.

## Shared Notification Framework

- A canonical internal notification model is available in `backend/models/notification.py`.
- The model carries `notification_id`, `patient_id`, `internal_uuid`,
  `appointment_id`, `consultation_context_id`, `department`, `doctor`,
  `notification_type`, `title`, `message`, `metadata`, `status`,
  `created_at`, `read_at`, and `version`.
- Supported statuses are `PENDING`, `DELIVERED`, `READ`, and `FAILED`.
- Supported types are `APPOINTMENT`, `LAB`, `REPORT`, `CONSULTATION`, and
  `GENERAL`.
- Persistence helpers in `backend/general_physician/db/pgvector_tracker.py`
  add `create_notification()`, `get_notifications()`, and `mark_read()`
  using the existing Postgres-backed storage layer.
- The current workflow is accepted lab -> create persisted notification -> stop.
  No delivery path, WebSocket push, email, SMS, or frontend implementation is
  included in this phase.

## Patient Timeline & Longitudinal History

- A canonical patient timeline model is available in `backend/models/timeline.py`.
- The timeline is the permanent longitudinal medical history for the patient,
  separate from conversation memory, OKF, or RAG retrieval.
- The top-level timeline carries `timeline_id`, `patient_id`, `internal_uuid`,
  `version`, `created_at`, `updated_at`, and a `history` array.
- Each history entry contains `entry_id`, `appointment_id`,
  `consultation_context_id`, `department`, `doctor`, `visit_date`,
  `chief_complaint`, `clinical_summary`, `assessment`,
  `recommended_tests`, and `status`.
- Persistence helpers in `backend/general_physician/db/pgvector_tracker.py`
  add `get_patient_timeline()`, `append_timeline_entry()`, and
  `load_patient_history()` using the existing Postgres-backed storage layer.
- Ownership follows the patient-first model: the patient owns the timeline,
  and each consultation-derived entry is appended to that shared history for
  future departments to reuse.

## Consultation Orchestration (Phase 3)

A lightweight consultation handoff has been introduced between the receptionist booking flow and the doctor-ready state. The backend now creates a canonical consultation context as soon as an appointment is confirmed, persists it with the appointment and session identifiers, and exposes the context state through the existing WebSocket handoff payload.

- Canonical object: `backend/models/intake.py` defines `ConsultationContext`.
- Persistence: `backend/general_physician/db/pgvector_tracker.py` stores consultation contexts in a `consultation_contexts` table.
- Appointment integration: appointment records now carry a `consultation_context_id` reference when available.
- Lifecycle: consultation status is prepared as `CREATED` and is surfaced as `consultation_status` in the appointment-ready event.
- Frontend: the appointment panel now displays the selected department and pending consultation status without starting the doctor chat.

## Known Issues

- Some large PDF pages can exceed embedding token limits and are skipped
  during ingest (documented in README ingest steps).
- This is a prototype — prompts and guardrails are experimental and should
  not be used for clinical decision-making.

## Development Roadmap (high level)

- Phase 0 — Documentation and architecture lock (this repository state).
- Phase 1 — Patient Foundation: add persistent patient records and secure
  authentication.
- Phase 2 — Specialist routing: enable cardiology and neurology agents.
- Phase 3 — Lab integration: connect real lab services and improve report
  fidelity.

## Next Recommended Phase

Patient Foundation — establish patient data model, secure auth, and stable
session handling before adding more clinical features.

---

For design notes and progress, see `docs/BACKEND_PROGRESS.md`.

This README was updated as part of Phase 0 documentation work.