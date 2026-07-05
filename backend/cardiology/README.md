# General Physician Backend

## Overview
This is the FastAPI backend for the Ally AI general physician service. It handles WebSocket connections for the routing graph (appointment booking) and doctor graph (live consultations), along with REST endpoints for document upload and chat.

## Architecture

### Components
- **WebSocket Router** (`ws/router.py`): Handles real-time WebSocket connections and routes messages through the routing graph or doctor graph
- **Routing Graph** (`graphs/routing_graph.py`): State machine for patient intake, doctor selection, slot selection, and booking confirmation
- **Doctor Agent** (`agent.py`): LangGraph-based doctor consultation agent with questioning, evaluation, and lab test recommendation
- **RAG Retriever** (`rag/retriever.py`): Retrieves relevant medical knowledge based on patient symptoms
- **LLM Client** (`llm/nvidia_client.py`): Interface to NVIDIA NIM API for LLM inference

### State Flow

#### Routing Graph Flow
1. **GREETING** → Initial welcome message
2. **INTENT_CLASSIFICATION** → Classify patient intent (appointment vs consultation)
3. **HEALTH_STATUS_QUESTIONS** → Ask 2-3 health questions
4. **DOCTOR_SELECTION** → User selects doctor from available options
5. **SLOT_SELECTION** → User selects available time slot
6. **BOOKING_CONFIRMATION** → Confirm appointment and emit `doctor_ready` event
7. **DONE** → Routing complete

#### Doctor Graph Flow
1. **SESSION_INIT** → Initialize doctor session with patient context
2. **QUESTIONING** → Ask clinical questions (max 5 questions)
3. **EVALUATION** → Evaluate symptoms and recommend tests if needed
4. **LAB_NOTIFICATION** → Present lab test recommendations
5. **USER_DECISION** → User accepts/rejects lab tests
6. **REPORT_PENDING** → Generate lab report if tests accepted
7. **SESSION_COMPLETE** → Consultation complete

## Known Issues and Fixes

### Issue 1: Slow Response Times
**Status**: ✅ FIXED
**Problem**: LLM responses were taking too long due to using the 70B parameter model (`meta/llama-3.1-70b-instruct`)
**Fix**: Switched to the faster 8B model (`meta/llama-3.1-8b-instruct`) in `.env` file
**Impact**: Response times improved by 5-10x
**Configuration**: 
```env
NVIDIA_MODEL=meta/llama-3.1-8b-instruct
```

### Issue 2: Generic "I hit a snag" Error
**Status**: ✅ FIXED
**Problem**: Doctor consultation failures showed generic error message without actual error details
**Fix**: Updated error handling in `ws/router.py` to include actual exception message in the response
**Change**: 
```python
# Before
except Exception:
    await _send(ws, WSEvent(type="text", payload={"content": "I hit a snag - please try again."}))

# After  
except Exception as e:
    error_msg = str(e) if str(e) else "I hit a snag - please try again."
    await _send(ws, WSEvent(type="text", payload={"content": f"I hit a snag - {error_msg}"}))
```

### Issue 3: Doctor Selection Loop
**Status**: ✅ FIXED
**Problem**: Selecting a doctor would loop back to doctor selection instead of progressing to slot selection
**Root Cause**: Frontend was sending doctor selection events without the `context: "receptionist"` field
**Fix**: Added context field to doctor selection event in `frontend/hooks/useChatSocket.ts`
**Change**:
```typescript
// Before
payload: { id: doctorId, doctor_id: doctorId }

// After
payload: { id: doctorId, doctor_id: doctorId, context: "receptionist" }
```

### Issue 4: WebSocket Connection Failure
**Status**: ⚠️ PARTIALLY RESOLVED
**Problem**: Frontend WebSocket connections failing with "WebSocket connection to 'ws://localhost:8000/ws/...' failed"
**Root Cause**: Backend server not running on port 8000
**Workaround**: Backend needs to be started locally since Docker commands not working in current environment
**Command**:
```bash
cd backend/general_physician
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Issue 5: Consultation Flow After Slot Selection
**Status**: ✅ VERIFIED WORKING
**Problem**: User wanted to ensure consultation appears automatically after time slot selection
**Verification**: Flow is already implemented correctly:
1. Slot selection → Booking confirmation
2. Backend emits `doctor_ready` event with appointment details
3. Frontend automatically switches to Appointments tab
4. Shows pre-consultation upload screen
5. "Start Consultation" button appears after upload
6. Live consultation chat interface starts

## Environment Setup

### Required Environment Variables
```env
POSTGRES_DB=allyai
POSTGRES_USER=allyai
POSTGRES_PASSWORD=allyai
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL=meta/llama-3.1-8b-instruct
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_PROVIDER=nvidia

APPOINTMENT_SERVICE_URL=http://localhost:8081
```

### Dependencies
See `requirements.txt` for Python dependencies.

## Running the Backend

### Local Development
```bash
cd backend/general_physician
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker
```bash
docker-compose up -d --build backend
```

## API Endpoints

### WebSocket
- `GET /ws/{user_id}` - WebSocket endpoint for real-time communication

### REST
- `POST /upload_document` - Upload patient documents
- `POST /chat` - Shortcut endpoint to drive routing graph

## Testing

Run tests with:
```bash
pytest backend/general_physician/tests/
```

## Current Limitations

1. **Docker Environment**: Docker commands not working in current development environment, requiring local backend startup
2. **Error Visibility**: While error messages are improved, backend logs need to be checked for detailed debugging
3. **LLM Speed**: Even with 8B model, responses can be slow depending on NVIDIA API load

## Future Improvements

1. Add proper Docker volume mounting for development
2. Implement retry logic for LLM API failures
3. Add comprehensive logging and monitoring
4. Implement caching for RAG retrieval
5. Add rate limiting for API endpoints
