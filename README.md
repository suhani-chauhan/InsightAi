# InsightMind AI

**AI-Powered Data Intelligence, Smart Data Cleaning, Exploratory Analysis & AutoML.**

Ask your database questions in plain English and get SQL, results, charts, and dashboards back in seconds — then send any result into a full **Data Science workspace** for profiling, quality analysis, smart cleaning, EDA, and real machine-learning models.

> InsightMind AI evolved from **QueryMind**, an AI-powered database-analytics platform. QueryMind's entire feature set — the LangGraph database agent, NL→SQL, dashboards, query library, scheduling — is intact. Everything under **Insight Studio** below is the new Data Intelligence layer built on top of it.

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-Ready-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Supabase-Auth%20%2B%20Data-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase" />
</p>

<p align="left">
  <img src="https://img.shields.io/badge/LangGraph-Agent%20Orchestration-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Google%20Gemini-LLM-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Celery-Background%20Jobs-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/Redis-Broker-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Vite-Build-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy" />
</p>

---

## 🎥 Demo Video

▶️ **[Watch the full product demo](https://youtu.be/X7novGZY15E)** — natural-language questions turning into SQL, live results, auto-selected charts, saved queries, and dashboards.

---

## 💡 What is InsightMind AI?

InsightMind AI is a **full-stack AI Data Intelligence platform** that connects databases and query results to intelligent data profiling, automated data cleaning, exploratory analysis, machine learning, predictive insights, dashboards, and natural-language analytics.

**The BI half (from QueryMind):** connect a real database, type a question like *"How many support tickets are there per category, broken down by priority?"*, and a **tool-calling LangGraph agent** explores your schema, writes the SQL, validates it, runs it safely (read-only), and hands back the answer with an explanation, a results table, and an automatically chosen chart. Under the hood: a 12-tool agent loop with budget enforcement, context compaction, error-recovery ladders, and a deterministic fallback pipeline.

**The Data Science half (Insight Studio):** click **Analyze Dataset** on any query result and step through a guided workflow — **Dataset → Quality → Clean → Explore → ML → Report**. It profiles the data, scores its quality, recommends (never blindly applies) cleaning operations with a before/after preview and undo history, runs EDA with grounded insights, and trains and compares real scikit-learn models with leakage-safe preprocessing, feature importance, and a live prediction form.

### The AI principle

The LLM is an **orchestrator and explanation layer only**. Every number you see — statistics, quality scores, cleaning impact, model metrics, feature importance — is computed deterministically in Python (pandas / numpy / scikit-learn). The LLM is given those computed results and asked to explain them; it never calculates analytics and never invents figures.

### The problem it solves

Getting an answer out of a database normally requires you to:

1. Know where the data lives and how tables relate
2. Write correct SQL by hand
3. Verify the query is safe and performant
4. Interpret raw rows into something a human can act on
5. Rebuild the same reports over and over

InsightMind AI collapses all five steps into a single conversation, while keeping everything **auditable** — every agent step (schema search, table inspection, validation, execution) is traceable in the UI via "Show Agent Steps." From there, one click sends the result into Insight Studio for cleaning, EDA, and modelling.

---

## 💬 AI Chat — from question to insight

Ask a question, watch the agent reason through your schema, and get back explained SQL plus results.

![Natural language to SQL with explanation and agent steps](demos/chat_1.png)

The agent explains *how* it derived the query — which tables it joined, how it grouped, and why:

![Complex query with HAVING clause and detailed explanation](demos/chatt_3.png)

Results render as a sortable table with execution time, and a chart is auto-selected to fit the data shape:

![Results table with average ratings and review counts](demos/chat_4.png)

Charts are interactive — hover for exact values, switch between Bar, Line, Pie, and Area with one click:

![Grouped bar chart with hover tooltips per ticket category](demos/chat_2.png)

Dual-axis charts are handled automatically when the metrics live on different scales:

![Dual y-axis chart comparing average rating vs review count](demos/chat_5.png)

Multi-grid KPI views break one answer into per-segment mini-dashboards:

![Multi-grid KPI breakdown by department](demos/chat_6.png)

---

## 📊 Dashboards — pin answers, keep them live

Any chat result can be added to a dashboard in one click. Widgets are drag-and-drop, resizable, and each one can switch its own chart type. Dashboards support runtime filters, PNG export, and scheduled refresh.

![Dashboard with line and bar widgets for order analytics](demos/Dashboard_1.png)

![Dashboard with project performance and salary breakdowns](demos/Dashboard_2.png)

---

## 📚 Query Library — save, organize, schedule

Every useful query can be saved into folders, tagged, re-run, and scheduled. The library shows the SQL, run history, and last-run status per query. Scheduled queries execute in the background via Celery workers.

![Query library with folders, saved SQL, and scheduling](demos/Library_1.png)

---

## 🔌 Connections — real databases, safely

Connect PostgreSQL databases (including cloud-hosted, e.g. Supabase poolers) through a guided wizard with SSL and SSH-tunnel support. Each connection gets a live health check, latency telemetry, and a fully mapped schema ledger.

![Connection detail with schema ledger, health, and telemetry](demos/connection_1.png)

![Guided source registration wizard with credentials step](demos/connection_2.png)

---

## 🧪 Insight Studio — the Data Science workspace

Start from any of four sources — a **query result** (one click from chat), a **CSV/TSV upload**, a **database table** (connection → table, read once, read-only), or the built-in **demo dataset** — and step through a guided Data Science workflow. Nothing here touches your source database; the workspace operates on a bounded in-memory **analysis copy**.

**Workflow:** `Dataset → Quality → Clean → Explore → ML → Report`, with an **Ask InsightMind** panel available at every step.

| Step | What it does |
|------|--------------|
| **Dataset** | Row/column counts, inferred column kinds (numeric / categorical / datetime / boolean / text), per-column stats (missing %, unique, mean/median/mode, quantiles, IQR, outliers, skew, histogram), sample rows |
| **Quality** | 7 issue detectors — missing values, duplicates, numeric/date-as-string, categorical inconsistency (`India`/`india`/`INDIA`), outliers (IQR + modified z-score), constant / near-zero-variance columns, potential target leakage. Explainable **0–100 quality score** with a per-dimension breakdown |
| **Clean** | An AI recommendation engine turns each issue into a concrete operation with **problem / solution / reason / expected impact**. *Recommendation mode* (approve each) or *Smart Clean* (apply high-confidence, low-risk fixes). Dry-run **preview** with before/after and a column-level diff. Exact **undo / reset** history. 11 operations: trim whitespace, standardize categories, to-numeric, to-datetime, drop duplicates, drop column, drop rows, impute (mean/median/mode/constant/KNN, auto-selected by distribution), handle outliers (keep/remove/cap/flag), group rare categories, map categories |
| **Explore** | Numeric & categorical summaries, correlation matrix + heatmap, 7 chart types (histogram, box, bar, pie, scatter, line, correlation heatmap), and **auto-insights grounded in the computed statistics** — skew, imbalance, correlation, group differences. Uses "associated with", never "causes" |
| **ML** | Auto-detects classification vs regression (user can override). Trains **5 classifiers / 6 regressors** inside an sklearn `Pipeline` + `ColumnTransformer` fitted **only on the training split** — no leakage. Stratified split, 5-fold cross-validation, model comparison ranked by the task-appropriate metric, confusion matrix / ROC-AUC / R² / RMSE, native or permutation **feature importance** (one-hot columns collapsed to their source feature), and a dynamic **prediction form** that runs inputs back through the exact fitted pipeline |
| **Report** | Assembles dataset overview, quality summary, cleaning operations, before/after, EDA findings, ML comparison, best model, feature importance, and recommendations — exportable as standalone HTML |

**Ask InsightMind** answers natural-language questions ("What should I clean first?", "Which model performed best and why?") grounded strictly in the session's computed artifacts. If the LLM is unavailable the panel degrades gracefully — the computed analysis on the page stays accurate.

A safe, clearly-labelled **demo dataset** (employee attrition, seeded with missing values, duplicates, inconsistent categories, and salary outliers) lets you try the whole workflow without connecting a database.

---

## ✨ Feature Overview

| Area | What you get |
|------|--------------|
| **AI Agent** | Tool-calling LangGraph agent with 12 tools: schema search, table inspection, relationship discovery, data profiling, row counting, SQL validation, live preview queries, and more |
| **Data profiling** | Deterministic pandas/numpy profiling — dataset- and column-level stats, type inference, constant/near-constant/high-cardinality detection |
| **Data quality** | 7 issue detectors + an explainable 0–100 quality score with per-dimension breakdown; every figure computed, not estimated |
| **Smart cleaning** | AI recommendations with reasons, dry-run preview with before/after + column diff, Smart-Clean auto-apply for low-risk fixes, exact undo/reset history; source database never modified |
| **EDA** | Numeric/categorical summaries, correlations, 7 chart types, auto-insights grounded in computed statistics |
| **AutoML** | Real scikit-learn training (5 classifiers / 6 regressors), leakage-safe `Pipeline`+`ColumnTransformer`, stratified split, 5-fold CV, model comparison, feature importance, live prediction form |
| **Safety** | Read-only enforcement, write-intent refusal, query timeouts, row-limit wrapping, live-query caps, credential encryption (Fernet); Data Science runs on bounded analysis copies scoped to the owner |
| **Resilience** | Call/time budgets with salvage finish, mechanical no-LLM fallback, context compaction for long agent runs, difflib-powered error suggestions, repeat-tool-call detection ladder |
| **Chat UX** | Explanations with every query, expandable agent trace, editable SQL with re-run, pinned results, session history per connection |
| **Visualization** | Auto-selected chart types, dual-axis support, grouped/single/multi-grid modes, interactive tooltips, CSV export |
| **Dashboards** | Drag-and-drop grid, per-widget chart switching, runtime filters, live refresh, PNG export, share links |
| **Library** | Folders, tags, duplicate detection, scheduling (daily/weekly/monthly), run history, public template cloning |
| **Multi-user** | Supabase JWT auth with HTTP-only cookies, per-owner data isolation enforced at the repository layer |
| **Background jobs** | Celery + Redis + Beat for scheduled query runs and dashboard widget refresh, with dispatch locks |

---

## 🏗️ Architecture

```mermaid
flowchart LR
    U[User] --> FE[React 19 + Vite Frontend]
    FE --> API[FastAPI Routes]

    API --> SVC[Service Layer]
    SVC --> AGENT[LangGraph DB Agent]
    SVC --> PIPE[NL-to-SQL Fallback Pipeline]
    SVC --> QE[Query Engine]
    SVC --> REPO[Repositories]
    SVC --> WORKERS[Celery Workers]
    SVC --> DS[Data Science Engine]

    DS --> PANDAS[pandas / numpy / scikit-learn]
    DS --> LLMX[LLM: explanation layer only]
    AGENT --> LLM[Gemini / Groq via LangChain]
    PIPE --> LLM
    LLMX --> LLM
    AGENT --> QE
    QE --> EXTDB[(Connected PostgreSQL DBs)]
    QE -. query result .-> DS
    REPO --> SB[(Supabase / App DB)]
    WORKERS --> SVC
```

The Data Science engine is fully deterministic: `pandas` / `numpy` / `scikit-learn` compute every statistic, cleaning transform, quality score, and model metric. The LLM only receives those computed results and explains them.

### How a chat request flows

1. **Deterministic shortcuts first** — schema commands like "show all tables" are answered instantly from the cached catalog, with zero LLM calls. Write-intent messages are refused outright.
2. **Agent loop** — the LangGraph agent iterates `think → call tool → observe`, exploring schema, validating SQL, and profiling data. Budgets cap tool calls and wall-clock time; when exceeded, a salvage finish extracts the best answer so far.
3. **Context compaction** — long tool transcripts are compacted mid-run so the agent keeps its scratchpad without blowing the context window.
4. **Fallback pipeline** — if the agent fails, a simpler schema-prompted generation pipeline takes over, and the failed agent trace is preserved for debugging.
5. **Execution** — SQL runs through the query engine with read-only checks, timeouts, and row limits, then results are persisted to the chat session with full metadata.

### Backend layout

```text
backend/app/
  api/            # FastAPI routes, request/response schemas, auth deps
  core/           # config, secrets, logging, CORS, error handling
  db/             # ORM models, repositories, session management
  services/       # chat, connections, library, dashboards, billing, auth,
                  #   data_science_service (in-memory analysis sessions)
  agents/         # db_agent (tool-calling loop), nl_to_sql, visualization
  data_science/   # profiling, quality, cleaning, eda, ml, report, demo_data,
                  #   insights_llm — deterministic pandas/numpy/sklearn engine
  integrations/   # LLM client (Gemini/Groq), Supabase
  query_engine/   # execution, schema inspection, safety wrapping
  workers/        # Celery app, beat scheduler, background jobs
```

### Data Science API

All routes are owner-scoped and operate on an in-memory analysis copy:

```text
POST /api/data-science/sessions            # from a query result {columns, rows}
POST /api/data-science/sessions/upload     # from CSV/TSV text {name, content, format}
POST /api/data-science/sessions/from-table # from a DB table {connection_id, table, db_schema, limit}
POST /api/data-science/sessions/demo       # built-in demo dataset
POST /api/data-science/sessions/{id}/profile
POST /api/data-science/sessions/{id}/quality
POST /api/data-science/sessions/{id}/cleaning/recommendations | preview | apply | undo | reset
POST /api/data-science/sessions/{id}/eda
POST /api/data-science/sessions/{id}/ml/detect-task | train | predict
POST /api/data-science/sessions/{id}/report
POST /api/data-science/sessions/{id}/ask
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | React 19, TypeScript, Vite, React Router, Zustand, Recharts, react-grid-layout, Lucide |
| **Backend** | Python 3.11, FastAPI, Pydantic v2, Uvicorn |
| **AI / Agents** | LangGraph, LangChain, Google Gemini (primary), Groq (switchable via `LLM_PROVIDER`) |
| **Data Science** | pandas, numpy, scikit-learn — all profiling, cleaning, EDA, and model training |
| **Data & Auth** | Supabase (Postgres + JWT auth), SQLAlchemy, psycopg2 |
| **Query Execution** | SQLAlchemy engines per connection, SSH tunneling, schema introspection |
| **Background Jobs** | Celery, Redis, Celery Beat |
| **Testing** | Pytest — 460+ backend tests covering agent budgets, compaction, tools, safety, repositories, provider switching, and the full Data Science engine + API |

---

## 🧠 Engineering Highlights

These are the parts I'm most proud of as an engineer:

- **Resilient agent design** — the agent never just "gives up." Budget exhaustion triggers an LLM salvage finish; if *that* fails to produce valid JSON, a mechanical salvage assembles an answer from the trace with zero LLM calls.
- **Context compaction with round-pairing invariants** — tool-call/response pairs are compacted together so the message history stays API-valid while shrinking dramatically.
- **Error recovery ladder** — repeated failing tool calls escalate through warn → skip-with-explanation → force-finish, with difflib-based "did you mean" suggestions on schema errors.
- **Defense in depth for SQL safety** — regex write-detection at the chat boundary, read-only validation in the engine, statement timeouts, and automatic row-limit wrapping.
- **Provider abstraction** — swapping Gemini ↔ Groq is one env var; message-content normalization handles each provider's response shape differences.
- **Owner-scoped repositories** — every query filters by `owner_id` at the data layer, verified by dedicated multi-user isolation tests.

---

## 🚀 Local Setup

### 🐳 Quick start with Docker (recommended)

The whole stack — API, Celery worker, beat scheduler, Redis, and the frontend — runs with one command. You only need Docker installed, plus two free accounts you bring yourself:

- A **Supabase project** (auth + app data) — [supabase.com](https://supabase.com), free tier
- A **Google Gemini API key** (or Groq) — [aistudio.google.com](https://aistudio.google.com), free tier

```bash
git clone https://github.com/danishali778/query-mind.git
cd query-mind

# Fill in your Supabase + LLM keys in both files:
copy backend\.env.example backend\.env      # cp on macOS/Linux
copy frontend\.env.example frontend\.env

docker compose up --build
```

The backend applies database migrations automatically on startup. Open **http://localhost:5173** — the API is at http://localhost:8000.

> Redis URLs are handled for you inside compose; the values in `.env.example` only matter for the manual setup below.

### Manual setup

#### Prerequisites

- Node.js 18+
- Python 3.11+
- A Supabase project
- A Google Gemini API key (or Groq)
- Redis 7+ (optional in dev — rate limiting falls back to in-memory)

### 1. Clone

```bash
git clone https://github.com/danishali778/query-mind.git
cd query-mind
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # then fill in your keys
uvicorn app.main:app --reload
```

Optional — background workers for scheduled queries (separate terminals):

```bash
celery -A app.workers.worker:app worker --loglevel=info --queues default,scheduled,templates --pool=solo
celery -A app.workers.beat:app beat --loglevel=info
```

API runs at `http://127.0.0.1:8000`.

### 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

App runs at `http://127.0.0.1:5173`.

### Key environment variables

**`backend/.env`**

```env
# App
APP_ENV=development
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174

# LLM provider — gemini or groq
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash
AGENT_MODE=tools

# Supabase (auth + app data)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
APP_DATABASE_URL=postgresql+psycopg2://postgres:password@db.your-project-id.supabase.co:5432/postgres

# Connection credential encryption
ENCRYPTION_KEY=your-fernet-key

# Background jobs (optional in dev)
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

**`frontend/.env`**

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_SUPABASE_URL=your-supabase-project-url
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
```

---

## 🧪 Testing

```bash
cd backend
python -m pytest

# Data Science engine + API only
python -m pytest tests/test_data_science_*.py
```

The suite covers the agent loop, tool behavior, budget/salvage paths, context compaction, LLM provider switching, SQL safety, schema commands, repositories with multi-user isolation, and API routes. The Data Science suites (`test_data_science_profiling / quality / cleaning / ml / api`) verify computed statistics, deterministic quality scoring, cleaning operations and undo history, classification/regression detection, leakage-safe training, real model metrics, feature importance, and that analysis sessions never mutate a database and stay scoped to their owner.

---

## 🗺️ Roadmap

- **Deeper analytical reasoning** — "Why is revenue dropping?" answered with multi-query investigations and narrative reports
- **Pin Data Science metrics to dashboards** — quality score, best-model F1, top feature, EDA charts as first-class widgets
- **Background Data Science jobs** — move large-dataset profiling, EDA, and model training onto the existing Celery workers with progress streaming
- **Excel (.xlsx) upload** — CSV/TSV upload ships now; Excel needs `openpyxl`
- **More database engines** — MySQL support is scaffolded; broader engine coverage planned
- **Collaboration** — shared workspaces, dashboard permissions, and audit trails

---

## 📄 Notes

- `backend/app` is the canonical backend package; `backend/main.py` is a thin convenience wrapper.
- Data Science analysis sessions are held **in memory** — bounded (8 per user, 3-hour TTL), owner-scoped, and never persisted or written back to a database. They do not survive a server restart and are not shared across worker processes; this fits the synchronous single-analyst workflow and keeps the source data untouched.
- Adding the Data Science layer introduces three backend dependencies: `pandas`, `numpy`, `scikit-learn` (see `backend/requirements.txt`). No new environment variables are required — the LLM narration layer reuses the existing `LLM_PROVIDER` / provider-key configuration and degrades gracefully when unavailable.
- All demo media lives in the [`demos/`](demos/) folder.
