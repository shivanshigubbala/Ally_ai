## Phase 4 — Unified Specialty Dispatcher

Status

Completed (implementation and documentation only; no runtime validation executed)

Summary

Introduced a canonical specialty dispatcher and routed consultation execution
through the specialty registry instead of direct specialty lookup. General
Physician remains unchanged as the existing adapter, Cardiology continues to
use its own controller through the new adapter, and unknown departments now
fail gracefully.

Files Modified

- backend/specialties/dispatcher.py
- backend/specialties/__init__.py
- backend/specialties/registry.py
- backend/specialties/cardiology/consultation_controller.py
- backend/general_physician/ws/router.py
- backend/general_physician/tests/test_specialty_framework.py
- README.md
- ARCHITECTURE.md
- TASK_HISTORY.md

Documentation Notes

- Dispatcher: resolves a consultation context to a specialty implementation.
- Registry Flow: registry is the single source of truth for department routing.
- Resolution Lifecycle: consultation context -> dispatcher -> registry -> specialty instance.
- Future Department Onboarding: add adapter, register adapter, no dispatcher changes required.
- Remaining Work: expand the registry with additional departments as they are implemented and wire any future specialty-specific entry points through the same dispatch contract.

Next Phase

Specialty expansion and broader department-specific workflow integration.

## Phase 3B — Patient Timeline & Longitudinal Medical History

Status

Completed (implementation and documentation only; no runtime validation executed)

Summary

Implemented a canonical patient timeline model and persistence helpers that
store longitudinal history entries derived from completed consultations.
The timeline is patient-owned and reusable by future specialties without
changing consultation persistence, GP reasoning, or doctor prompts.

Files Modified

- backend/models/timeline.py
- backend/models/__init__.py
- backend/general_physician/db/pgvector_tracker.py
- backend/general_physician/agent.py
- README.md
- ARCHITECTURE.md
- TASK_HISTORY.md

Documentation Notes

- Timeline Model: shared canonical object with a top-level timeline and history entries.
- Persistence: `get_patient_timeline()`, `append_timeline_entry()`, and
  `load_patient_history()` reuse existing Postgres-backed storage.
- Lifecycle: completed consultation -> structured summary -> append timeline entry -> persist timeline.
- Remaining Work: expand consumers for downstream departments and expose the timeline through additional interfaces.

Next Phase

Phase 4 — broader longitudinal history consumption and specialty reuse.

## Phase 3A — Shared Notification Framework

Status

Completed (implementation and documentation only; no runtime validation executed)

Summary

Implemented a canonical internal notification model and persisted it through the
existing backend persistence layer. The framework is reusable across modules and
supports the accepted-lab workflow without introducing delivery channels,
WebSocket pushes, email, SMS, or frontend behavior.

Files Modified

- backend/models/notification.py
- backend/models/__init__.py
- backend/general_physician/db/pgvector_tracker.py
- backend/general_physician/agent.py
- README.md
- ARCHITECTURE.md
- TASK_HISTORY.md

Documentation Notes

- Notification Model: shared canonical object with status and type enums.
- Persistence: `create_notification()`, `get_notifications()`, and
  `mark_read()` helpers reuse existing Postgres-backed storage.
- Lifecycle: accepted lab -> create persisted notification -> stop.
- Remaining Work: integrate notifications with downstream modules, add
  delivery adapters, and expose retrieval to other services in a later phase.

Next Phase

Phase 4 — downstream notification consumption and richer workflow integration.

## Phase 3 — Consultation Orchestration & Appointment Integration

Status

Completed (implementation and documentation only; no runtime validation executed)

Summary

Implemented a lightweight consultation handoff between the receptionist booking flow and the appointment-ready UI. The booking path now creates and persists a canonical consultation context, attaches it to the appointment, and exposes the context state through the existing WebSocket doctor-ready event without starting any doctor conversation.

Files Modified

- backend/models/intake.py
- backend/models/__init__.py
- backend/general_physician/db/pgvector_tracker.py
- backend/general_physician/graphs/routing_graph.py
- backend/general_physician/models/session_state.py
- backend/general_physician/services/local_store.py
- frontend/hooks/useChatSocket.ts
- frontend/types/chat.ts
- frontend/components/sidebar/AppointmentsPanel.tsx
- README.md
- ARCHITECTURE.md
- TASK_HISTORY.md

Documentation Notes

- Consultation Context: persisted as a canonical object with patient, session, appointment, department, doctor, and lifecycle metadata.
- Consultation Lifecycle: prepared as `CREATED` and surfaced for future doctor workflows.
- Appointment Integration: appointment records include the consultation context reference and remain compatible with the existing flow.
- Ownership Model: patient remains the root entity; the consultation context is owned by the appointment.
- Persistence Strategy: consultation context records are stored in Postgres for downstream reuse.
- WebSocket Payload Changes: existing `doctor_ready` events now include consultation status and department metadata.
- Remaining Work: doctor workflow loading, lifecycle transitions, and deeper department-specific reuse remain future work.

Next Phase

Phase 4 — doctor conversation orchestration and doctor-specific state loading.

## Phase 0

Status

Completed

Summary

Repository documentation and architecture lock completed. Created or updated
the following documentation files to accurately reflect the current repository
state without modifying source code or behavior.

Files Modified

- README.md
- ARCHITECTURE.md
- TASK_HISTORY.md

Notes

- No backend, frontend, database schema, prompt, or Docker behavior was
  modified as part of this phase.
- No tests were executed and no services were started.

Next Phase

Patient Foundation

## Phase 1B


Summary (Revision)

Replaced the previous Phase 1B registration with the intended Patient
Initialization workflow. Key changes:

- Registration is the only entry point — there is no login, authentication,
  or dashboard. After registration the frontend opens the Ally conversation
  directly.
- `Patient` is the root identity (human-readable `patient_id` + internal
  UUID-backed `session_id`). Sessions reference patients and are distinct
  from patient identifiers.

Files Modified (this revision)

- backend/general_physician/db/pgvector_tracker.py
- backend/general_physician/main.py
- frontend/lib/patient.ts
- frontend/app/signup/page.tsx
- frontend/app/app.tsx
- frontend/app/page.tsx
- frontend/app/login/page.tsx
- frontend/app/chat/page.tsx
- README.md
- ARCHITECTURE.md
- TASK_HISTORY.md

Notes

- Removed demo migration helpers and stopped persisting `patient_id` in
  `localStorage` as the primary identity. Session identifiers are transient
  and stored in `sessionStorage`.
- Registration payloads now only include identity fields (name, age, gender,
  phone, city, consent). Medical history is collected later by Ally during
  intake.

Next Phase

Patient Foundation (continued): persist patient records and add secure
session management (deferred — no auth added in this revision).

Implemented a backend-backed patient registration workflow that generates a
permanent patient identifier, persists patient profiles to Postgres, creates
an initial session, and migrates any existing client-side artifacts when
possible. The frontend signup flow now calls the backend registration API and
stores the returned `patientId` in local storage.

Files Modified

- backend/general_physician/db/pgvector_tracker.py
- backend/general_physician/main.py
- frontend/lib/patient.ts
- frontend/app/signup/page.tsx
- README.md
- ARCHITECTURE.md
- TASK_HISTORY.md

Notes

- No authentication, login, appointments, RAG, or clinical logic were
  implemented or modified.
- No tests were run and no containers were started.

Next Phase

Patient Foundation (continued): persist patient records and add secure
session management.
