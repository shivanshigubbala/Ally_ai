# Ally AI Integration Issues Report

## Executive Summary
The codebase has several critical integration issues around patient ID tracking, appointment lifecycle management, and WebSocket state persistence. These issues prevent the system from properly tracking patients across registration, consultation booking, and doctor interactions.

---

## 1. FRONTEND APP FLOW ISSUES

### Issue 1.1: No Patient ID Generation at Registration
**File:** [frontend/app/signup/page.tsx](frontend/app/signup/page.tsx#L1-L300)
**Lines:** 200-230  
**Problem:**
- Signup collects user profile but never generates or assigns a `patient_id`
- Patient ID should be created at registration and persisted
- `registerProfile()` function doesn't return a patient_id to the frontend

**Current Flow:**
```typescript
const res = await registerProfile(payload as any);
// No patient_id returned or stored
```

**Impact:** Patient cannot be uniquely identified by the backend; all identification relies on `user_id` derived from name.

---

### Issue 1.2: User ID Derived from Name Only
**File:** [frontend/lib/patient.ts](frontend/lib/patient.ts#L1-L80)
**Lines:** 40-50  
**Function:** `slugifyUserId(name: string)`  
**Problem:**
- `user_id` is created by slugifying patient name (e.g., "John Smith" → "john_smith")
- Two patients with same name create collision
- User ID changes if patient changes their name
- No UUID or stable identifier

**Current Code:**
```typescript
export function slugifyUserId(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return slug || "guest";
}
```

**Impact:** Cannot support multiple patients with same name; breaks data integrity.

---

### Issue 1.3: No Patient ID Passed on WebSocket Connection
**File:** [frontend/hooks/useChatSocket.ts](frontend/hooks/useChatSocket.ts#L1-L100)
**Lines:** 1-50  
**Problem:**
- WebSocket connects to `/ws/{user_id}` where `user_id` is name-derived slug
- No patient_id header or parameter sent
- Backend cannot validate patient identity from ID

**Current Connection:**
```typescript
const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE_URL?.replace(/\/$/, "") || "ws://localhost:8000";
// ws://localhost:8000/ws/john_smith  ← No patient_id
```

**Impact:** Backend has no way to verify patient identity independent of name-based slug.

---

### Issue 1.4: Appointment ID Loss on Page Reload
**File:** [frontend/app/chat/page.tsx](frontend/app/chat/page.tsx#L1-L100)
**Lines:** 40-70  
**Problem:**
- `appointmentBooked` flag is stored in React state, not localStorage
- Page refresh loses appointment context
- Must restart consultation flow

**Current Code:**
```typescript
const [appointmentBooked, setAppointmentBooked] = useState(false);
const [doctorReady, setDoctorReady] = useState<DoctorReadyInfo | null>(null);
// Both lost on page reload
```

**Impact:** User loses appointment context after browser refresh; poor UX.

---

### Issue 1.5: Patient ID Not Persisted in Session
**File:** [frontend/lib/patient.ts](frontend/lib/patient.ts#L15-L30)
**Problem:**
- No `patientId` field stored in `PatientProfile` interface initially
- Field added as optional (`patientId?: string`) but never populated
- No way to retrieve patient_id on login

**Interface Definition:**
```typescript
export interface PatientProfile {
  // ... other fields
  patientId?: string;  // Optional, never set
}
```

**Impact:** Cannot restore patient context on login without re-registering.

---

## 2. BACKEND API ENDPOINTS ISSUES

### Issue 2.1: No Registration/Patient Creation Endpoint
**File:** [backend/general_physician/main.py](backend/general_physician/main.py#L1-L100)
**Lines:** 1-300  
**Problem:**
- No `/register` or `/patient` POST endpoint
- No way for frontend to explicitly create a patient record
- Patient creation happens implicitly in appointment booking

**Missing Endpoint:**
```python
# Should exist but doesn't:
@app.post("/register")
async def register_patient(profile: PatientProfile) -> dict:
    # Create patient and return patient_id
    pass

@app.post("/patient/{user_id}")
async def create_or_update_patient(user_id: str, profile: dict) -> dict:
    # Ensure patient exists in system
    pass
```

**Impact:** No explicit patient registration flow; implicit creation through appointments.

---

### Issue 2.2: No Patient ID Validation Endpoint
**File:** [backend/general_physician/main.py](backend/general_physician/main.py#L50-L100)
**Problem:**
- No endpoint to validate patient_id or user_id
- Frontend cannot confirm patient was created
- No way to get patient context by ID

**Missing Endpoint:**
```python
@app.get("/patient/{patient_id}")
async def get_patient(patient_id: str) -> dict:
    # Return patient profile
    pass

@app.get("/patient/validate/{patient_id}")
async def validate_patient(patient_id: str) -> dict:
    # Return 200 if valid, 404 if not
    pass
```

**Impact:** No way to verify patient exists before starting consultation.

---

### Issue 2.3: Patient ID Not Passed to WebSocket Init
**File:** [backend/general_physician/ws/router.py](backend/general_physician/ws/router.py#L50-L150)
**Lines:** 50-70  
**Problem:**
- WebSocket endpoint only takes `user_id` parameter
- patient_id must be extracted from message or derived from user_id
- No initial patient context validation

**Current Endpoint:**
```python
@router.websocket("/ws/{user_id}")
async def ws_endpoint(ws: WebSocket, user_id: str) -> None:
    # No patient_id parameter
    # Must be extracted from first message
    pass
```

**Impact:** Patient identity unverified at connection time.

---

## 3. DATABASE MODELS ISSUES

### Issue 3.1: No Explicit Patient Table
**File:** [backend/general_physician/db/models.py](backend/general_physician/db/models.py#L1-L100)
**Lines:** 1-50  
**Problem:**
- Only generic `User` table with JSONB fields
- No `Patient` table with explicit fields
- Patient identity mixed with user account identity

**Current Schema:**
```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    profile = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    health_data = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    # No explicit patient_id field
```

**Missing:**
```python
class Patient(Base):
    __tablename__ = "patients"
    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    external_patient_id = Column(String(255), unique=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))
```

**Impact:** Cannot track patient identity independent of user account; no persistent patient record.

---

### Issue 3.2: Session Table Missing Patient ID
**File:** [backend/general_physician/db/models.py](backend/general_physician/db/models.py#L15-L50)
**Lines:** 15-30  
**Problem:**
- `Session` has `user_id` but no `patient_id`
- Cannot link session to patient record
- Consultation cannot be tied to patient

**Current Schema:**
```python
class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Missing: patient_id
    status = Column(String(50), nullable=False, server_default=text("'active'"))
```

**Required Addition:**
```python
patient_id = Column(String(36), nullable=True)  # Link to Patient table
```

**Impact:** Cannot retrieve all sessions for a specific patient; breaks patient history lookup.

---

### Issue 3.3: Appointment Patient ID Optional
**File:** [backend/general_physician/services/local_store.py](backend/general_physician/services/local_store.py#L1-L50)
**Lines:** 30-40  
**Problem:**
- `Appointment.patient_id` is optional
- Appointments can exist without patient reference
- No foreign key relationship

**Current Definition:**
```python
@dataclass
class Appointment:
    id: str
    doctor_id: str
    slot_id: str
    patient: str  # Just a name string
    reason: str
    department: str
    booked_at: datetime
    patient_id: Optional[str] = None  # ← Optional, no FK
    session_id: Optional[str] = None
    consultation_context_id: Optional[str] = None
    status: str = "booked"
```

**Problem:** `patient` is a string (name), `patient_id` is optional.

**Impact:** Appointments not properly linked to patient records.

---

## 4. WEBSOCKET FLOW ISSUES

### Issue 4.1: Patient ID Extracted From Message, Not Connection
**File:** [backend/general_physician/graphs/routing_graph.py](backend/general_physician/graphs/routing_graph.py#L115-L140)
**Lines:** 115-140  
**Function:** `_extract_patient_id(text: str)`  
**Problem:**
- Patient ID extracted by regex from message content: `"my id is 42"` or `"ID: 42"`
- Not all patients will state their ID
- Fragile regex-based extraction

**Current Extraction:**
```python
def _extract_patient_id(text: str) -> str | None:
    patterns = [
        r"\b(?:patient\s+)?id(?:entifier)?\s*(?:is|=|:)?\s*([0-9A-Za-z-]+)\b",
        r"\bID[:#]?\s*([0-9A-Za-z-]+)\b",
        r"\bmy\s+id\s*(?:is|=|:)?\s*([0-9A-Za-z-]+)\b",
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None
```

**Issues:**
- Requires patient to explicitly state ID
- No validation of extracted ID
- Easily missed if patient forgets

**Impact:** Patient ID often remains unset through routing flow.

---

### Issue 4.2: No Patient ID Validation at Consultation Start
**File:** [backend/general_physician/ws/router.py](backend/general_physician/ws/router.py#L245-L280)
**Lines:** 245-280  
**Function:** `_handle_start_consultation()`  
**Problem:**
- No check that patient_id exists before starting doctor session
- Consultation starts with potentially missing patient_id
- Doctor state may have null patient_id

**Current Code:**
```python
async def _handle_start_consultation(ws: WebSocket, user_id: str,
                                     payload: dict) -> None:
    appointment_id = payload.get("appointment_id", "")
    if not appointment_id:
        await _send(ws, WSEvent(type="text", payload={
            "content": "No appointment ID provided.",
        }))
        return
    # ← No patient_id validation here
    
    # Proceed to doctor consultation without verifying patient
    await _drive_doctor(ws, user_id, appointment_id, None, None)
```

**Impact:** Doctor graph may operate without patient context.

---

### Issue 4.3: Lab Decision Doesn't Validate Patient Context
**File:** [backend/general_physician/ws/router.py](backend/general_physician/ws/router.py#L310-L340)
**Lines:** 310-340  
**Problem:**
- Lab decision event carries `session_id` or `appointment_id`
- No patient_id validation
- Cannot ensure lab decision belongs to correct patient

**Current Code:**
```python
# From ws_endpoint's message loop:
if evt.type == "select":
    # Lab decision or other select event
    action = evt.payload.get("action", "")
    if action == "lab_accept" or action == "lab_reject":
        # ← No patient_id verification
        # Process decision for appointment
        possible_apt = evt.payload.get("session_id") or evt.payload.get("appointment_id")
        if possible_apt:
            _doctor_sessions[user_id] = possible_apt
            await _drive_doctor(ws, user_id, possible_apt, ...)
```

**Impact:** Lab decision could be misattributed; no audit trail.

---

### Issue 4.4: State Not Persisted Across Reconnection
**File:** [backend/general_physician/ws/router.py](backend/general_physician/ws/router.py#L350-L380)
**Lines:** 350-380  
**Problem:**
- `_user_state` and `_doctor_sessions` are in-memory dicts
- Lost on server restart
- Reconnection requires restarting consultation

**Current State Management:**
```python
_user_state: dict[str, str] = {}  # In-memory only
_doctor_sessions: dict[str, str] = {}  # In-memory only

@router.websocket("/ws/{user_id}")
async def ws_endpoint(ws: WebSocket, user_id: str) -> None:
    # On disconnect:
    except WebSocketDisconnect:
        if user_id in _doctor_sessions:
            del _doctor_sessions[user_id]  # ← Data lost
        if user_id in _connections:
            del _connections[user_id]
        return
```

**Impact:** Cannot resume consultation after reconnection.

---

## 5. SPECIALTY DISPATCHER ISSUES

### Issue 5.1: Dispatcher Lacks Patient Context
**File:** [backend/specialties/dispatcher.py](backend/specialties/dispatcher.py#L1-L60)
**Lines:** 1-60  
**Problem:**
- `resolve_specialty()` takes consultation context only
- No patient_id available to resolver
- Cannot fetch patient-specific specialty config

**Current Dispatch:**
```python
def resolve_specialty(consultation_context: Any, registry: SpecialtyRegistry | None = None) -> BaseSpecialty:
    return SpecialtyDispatcher(registry=registry).dispatch(consultation_context)
    # ← No patient_id parameter
```

**Missing:**
```python
def resolve_specialty(
    consultation_context: Any, 
    patient_id: str | None = None,  # ← Missing
    registry: SpecialtyRegistry | None = None
) -> BaseSpecialty:
    # Could use patient_id to fetch patient preferences
    pass
```

**Impact:** Cannot personalize specialty selection based on patient history.

---

### Issue 5.2: Dispatcher Called Without Appointment Context
**File:** [backend/general_physician/ws/router.py](backend/general_physician/ws/router.py#L27-L45)
**Lines:** 27-45  
**Function:** `_resolve_doctor_step()`  
**Problem:**
- Dispatcher called with appointment context
- Appointment may not have patient_id set
- Fails if appointment record not found

**Current Implementation:**
```python
def _resolve_doctor_step(appointment_id: str):
    """Resolve the appointment's specialty implementation through the shared dispatcher."""
    apt = store.get_appointment(appointment_id) or {}  # ← May be None or missing patient_id
    department = apt.get("department") or "general"
    consultation_context = {
        "selected_department": department,
        "department": department,
    }
    specialty = resolve_specialty(consultation_context)
    return specialty.run_consultation
```

**Issues:**
- No error handling if appointment not found
- Loses patient context when passing to dispatcher
- Department is only context passed

**Impact:** Cannot trace consultation back to patient if appointment lookup fails.

---

## 6. ROUTING GRAPH STATE ISSUES

### Issue 6.1: Patient ID Not Set on Greeting
**File:** [backend/general_physician/graphs/routing_graph.py](backend/general_physician/graphs/routing_graph.py#L330-L360)
**Lines:** 330-360  
**Function:** `greeting_node()`  
**Problem:**
- Greeting node doesn't initialize patient_id
- Patient name extracted later, ID extraction not triggered
- First message often doesn't contain ID

**Current Code:**
```python
def greeting_node(state: RoutingState, emit: Emitter) -> RoutingState:
    # ...
    patient_name = state.patient_name or (state.user_id or "there").replace("_", " ").title()
    # ← patient_id not initialized
    # ← No prompt asking for patient ID
    state.current_node = "INTENT_CLASSIFICATION"
    return state
```

**Impact:** Patient ID remains unset unless explicitly mentioned in symptom message.

---

### Issue 6.2: Patient ID Not Validated Before Booking
**File:** [backend/general_physician/graphs/routing_graph.py](backend/general_physician/graphs/routing_graph.py#L700-L780)
**Lines:** 700-780  
**Function:** `booking_node()`  
**Problem:**
- Appointment booking doesn't validate patient_id exists
- Booking proceeds with optional patient_id

**Current Code:**
```python
def booking_node(state: RoutingState, emit: Emitter) -> RoutingState:
    # ...
    status, body = store.book_appointment(
        doctor_id=state.selected_doctor or GP_DOCTOR_ID,
        slot_id=state.selected_slot or "",
        patient=state.patient_name or state.user_id,
        reason="booked via Ally receptionist",
        patient_id=state.patient_id,  # ← May be None
        # ...
    )
```

**Issues:**
- `patient_id` can be None
- No attempt to validate or create patient before booking
- Appointment creates orphaned record

**Impact:** Appointments without patient reference; cannot retrieve later.

---

### Issue 6.3: Consultation Context Not Linked to Patient
**File:** [backend/general_physician/graphs/routing_graph.py](backend/general_physician/graphs/routing_graph.py#L620-L660)
**Lines:** 620-660  
**Function:** `_persist_consultation_context()`  
**Problem:**
- Consultation context persisted with potentially null patient_id
- Uses `state.patient_id` which may not be set
- Falls back to user_id or patient_name

**Current Code:**
```python
def _persist_consultation_context(state: RoutingState, appointment_id: str | None, 
                                  doctor_name: str | None, department: str | None) -> None:
    intake = CanonicalIntake(
        patient_id=state.patient_id,  # ← May be None
        session_id=f"routing:{state.user_id}",
        # ...
    )
    context = ConsultationContext(
        patient_reference=state.patient_name or state.patient_id or state.user_id,  # ← Fallback chain
        patient_id=state.patient_id,  # ← May be None
        # ...
    )
```

**Impact:** Consultation not retrievable by patient_id.

---

## 7. SUMMARY TABLE: Critical Issues by Component

| Component | Issue | Severity | Impact |
|-----------|-------|----------|--------|
| **Frontend Registration** | No patient_id generation | CRITICAL | No unique patient identity |
| **Frontend User ID** | Derived from name only | CRITICAL | Name collisions break system |
| **Frontend State** | Appointment ID lost on reload | HIGH | Poor UX, lost context |
| **Backend APIs** | No registration endpoint | CRITICAL | No explicit patient creation |
| **Backend APIs** | No patient lookup endpoint | HIGH | Cannot verify patient exists |
| **WebSocket Init** | No patient_id passed | CRITICAL | Patient unverified at connection |
| **Database** | No Patient table | CRITICAL | No persistent patient record |
| **Database** | Session missing patient_id | HIGH | Cannot retrieve sessions by patient |
| **Database** | Appointment patient_id optional | HIGH | Appointments orphaned |
| **WebSocket** | Patient ID from message only | HIGH | Fragile extraction, often fails |
| **WebSocket** | No consultation validation | HIGH | Doctor session without patient |
| **WebSocket** | Lab decisions unvalidated | MEDIUM | Lab work not tied to patient |
| **WebSocket** | State in-memory only | HIGH | Lost on reconnection |
| **Dispatcher** | No patient context | MEDIUM | Cannot personalize specialty |
| **Routing Graph** | No patient ID prompt | HIGH | ID often unset |
| **Routing Graph** | No booking validation | HIGH | Appointments without patient |

---

## 8. RECOMMENDED FIXES (Priority Order)

### P0 - Critical (Implement First)
1. Add UUID-based `patient_id` generation at registration
2. Create `/register` endpoint that returns `patient_id`
3. Add `Patient` table to database
4. Store `patient_id` in session and pass on WebSocket connection
5. Validate patient_id at WebSocket connection time

### P1 - High (Implement Next)
6. Add `patient_id` to Session table (foreign key to Patient)
7. Make Appointment `patient_id` NOT NULL with foreign key
8. Add `/patient/{patient_id}` endpoint for patient lookup
9. Persist appointment ID and patient ID in localStorage
10. Prompt for patient ID at start of greeting if not provided

### P2 - Medium (Implement After)
11. Persist WebSocket state to database for reconnection
12. Add patient context to specialty dispatcher
13. Validate patient_id in lab decision handling
14. Add audit logging for patient interactions

---

## 9. DATA FLOW: CURRENT vs. EXPECTED

### Current Flow (Broken)
```
Signup (no patient_id) 
  → name → user_id (slugified)
  → WebSocket /ws/{user_id}
  → Patient ID extracted from message (fragile)
  → Appointment booked with optional patient_id
  → Consultation without validated patient
  → Lost on reconnect
```

### Expected Flow (Fixed)
```
Register (generate patient_id) 
  → POST /register → return patient_id + user_id
  → Store patient_id in localStorage
  → WebSocket /ws/{user_id}?patient_id={patient_id}
  → Validate patient_id at connection
  → Initialize consultation with patient context
  → Appointment booked with required patient_id
  → Consultation linked to patient record
  → Persist state, handle reconnection
```

---

## 10. TESTING RECOMMENDATIONS

### Unit Tests
- [ ] Patient ID generation is unique
- [ ] Patient ID persists across sessions
- [ ] Appointment booking fails without patient_id
- [ ] Consultation context includes patient_id
- [ ] Specialty dispatcher receives patient context

### Integration Tests
- [ ] Registration → Chat → Booking → Consultation flow
- [ ] Patient can reconnect and resume consultation
- [ ] Lab decisions properly attributed to patient
- [ ] Multiple patients with same name don't collide
- [ ] Patient history retrievable by patient_id

### E2E Tests
- [ ] Full signup to doctor consultation journey
- [ ] Page reload during appointment
- [ ] Multiple patient sessions concurrently

---

## Appendix: File References

**Frontend:**
- [frontend/app/signup/page.tsx](frontend/app/signup/page.tsx) - Registration form
- [frontend/lib/patient.ts](frontend/lib/patient.ts) - Patient profile utilities
- [frontend/hooks/useChatSocket.ts](frontend/hooks/useChatSocket.ts) - WebSocket client
- [frontend/app/chat/page.tsx](frontend/app/chat/page.tsx) - Chat layout and state

**Backend:**
- [backend/general_physician/main.py](backend/general_physician/main.py) - API endpoints
- [backend/general_physician/ws/router.py](backend/general_physician/ws/router.py) - WebSocket handler
- [backend/general_physician/graphs/routing_graph.py](backend/general_physician/graphs/routing_graph.py) - Routing state machine
- [backend/general_physician/db/models.py](backend/general_physician/db/models.py) - Database models
- [backend/general_physician/services/local_store.py](backend/general_physician/services/local_store.py) - In-memory store
- [backend/specialties/dispatcher.py](backend/specialties/dispatcher.py) - Specialty resolver
- [backend/general_physician/models/session_state.py](backend/general_physician/models/session_state.py) - State classes
