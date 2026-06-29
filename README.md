# Ally AI

This repository contains the initial project structure for the hospital agent proof-of-concept.

## Project Structure

```
hospital-agent-poc/
├── README.md
├── docker-compose.yml # PostgreSQL + pgvector only
├── .env.example
├── .gitignore
│
├── frontend/ # Next.js 14 (UI layer)
│ ├── app/
│ │ ├── page.tsx # Chat entry page
│ │ ├── layout.tsx
│ │ └── globals.css
│ ├── components/
│ │ ├── chat/
│ │ │ ├── ChatPanel.tsx
│ │ │ ├── MessageBubble.tsx
│ │ │ └── DoctorPersonaHeader.tsx
│ │ ├── cards/
│ │ │ ├── DeptSelectCard.tsx
│ │ │ ├── DoctorSelectCard.tsx
│ │ │ └── SlotSelectCard.tsx
│ │ ├── lab/
│ │ │ ├── LabNotificationCard.tsx
│ │ │ └── AcceptRejectButtons.tsx
│ │ └── inbox/
│ │   ├── InboxPanel.tsx
│ │   └── ReportDownloadLink.tsx
│ ├── lib/
│ │ ├── websocket.ts
│ │ └── types.ts
│ └── package.json
│
├── backend/ # FastAPI + LangGraph services
│ ├── main.py
│ ├── ws/
│ │ └── router.py
│ ├── graphs/
│ │ ├── routing_graph.py
│ │ ├── doctor_graph_base.py
│ │ ├── cardiology_agent.py
│ │ ├── neurology_agent.py
│ │ ├── endocrinology_agent.py
│ │ └── evaluation_node.py
│ ├── rag/
│ │ ├── ingest.py
│ │ ├── retrieve_chunks.py
│ │ └── documents/
│ ├── models/
│ │ ├── lab_decision.py
│ │ └── session_state.py
│ ├── db/
│ │ └── checkpointer.py
│ └── requirements.txt
│
├── services/
│ ├── appointment/ # Go service
│ │ ├── main.go
│ │ ├── handlers/
│ │ │ ├── departments.go
│ │ │ ├── doctors.go
│ │ │ ├── slots.go
│ │ │ └── appointments.go
│ │ └── go.mod
│ └── lab/ # Go service
│   ├── main.go
│   ├── handlers/
│   │ ├── lab_tests.go
│   │ ├── reports.go
│   │ └── inbox.go
│   ├── pdf/
│   │ └── generate.go
│   └── go.mod
│
├── migrations/
│ ├── alembic/ # FastAPI-owned tables
│ │ └── versions/
 │ └── go-migrate/ # Go-owned tables
│     └── versions/
├── scripts/
│ └── seed.py
└── docs/
  ├── openapi.yaml
  └── integration-contracts.md
```

## Notes

- This repo has an initial project skeleton with placeholder files.
- Use `docker-compose up` to start services once implementations are added.
- `backend/requirements.txt` contains FastAPI dependencies.
- `services/` contains Go service modules.
