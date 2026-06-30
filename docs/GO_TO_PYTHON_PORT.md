# Go → Python Port Guide

This document is for the person converting the legacy Go microservices
(`services/appointment`, `services/lab`) into the Python backend.

The Python backend is the **source of truth** today. The Go services still
exist on disk for reference, but the live path (`backend/main.py` →
`backend/ws/router.py` → `backend/graphs/*`) does **not** call the Go
HTTP API. It uses an in-memory `LocalStore` (`backend/services/local_store.py`)
whose surface area exactly mirrors the Go service.

If/when you port the Go services' logic to Python, the table below maps
each Go file to its Python equivalent (or notes that no Python equivalent
exists yet because the feature is unimplemented).

## Services

### `services/appointment/` (Go HTTP service, port 8081)

| Go file                                     | Python equivalent                                  | Notes |
|---------------------------------------------|----------------------------------------------------|-------|
| `main.go`                                   | `backend/main.py` (via `ws/router.py`)             | WebSocket replaces HTTP. No standalone service. |
| `handlers/store.go` (`Store`, `seed`, `BookAppointment`, `ListAppointments`, etc.) | `backend/services/local_store.py` (`LocalStore`, `_seed`, `book_appointment`, etc.) | Same in-memory model. `LocalStore` is currently the live store; the HTTP version is unused. |
| `handlers/departments.go` (`ListDepartments`) | `LocalStore.list_departments`                      | Returns `[{"id","name"}]`. |
| `handlers/doctors.go` (`ListDoctors`)        | `LocalStore.list_doctors(department)`              | |
| `handlers/slots.go` (`ListSlots`)            | `LocalStore.list_slots(doctor_id)`                 | |
| `handlers/appointments.go` (`BookAppointment`, `ListAppointments`) | `LocalStore.book_appointment(...)`                | Returns `(status_code:int, body:dict)`. Status `409` = slot taken. |
| `handlers/handlers.go` (`API` struct, mux)   | n/a — Python uses FastAPI WebSocket dispatcher in `backend/ws/router.py` | |

**Key behavioural differences to preserve when porting:**

1. `Store.slotID(n)` uses base-36 ids (`s1, s2, ..., s9, sa, sb, ...`).
   The Python `_next_id` uses decimal (`s1, s2, ...`). **Pick one and
   document it**; clients depend on slot id strings.
2. `Store.BookAppointment` returns `ErrSlotBooked` when the slot is taken.
   Python returns `(409, {"error":"slot_taken"})`. Match the status code.
3. `LocalStore` only seeds one doctor (`d5`, General Practice). The Go
   service seeds 5 doctors across 4 departments. The Python receptionist
   graph hardcodes routing to `general` and `d5` (see
   `backend/graphs/routing_graph.py: GP_DOCTOR_ID = "d5"`). When porting
   multi-department logic from Go, update `routing_graph.intent_node`
   to pick the department from the LLM output instead of hardcoding
   `general`.

### `services/lab/` (Go lab service — currently empty `main.go`)

| Go file                  | Python equivalent                       | Notes |
|--------------------------|------------------------------------------|-------|
| `main.go`                | n/a — `general_physician_agent.py` emits a `lab_notification` and `report_ready` WSEvent | Lab is a stub for now. |
| `handlers/lab_tests.go`  | n/a                                      | LLM-driven recommendation only. |
| `handlers/reports.go`    | n/a — fake `inbox_id` in `general_physician_agent.report_pending` | |
| `handlers/inbox.go`      | n/a                                      | |
| `pdf/generate.go`        | n/a                                      | PDF gen deferred. |

## Data shapes

Both sides should agree on the JSON wire format:

```json
{
  "department": {"id": "general", "name": "General Practice"},
  "doctor":     {"id": "d5", "name": "Dr. Alex Rivera", "department_id": "general"},
  "slot":       {"id": "s1", "doctor_id": "d5", "start_time": "2026-01-01T10:00:00+00:00"},
  "appointment":{"id": "a1", "doctor_id": "d5", "slot_id": "s1", "patient": "alice", "reason": "...", "department": "general", "booked_at": "..."}
}
```

The Python CLI (`chat_cli.py`) and the WebSocket dispatcher
(`backend/ws/router.py`) read these shapes. Don't change them without
updating both.

## How to verify parity

```bash
# Start the Go service
go run ./services/appointment

# Hit it
curl http://localhost:8081/departments
curl http://localhost:8081/doctors?department=general
curl http://localhost:8081/slots?doctor=d5
curl -X POST http://localhost:8081/appointments \
  -H "content-type: application/json" \
  -d '{"doctor_id":"d5","slot_id":"s1","patient":"alice","reason":"checkup"}'
```

The Python `LocalStore` should return the **same JSON** for the same
inputs. Drop the Go service in a test that replays a sequence of calls
and asserts equality against `LocalStore` — that is the contract.
