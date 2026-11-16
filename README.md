# ForgetCheck — RAG Deletion & Access-Revocation Tester

> **Tagline:** Check what your AI can still reveal after access changes.  
> **Repository:** [https://github.com/anilkumargadi27-hub/RAG-Deletion-Tester](https://github.com/anilkumargadi27-hub/RAG-Deletion-Tester)  

[![Tests](https://img.shields.io/badge/pytest-24%20passed-emerald)](backend/tests)
[![Playwright](https://img.shields.io/badge/Playwright-E2E%20Passed-blue)](backend/tests/test_e2e_browser.py)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-teal)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19%20%2B%20Vite-cyan)](frontend)

---

## 1. The Problem & Honest Product Boundary

When an enterprise document is deleted or an employee's permission is revoked, document-grounded AI assistants can continue exposing confidential secrets through:
1. **Stale Vector Indexes:** Unpurged vector chunks retrieved by semantic search.
2. **Stale Answer Caches:** Pre-computed answers returned without dependency revalidation.
3. **Stale Conversation Memory:** Retained assistant messages in ongoing multi-turn sessions.

**ForgetCheck** automatically tests whether those retained copies cause newly generated responses to leak forbidden facts.

### Product Boundary & Truth Standards
- **Scope:** ForgetCheck tests application-level retrieval filters, vector store tombstones, database-backed answer cache invalidation, and session conversation memory pruning.
- **Out of Scope:** It does not erase facts from foundational LLM weights or claim universal machine unlearning.
- **Client Boundary:** Information already delivered to an employee's screen prior to deletion cannot be revoked client-side. We evaluate newly returned responses.
- **Verdict Standard:** Audit reports state **"No leakage observed in these tests"**, never *"Guaranteed secure"*.
- **Trace Attribution:** Attribution to a specific layer is verified through controlled source replay; otherwise labeled *Suspected / Multi-Source*.

---

## 2. Architecture Overview

ForgetCheck is implemented as a full-stack monorepo:

```
├── backend/
│   ├── app/
│   │   ├── api/            # Versioned REST APIs (auth, documents, chat, synthetic, reports, admin, health)
│   │   ├── core/           # Security (bcrypt, HttpOnly sessions, CSRF), seed data
│   │   ├── models/         # SQLAlchemy models (SQLite with WAL mode and foreign keys)
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── services/       # VectorStore (Chroma/TF-IDF), Retrieval, Generator, Cache, Session, Detector, Worker, PDF Exporter
│   │   └── main.py         # FastAPI application with lifecycle worker and static asset serving
│   └── tests/              # 24 Unit, integration, regression, and Playwright E2E browser tests
├── frontend/               # React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts, Lucide Icons
├── scripts/                # Startup, seed, and regression CLI tools
├── Dockerfile              # Multi-stage production container
└── render.yaml             # Render Blueprint specification with persistent disk
```

### Two Answer Modes
1. **Local Extractive Mode (Deterministic, Default):**
   - Extracts supported sentences strictly from permitted retrieved chunks.
   - Fully operational offline with zero paid API keys or external quotas.
   - Deterministic and verified across all automated test suites.
2. **Live Gemini Mode:**
   - Server-side integration using official Google GenAI Python SDK (`google-genai`).
   - Configured via `GEMINI_API_KEY` and `GEMINI_MODEL`.
   - Includes admin-only credential-safe connection test, rate-limit handling, and grounded citations.
   - Never silently falls back if an error occurs.

---

## 3. Quick Local Startup

### Prerequisites
- Python 3.11+ (Python 3.13 verified)
- Node.js 18+ (Node 24 verified)
- Git

### One-Command Startup (Native Windows PowerShell)
```powershell
.\scripts\run_dev.ps1
```

### One-Command Startup (macOS / Linux)
```bash
chmod +x scripts/run_dev.sh
./scripts/run_dev.sh
```

### Access Points
- **Web Dashboard:** [http://localhost:8000](http://localhost:8000) (or `http://localhost:5173` with Vite dev proxy)
- **API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### Default Seeded Credentials
| Role | Username | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@ForgetCheck2026!` | User management, documents, full synthetic lab, system diagnostics |
| **Auditor** | `auditor` | `Auditor@ForgetCheck2026!` | Synthetic suites, trace explorer, controlled replay, formal audit report exports |
| **Member** | `member` | `Member@ForgetCheck2026!` | Grounded Assistant Playground for permitted documents and personal sessions |

---

## 4. 3-Minute Interview Demonstration Script

Follow this sequence to demonstrate ForgetCheck's capabilities:

1. **Sign In (`/login`):**
   - Click the "Admin" shortcut button and sign in to view the Overview dashboard.
2. **Launch the Guided Demo (`/demo`):**
   - Click **"Run Guided Demo"** -> **"Start Step-by-Step Execution"**.
   - *Phase 1 (Baseline):* An authorized HR manager asks for Ravi's compensation. The system answers: *"Ravi's monthly salary is INR 90,000"* (`CANARY-HR-78923-SAL`).
   - *Phase 2 (Mutation):* The document is deleted and tombstoned in the database.
   - *Phase 3 (Fault Injection):* The runner exercises a stale vector index fault as an unauthorized employee.
   - *Phase 4 (Leak Detection):* The detector flags **LEAK DETECTED** with exact canary attribution.
   - *Phase 5 (Controlled Replay):* Click **"Verify Suspected Source"** with vector retrieval suppressed -> the leak converts to **BLOCKED**, proving root cause!
   - *Phase 6 (Corrected Rerun):* Click **"Rerun with Corrected Secure Pipeline"**.
   - *Phase 7 (Assurance):* The system blocks the secret while **simultaneously answering positive controls** (*"CarePlus Platinum health insurance"*).
3. **Inspect Traces & Audit Reports (`/runs` & `/reports`):**
   - Open the completed audit run and download the **Formal PDF Audit Report**.

---

## 5. Automated Verification Suite

Run all 24 automated unit, integration, and Playwright browser tests:

```bash
# Run backend pytest suite + Playwright E2E browser tests
pytest backend/tests -v

# Run standalone CLI regression test
python scripts/run_regression.py
```

### Test Results
```
backend/tests/test_auth.py ......................... [PASSED]
backend/tests/test_deletion_semantics.py ........... [PASSED]
backend/tests/test_documents.py .................... [PASSED]
backend/tests/test_leak_detector.py ................ [PASSED]
backend/tests/test_synthetic_faults.py ............. [PASSED]
backend/tests/test_reports.py ...................... [PASSED]
backend/tests/test_e2e_browser.py .................. [PASSED]

24 passed in 21.65s (100% pass rate)
```

---

## 6. Docker & Render Cloud Deployment

### Docker Compose
```bash
docker compose up --build
```

### Render Deployment (`render.yaml`)
ForgetCheck is pre-configured for a single-service Docker deployment on Render with persistent disk storage:
1. Connect GitHub repository `anilkumargadi27-hub/RAG-Deletion-Tester` to Render.
2. Select Blueprint deployment using `render.yaml`.
3. Persistent disk mounts `/var/data` for SQLite database, Chroma vector store, and report artifacts.
4. Health check endpoint: `/health`.

---

## 7. License
Apache 2.0. Built for robust RAG lifecycle verification.
