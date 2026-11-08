# TracePilot — AI-Powered Error & Log Intelligence Platform

TracePilot is an enterprise-grade AI debugging assistant and log intelligence platform powered by Google Gemini. It ingests complex software exceptions, stack traces, and application logs to produce structured, verified, machine-readable debugging reports.

---

## 1. Architecture Overview

TracePilot follows a decoupled, security-first full-stack architecture:

```
┌────────────────────────────────────────────────────────┐
│             React + Vite Frontend (SPA)                │
│    (Developer UI, Error Input, Presets, Report Cards)   │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP REST / Server-Sent Events (SSE)
                            ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Backend (app/api/server.py)        │
│   (/api/health, /api/debug, /api/debug/stream, ...)    │
└───────────────────────────┬────────────────────────────┘
                            │ Reuses Existing Backend Engine
                            ▼
┌────────────────────────────────────────────────────────┐
│               TracePilot Core Services                 │
│  • Input Validation & Normalization (app/input/)       │
│  • Heuristic Secret Redaction (app/input/redactor.py)  │
│  • Prompt Construction (app/prompting/)                │
│  • 2-Model Primary/Fallback Client (app/llm/)          │
│  • Streaming & Telemetry (app/llm/streaming.py)        │
│  • Schema Parsing & Validation (app/schemas/)          │
│  • Verified Pricing Cost Analyzer (experiments/)       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Key Features

- **Strict Two-Model Failover Architecture**:
  - **Primary Model**: `gemini-3.5-flash-lite` (fast, cost-effective standard diagnosis).
  - **Fallback Model**: `gemini-3.5-flash` (automatic failover for quota exhaustion, rate limits, timeouts, or truncated responses).
  - Fail-fast boundary for non-recoverable errors (401 authentication and 400 bad request fail immediately without wasting API budget).
- **Defense-in-Depth Input Security**:
  - Regex secret redaction for API keys, passwords, database URIs, Google API keys, AWS keys, GitHub PATs, JWTs, and private keys.
  - Untrusted data delimitation (`UNTRUSTED_DATA_START` ... `UNTRUSTED_DATA_END`) to isolate raw user traces from model system instructions.
- **Pydantic Structured Output Schema**:
  - Every response is validated against the [`DebuggingReport`](file:///c:/Users/mukesh/Documents/Gen%20ai/LLM%20mini%20projects/Trace%20Pilot%20week%202/app/schemas/debugging_report.py) schema (Error Info, Summary, Grounded Evidence, Root Causes, Debugging Steps, Suggested Fix, Verification, Confidence & Review).
- **Dual Execution Modes**:
  - **Synchronous REST**: Instant JSON responses with validated schema and usage telemetry.
  - **Real-Time Streaming (SSE)**: Incremental text streaming with buffer discard on failover and strict post-stream Pydantic validation.
- **Developer-Focused UI / UX**:
  - Single-page application built with React + Vite.
  - Preset benchmark scenarios across Python, JavaScript, PostgreSQL, HTTP, and Application Logs.
  - Evaluation Lab dashboard rendering real Phase 9 benchmark metrics and head-to-head model comparisons.

---

## 3. Technology Stack

- **Backend**: Python 3.14+, FastAPI, Uvicorn, Google GenAI SDK, Pydantic v2, python-dotenv.
- **Frontend**: React 18, Vite 5, Vanilla CSS Design System (no heavy UI framework bloat).
- **Testing & Quality**: pytest, httpx, Ruff.

---

## 4. Folder Structure

```
Trace Pilot week 2/
├── app/
│   ├── api/                     # FastAPI web server and request/response schemas
│   │   ├── schemas.py
│   │   └── server.py
│   ├── input/                   # Input validation, normalization, and secret redaction
│   │   ├── preprocessor.py
│   │   ├── redactor.py
│   │   └── validators.py
│   ├── llm/                     # Gemini client, retry backoff, streaming, exceptions
│   │   ├── api_handler.py
│   │   ├── client.py
│   │   ├── exceptions.py
│   │   ├── logger.py
│   │   ├── model_config.py
│   │   ├── response_handler.py
│   │   ├── retry_handler.py
│   │   └── streaming.py
│   ├── prompting/               # System instructions and isolated user messages
│   │   ├── system_prompts.py
│   │   └── user_messages.py
│   ├── schemas/                 # Pydantic structured schemas
│   │   └── debugging_report.py
│   └── main.py                  # Core pipeline entrypoint
├── data/
│   └── benchmark_inputs.py      # Standardized 10-case debugging benchmark suite
├── experiments/                 # Model comparison, parameter lab, cost and evaluation engines
│   ├── cost_analyzer.py
│   ├── evaluation_engine.py
│   ├── model_comparison.py
│   └── quality_evaluator.py
├── frontend/                    # React + Vite developer dashboard
│   ├── src/
│   │   ├── components/          # Navbar, ErrorInput, DebugReport, EvaluationView
│   │   ├── services/            # API client service
│   │   ├── App.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── output/                      # Generated evaluation reports and machine-readable metrics
│   ├── debugging_evaluation_results.json
│   └── phase_9_evaluation_report.md
├── tests/                       # 124 unit and integration tests (zero live API calls)
│   ├── test_api_server.py
│   ├── test_evaluation_engine.py
│   ├── test_reliability_security.py
│   ├── test_streaming_engine.py
│   └── test_structured_engine.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 5. Prerequisites

- Python 3.10+ (tested on Python 3.14)
- Node.js 18+ (tested on Node v24.13.0) and npm 9+
- A Google Gemini API Key

---

## 6. Installation & Setup

### A. Backend Setup
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate       # On Windows PowerShell
   # source .venv/bin/activate    # On Linux / macOS
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment Variables:
   Copy `.env.example` to `.env` and fill in your Gemini API key:
   ```bash
   cp .env.example .env
   ```
   Values in `.env`:
   ```ini
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.5-flash-lite
   GEMINI_MODEL_FALLBACK=gemini-3.5-flash
   GEMINI_REQUEST_TIMEOUT_SECONDS=30
   GEMINI_MAX_RETRIES=2
   GEMINI_RETRY_BASE_DELAY=1.0
   ```

### B. Frontend Setup
1. Navigate to the `frontend/` directory and install dependencies:
   ```bash
   cd frontend
   npm install
   ```

---

## 7. Running the Application

### 1. Launch the Backend Server
From the project root:
```bash
.\.venv\Scripts\uvicorn.exe app.api.server:app --host 127.0.0.1 --port 8000 --reload
```
The REST API will be available at `http://127.0.0.1:8000`. Interactive OpenAPI documentation is accessible at `http://127.0.0.1:8000/docs`.

### 2. Launch the Frontend Development Server
In a separate terminal:
```bash
cd frontend
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## 8. API Endpoints Documentation

| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| `GET` | `/api/health` | Service health status and configured model names | None | `HealthResponse` |
| `GET` | `/api/examples` | 10 benchmark test presets for instant testing | None | `list[ExampleCase]` |
| `GET` | `/api/evaluation` | Real Phase 9 benchmark evaluation results | None | `EvaluationResponse` |
| `POST` | `/api/debug` | Synchronous error analysis and structured validation | `DebugRequest` | `DebugResponse` |
| `POST` | `/api/debug/stream` | Server-Sent Events (SSE) streaming endpoint | `DebugRequest` | `text/event-stream` |

---

## 9. Testing & Code Quality

Run the complete automated test suite (all 124 tests are fully mocked; zero live Gemini API calls):
```bash
pytest -v
```

Run code formatting and linting:
```bash
ruff check app experiments tests
```

Build the frontend for production:
```bash
cd frontend
npm run build
```

---

## 10. Security & Methodological Guarantees

- **No Code Execution**: TracePilot strictly generates static debugging advice. Suggested code snippets or fix scripts are never executed via `eval()`, `exec()`, or subprocesses.
- **Client-Side Secret Isolation**: All Gemini API interactions, keys, and environment variables are strictly encapsulated in the Python backend. The browser never receives or stores API credentials.
- **Buffer Cleansing on Streaming Failover**: If the primary stream fails midway, partial chunks are completely discarded before fallback generation begins.
- **Ground-Truth Distinction**: Deterministic rule-based evaluation metrics (Accuracy, Precision, Recall, Macro-F1) are strictly segregated from advisory LLM-judge scores.

---

## 11. Current Limitations

1. **Static Analysis Only**: Recommendations are derived from static trace inspection without active access to the user's local filesystem or runtime environment.
2. **Heuristic Redaction**: Regex-based redaction provides strong defense-in-depth, but cannot mathematically guarantee detection of high-entropy proprietary secrets without organization-level ingestion gates.
3. **In-Memory History**: Session history is maintained in local UI state; persistent historical storage is omitted by design to guarantee developer credential privacy.
