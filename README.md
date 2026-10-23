# PSAI — AI-Powered Technical Support & Troubleshooting Platform

> **Product Tagline:** *Diagnose smarter. Resolve faster.*

PSAI is an enterprise-grade backend platform designed for intelligent, evidence-grounded technical incident troubleshooting and real-time dashboard operations.

The backend simultaneously powers two interfaces:
1. **Customer-Facing AI Troubleshooting Assistant** — conversational, evidence-grounded diagnosis, automatic hypothesis formulation, and step-by-step resolution.
2. **Agent-Facing Real-Time Incident Management Dashboard** — live telemetry, automated severity scoring, deterministic diagnostic workflows, action-plan approvals, simulated remediation tools, and WebSocket event broadcasts.

---

## 1. Architecture Overview

PSAI is built as a modular monolith following strict separation of concerns, dependency injection, and clean architecture:

```
psai/
├── backend/
│   ├── app/
│   │   ├── api/v1/             # REST API routers & WebSocket endpoints
│   │   ├── core/               # App configuration, security, exceptions
│   │   ├── db/                 # Database engine, session dependency injection, declarative base
│   │   ├── models/             # SQLAlchemy 2.x ORM models
│   │   ├── schemas/            # Pydantic v2 validation contracts
│   │   ├── services/           # Business logic, LLM adapters, Embeddings, Orchestration
│   │   │   ├── llm_provider/   # Swappable LLM adapters (Gemini, OpenAI, Groq, Mock)
│   │   │   └── embeddings/     # Swappable embedding adapters (Local, OpenAI, Gemini)
│   │   ├── prompts/            # Versioned prompt templates
│   │   ├── policies/           # Deterministic severity scoring & safety filtering
│   │   ├── simulators/         # Predefined diagnostic & system remediation simulators
│   │   ├── websockets/         # Connection manager & monotonic sequence broadcaster
│   │   ├── tests/              # 25+ comprehensive automated tests (including 4 full scenarios)
│   │   └── main.py             # FastAPI entrypoint, middleware, health endpoints
│   ├── alembic/                # Database migrations
│   ├── alembic.ini             # Alembic configuration
│   ├── pyproject.toml          # Project configuration & pytest settings
│   ├── requirements.txt        # Pinned dependencies
│   └── Dockerfile              # Container definition
├── knowledge/
│   └── sample_docs/            # Pre-seeded runbooks & operational policies
├── docker-compose.yml          # Local multi-container stack (PostgreSQL + pgvector + Backend)
├── .env.example                # Sample environment configuration
└── README.md
```

---

## 2. Technology Stack

- **Runtime:** Python 3.12+
- **API Framework:** FastAPI with ASGI high-concurrency support
- **Data Validation:** Pydantic v2 with strict schema enforcement
- **ORM & Data Layer:** SQLAlchemy 2.x with UUID primary keys & UTC timestamps
- **Database:** PostgreSQL with `pgvector` for vector similarity (with automatic in-memory / SQLite fallback for instant zero-dependency local runs and testing)
- **Migrations:** Alembic
- **AI / LLM Orchestration:** Provider adapter supporting Google Gemini (`gemini-2.5-flash`), OpenAI (`gpt-4o-mini`), Groq (`llama-3.3-70b`), and a deterministic offline Mock provider
- **Knowledge Retrieval:** Semantic chunking, SHA-256 deduplication, dense 384-dimensional vector embeddings, and citation generation
- **Real-time Engine:** WebSockets with sequence numbering and data redaction
- **Simulators:** Safe, isolated mock diagnostic tools and remediation actions
- **Testing:** Pytest, pytest-asyncio, and HTTPX TestClient

---

## 3. Database Schema

All database models use UUID primary keys, UTC timestamps, and indexed foreign keys:

1. **`conversations`**: ID, status (`active`, `diagnosing`, `escalated`, `resolved`, `closed`), `product_area`, `environment`, `created_at`, `updated_at`.
2. **`messages`**: ID, `conversation_id`, role (`user`, `assistant`, `system`), `content`, `client_message_id` (idempotency key), `created_at`.
3. **`case_analyses`**: ID, `conversation_id`, `intent`, `sentiment`, `sentiment_score`, `urgency`, `severity_score` (0-100), `impact_scope`, `confirmed_facts`, `hypotheses` (ranked 1-3), `missing_information`, `escalation_required`, `created_at`.
4. **`knowledge_documents`**: ID, `title`, `source`, `version`, `status`, `content_hash` (SHA-256), `created_at`, `updated_at`.
5. **`knowledge_chunks`**: ID, `document_id`, `content`, `section`, `chunk_metadata`, `embedding` (`Vector(384)`).
6. **`diagnostic_runs`**: ID, `conversation_id`, `workflow_key`, `status` (`running`, `passed`, `failed`, `escalated`, `completed`), `current_step`, `created_at`, `completed_at`.
7. **`diagnostic_steps`**: ID, `run_id`, `step_key`, `instruction`, `result` (`pending`, `passed`, `failed`, `inconclusive`), `evidence`, `executed_at`.
8. **`action_plans`**: ID, `conversation_id`, `summary`, `customer_impact`, `confirmed_findings`, `steps_attempted`, `recommendations`, `required_evidence`, `recommended_team`, `escalation_reason`, `status` (`draft`, `approved`, `rejected`, `executed`), `created_at`, `approved_at`.
9. **`tickets`**: ID, `conversation_id`, `priority` (`low`, `medium`, `high`, `critical`), `status` (`open`, `in_progress`, `resolved`, `closed`), `assigned_team`, `summary`, `created_at`, `updated_at`.
10. **`audit_events`**: ID, `conversation_id`, `actor` (`customer`, `agent`, `system`), `event_type`, `payload` (secret-scrubbed JSON), `created_at`.

---

## 4. API Endpoints (`/api/v1`)

### Conversations & Messaging
- `POST /api/v1/conversations` — Create a conversation session.
- `GET /api/v1/conversations` — List conversations with pagination, status, and product area filters.
- `GET /api/v1/conversations/{id}` — Retrieve conversation details and state.
- `POST /api/v1/conversations/{id}/messages` — Submit message (with client idempotency check), retrieve grounded AI reply and citations.
- `POST /api/v1/conversations/{id}/analyze` — Recompute structured case analysis, hypotheses, and severity scoring.

### Diagnostics Workflows
- `POST /api/v1/conversations/{id}/diagnostics` — Start diagnostic workflow state machine.
- `GET /api/v1/diagnostics/{id}` — Retrieve workflow step execution history and status.
- `POST /api/v1/diagnostics/{id}/steps/{step_id}/result` — Record step outcome (`passed`, `failed`, `inconclusive`) and advance to next state.

### Action Plans & Human Approval
- `POST /api/v1/conversations/{id}/action-plan` — Generate comprehensive action plan.
- `GET /api/v1/conversations/{id}/action-plan` — Retrieve the latest plan.
- `POST /api/v1/action-plans/{id}/approve` — Approve plan for execution.
- `POST /api/v1/action-plans/{id}/reject` — Reject plan.

### Tickets & Simulated Actions
- `POST /api/v1/conversations/{id}/tickets` — Create a support ticket.
- `GET /api/v1/tickets` — List tickets with status and priority filters.
- `GET /api/v1/tickets/{id}` — Retrieve ticket details.
- `POST /api/v1/cases/{id}/actions` — Execute authorized simulated action (`mock_config_correction`, `mock_integration_health_check`, `mock_service_escalation`, `mock_compensation`).

### Knowledge Base & Retrieval
- `POST /api/v1/knowledge/documents` — Upload and index Markdown, TXT, or PDF documents into semantic vector index.
- `GET /api/v1/knowledge/documents` — List indexed documents.
- `GET /api/v1/knowledge/documents/{id}` — Retrieve document details.
- `DELETE /api/v1/knowledge/documents/{id}` — Remove document and all indexed chunks.
- `GET /api/v1/knowledge/search?q=...` — Semantic vector similarity search.

### Analytics & Real-Time Dashboard
- `GET /api/v1/analytics/overview` — Dashboard summary metrics.
- `GET /api/v1/analytics/incidents` — 7-day incident and high-severity trend data.
- `GET /api/v1/analytics/resolution` — Troubleshooting efficiency and resolution metrics.
- `WS /api/v1/ws/dashboard` — WebSocket stream broadcasting live updates (`message.created`, `case.updated`, `classification.completed`, `diagnostic.step_completed`, `action_plan.generated`, `action.completed`, `ticket.created`).

---

## 5. Severity & Escalation Engine

Severity scoring is deterministic and explainable:

$$\text{Severity Score} = (\text{Impact} \times 0.35) + (\text{Urgency} \times 0.25) + (\text{Scope} \times 0.25) + (\text{SLA Risk} \times 0.15)$$

- **Thresholds:**
  - `Low`: $< 30$
  - `Medium`: $30 - 59$
  - `High`: $60 - 84$
  - `Critical`: $\ge 85$
- **Mandatory Escalation Rules:**
  - Critical security incidents (e.g. credential compromise, breach).
  - Confirmed widespread service outages (regional or universal failure).
  - High severity score $\ge 70$.
  - Repeated diagnostic failure exceeding retry limit ($> 3$).

---

## 6. Security & Safety Controls

1. **Prompt Injection Defense:** Regex and pattern analysis detect override attempts (`ignore previous instructions`, `jailbreak`, etc.) and reject adversarial prompt tampering.
2. **Sensitive Data Masking:** Passwords, bearer tokens, API keys, and OTPs are redacted from audit trails and WebSocket broadcasts (`[REDACTED_TOKEN]`, `[REDACTED_PASSWORD]`).
3. **Role-Based Authorization:** Simulated actions check `X-Actor-Role` and require explicit `confirmed_approval=True` for consequential operations.
4. **Rate Limiting:** Sliding-window rate limiter per client IP.
5. **Upload Validation:** Strict size limits (10MB) and content type checks.

---

## 7. Setup & Quick Start

### Option A: Local Development (SQLite & Mock Provider — Zero external dependencies)

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Activate the virtual environment:**
   ```bash
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Seed sample knowledge runbooks:**
   ```bash
   python app/scripts/seed_knowledge.py
   ```

6. **Start the FastAPI development server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Open Swagger API Documentation:**
   Visit `http://localhost:8000/docs` in your browser.

---

### Option B: Docker Compose (PostgreSQL + pgvector)

```bash
docker compose up --build
```
This automatically boots:
- PostgreSQL with `pgvector` on port `5432`
- PSAI Backend with automatic Alembic migrations on port `8000`

---

## 8. Running Automated Tests

Run the full Pytest test suite:

```bash
cd backend
pytest -v
```

### Verified Test Scenarios:
- **Scenario 1:** API authentication failure (HTTP 401 after key rotation) that diagnoses stale cache, executes simulated cache invalidation, verifies credential sync, and resolves.
- **Scenario 2:** External CRM integration timeout that probes endpoint, detects persistent socket timeout, triggers retry limit, and escalates to Tier-2 DevOps.
- **Scenario 3:** Ambiguous complaint ("system slow and not working") that correctly identifies missing information, asks targeted clarifying questions, and avoids false escalation.
- **Scenario 4:** Suspected widespread outage (HTTP 500 spike across all users) that triggers mandatory critical escalation, validates database connection pool saturation, and dispatches PagerDuty alerts to Incident Command.
- **Unit & Security Suites:** Conversation persistence, message idempotency, knowledge vector search, prompt injection resistance, sensitive data masking, rate limiting, and WebSockets.
#   u n s t o p  
 