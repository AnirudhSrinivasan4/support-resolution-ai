# Intelligent Support Ticket Resolution Assistant

A production-minded prototype for helping customer support agents analyze incoming complaints, retrieve relevant domain evidence, and review grounded resolution drafts. The system is designed to deterministically abstain or recommend escalation when authoritative knowledge evidence is missing or insufficient.

> [!NOTE]
> This project is a production-minded prototype and demonstration system, not a production-ready application.

---

## Quick Start (Windows Demo)

Run the primary automated demo startup script from the repository root:

```cmd
.\start-app.bat
```

### Prerequisites
- **Docker Desktop**: Must be installed and running. Provides containerized PostgreSQL (with `pgvector`) and the FastAPI backend service.
- **Node.js & npm**: Required to build and run the React/Vite agent frontend UI.
- **Ollama**: Must be running locally on the host machine (`http://localhost:11434`) with the `qwen2.5:3b` model installed.
- **Git**: For source code management.

To pull the required Ollama model prior to running the demo:
```cmd
ollama pull qwen2.5:3b
```

### What `start-app.bat` does
1. **Checks Docker**: Verifies Docker daemon and Docker Compose availability.
2. **Checks Ollama**: Queries Ollama API on port 11434 to confirm it is reachable.
3. **Verifies Model**: Ensures `qwen2.5:3b` is present in local Ollama storage.
4. **Starts Backend Services**: Executes `docker compose up -d` to launch PostgreSQL 16 (`pgvector`) and the FastAPI application container.
5. **Waits for FastAPI Health**: Polls `http://localhost:8000/healthz` until the backend API reports status `ok`.
6. **Starts React/Vite Frontend**: Opens a new command window and runs `npm run dev` inside `frontend/`.
7. **Launches UI**: Automatically opens your default browser to `http://localhost:5173/`.

### Useful URLs
- **Agent UI Workspace**: [http://localhost:5173](http://localhost:5173)
- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Endpoint**: [http://localhost:8000/healthz](http://localhost:8000/healthz)

---

## Ollama Host & Docker Networking

The demo environment combines containerized infrastructure with local host LLM execution:

- **Host Machine**: Runs Ollama daemon serving `qwen2.5:3b` at `http://localhost:11434`.
- **Docker Containers**: Runs PostgreSQL (`db`) and FastAPI (`api`).

### `host.docker.internal` Bridge
Inside the Dockerized FastAPI container, external network calls to Ollama route to `http://host.docker.internal:11434/v1`. `host.docker.internal` is Docker's special DNS name that resolves container traffic to the host operating system's loopback interface.

### Benefits of Local Ollama Setup
- **Offline & Local Execution**: Enables complete demo execution without cloud dependencies or paid API keys.
- **Data Locality & Privacy**: Complaint text and support evidence remain strictly local.
- **Zero API Costs & Limits**: Eliminates rate limits and per-token charges during development and review.
- **Reproducible Demo**: Pinned `qwen2.5:3b` model behavior ensures deterministic local demonstration.

---

## End-to-End System Architecture

```
                                +-----------------------------------+
                                |    React + Vite Agent UI (5173)   |
                                +-----------------+-----------------+
                                                  |
                                                  v
                                +-----------------+-----------------+
                                |     FastAPI POST /v1/resolutions  |
                                +-----------------+-----------------+
                                                  |
                                                  v
                                +-----------------+-----------------+
                                |  Stage 1: Complaint Understanding |
                                |  (intent, category, product,      |
                                |   severity, sentiment)            |
                                +-----------------+-----------------+
                                                  |
                                                  v
                                +-----------------+-----------------+
                                |   Stage 2: Hybrid RRF Retrieval   |
                                |   (Semantic Vector + Full-Text)   |
                                +--------+----------------+---------+
                                         |                |
                     +-------------------+                +-------------------+
                     |                                                        |
                     v                                                        v
   +---------------------------------+                      +-----------------------------------+
   | 45-Doc Telecom KB (Authoritative)|                      | 61,765 Historical Tickets         |
   | Synthetic procedural guidance   |                      | Heterogeneous support context     |
   +-----------------+---------------+                      +-----------------+-----------------+
                     |                                                        |
                     +-------------------+                +-------------------+
                                         |                |
                                         v                v
                                +--------+----------------+---------+
                                | Stage 3: Bounded Grounded RAG     |
                                +-----------------+-----------------+
                                                  |
                                                  v
                                +-----------------+-----------------+
                                | Stage 4: Ollama LLM (qwen2.5:3b)  |
                                | via OpenAI-compatible adapter     |
                                +-----------------+-----------------+
                                                  |
                                                  v
                                +-----------------+-----------------+
                                | Stage 5: Citation & Abstention    |
                                | Validation Guardrails             |
                                +-----------------+-----------------+
                                                  |
                                                  v
                                +-----------------+-----------------+
                                | Stage 6: React UI Workspace       |
                                | (Resolution Steps OR Abstention)  |
                                +-----------------------------------+
```

---

## Request Pipeline & Stage Breakdown

When an agent enters a complaint in the frontend UI or issues a `POST /v1/resolutions` request, the backend processes the request through six distinct pipeline stages:

### Stage 1: Complaint Understanding
Before performing evidence retrieval, `POST /v1/resolutions` invokes the complaint understanding parser (`app/services/complaint_understanding.py`). This stage extracts five structured taxonomy fields:
- `intent`: Specific customer objective (e.g., `esim_activation`, `connectivity_issue`, `billing_dispute`).
- `category`: Broad operational category (e.g., `esim`, `network`, `billing`).
- `product`: Targeted service/device product (e.g., `esim`, `broadband`, `mobile_data`).
- `severity`: Operational severity level (`low`, `medium`, `high`, `critical`, `unknown`). Deterministic overrides automatically mark complete outage reports and explicit security compromises as `high`.
- `sentiment`: Informational customer emotional state (`positive`, `neutral`, `frustrated`, `angry`, `negative`, `unknown`).

### Stage 2: Hybrid Retrieval & Fusion (RRF)
The service queries two database search channels in parallel:
1. **Semantic Vector Search**: Generates a 384-dimensional dense vector using `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` and queries PostgreSQL `pgvector` with HNSW cosine distance.
2. **Lexical Full-Text Search**: Builds a PostgreSQL full-text search vector over subject and body text using a GIN index, rewarding matching terms with `ts_rank_cd`.

The candidate rank lists are merged using **Reciprocal Rank Fusion (RRF)**:
$$\text{RRF Score} = \sum_{m \in \{\text{semantic}, \text{lexical}\}} \frac{1}{k + r_m}$$
where $k=60$ by default and $r_m$ is the candidate's one-based rank in modality $m$.

*Note: Cross-encoder reranking is NOT implemented in the current retrieval pipeline. Retrieval uses RRF candidate rank fusion; reranking exists only as an architectural abstraction / future design option.*

### Stage 3: Dual Evidence Corpus Segregation
The pipeline retrieves evidence from two strictly segregated sources:
- **Authoritative Telecom Knowledge Base**: Contains **45 synthetic-curated demonstration procedures** (`knowledge_base/seeds/v1/documents.json`). This corpus represents official, binding operational policy for telecom workflows (e.g., eSIM profiles, PUK resets, roaming provisioning).
- **Historical Support Ticket Corpus**: Contains **61,765 tickets** from a heterogeneous public customer-support dataset. It is **not telecom-specific**. Historical agent answers are treated as unverified, imperfect historical evidence and are explicitly prevented from overriding KB procedures.

### Stage 4: Grounded RAG Generation
The service constructs an LLM prompt containing only bounded, retrieved evidence context:
- KB evidence is placed under `AUTHORITATIVE KNOWLEDGE BASE EVIDENCE`.
- Historical ticket evidence is placed under `HISTORICAL SUPPORT CASE EVIDENCE`.
- Factual and procedural claims in the prompt are strictly restricted to the supplied evidence text.

### Stage 5: Ollama Local LLM Execution
The prompt is sent to Ollama running `qwen2.5:3b` via an OpenAI-compatible HTTP adapter (`LLMProvider`). The LLM returns a structured JSON payload containing a draft resolution summary, ordered action steps, procedural escalation guidance, and cited source IDs.

### Stage 6: Citation Validation & Abstention Guardrails
1. **Pre-Generation Abstention Check**: Before calling the LLM, the service evaluates retrieved KB evidence relevance. If no retrieved KB document satisfies either the minimum vector similarity floor (`RESOLUTION_MIN_KNOWLEDGE_SIMILARITY=0.40`) or lexical score floor (`RESOLUTION_MIN_KNOWLEDGE_LEXICAL_SCORE=0.50`), the system deterministically **abstains** (`abstained=true`) and returns escalation advice without invoking LLM generation.
2. **Post-Generation Citation Validation**: If generation proceeds, the service programmatically inspects every citation ID emitted by the LLM. It verifies that each ID exists in the actual retrieved candidate set, derives citation titles/types from source metadata, and rejects fictitious or unretrieved document references.

---

## React/Vite Frontend Workspace

The frontend (`frontend/`) provides an interactive React + Vite workspace designed for customer support agents:

- **API Health Badge**: Continuously monitors backend status via `GET /healthz` and displays a live connection status indicator (`API available` / `API unavailable`).
- **Complaint Input Form**: Allows agents to paste customer complaints and trigger resolution generation.
- **Triage Card (`UnderstandingCard`)**: Displays the five structured classification badges (`intent`, `category`, `product`, `severity`, `sentiment`).
- **Resolution & Action Steps (`ResolutionCard`)**: Displays the grounded resolution draft alongside numbered, step-by-step instructions.
- **Escalation Guidance (`EscalationCard`)**: Provides procedural escalation instructions for cases requiring human supervisor intervention.
- **Evidence & Citations (`EvidenceCard`)**: Lists validated evidence citations, distinguishing between authoritative KB procedures and historical support cases with source IDs and titles.
- **Abstention Card (`AbstentionCard`)**: Renders a clear warning card when KB evidence is insufficient, directing the agent to standard escalation protocols.

---

## Design Decisions

| Choice / Component | Engineering Rationale & Purpose |
| :--- | :--- |
| **PostgreSQL + pgvector** | Consolidates relational data, full-text lexical search (GIN index), and vector embeddings (HNSW index) within a single database system. Avoids operating a separate standalone search/vector cluster. |
| **Hybrid Retrieval** | Combines dense semantic vector search (for concept matching and paraphrased complaints) with keyword search (for exact technical identifiers like `E4037`, device models, and acronyms). |
| **Reciprocal Rank Fusion (RRF)** | Merges candidate rankings from semantic and lexical channels without requiring raw score normalization across incompatible scales (cosine distance vs. `ts_rank_cd`). |
| **Multilingual MiniLM** | Uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions, 50+ languages). Supports both German and English tickets in the historical corpus with a fast, locally run open model. |
| **Separate Telecom KB** | Keeps authoritative procedural guidance (45 synthetic-curated documents) isolated from heterogeneous historical customer support cases (61,765 tickets), ensuring unverified historical answers cannot override official policy. |
| **Ollama / Qwen (`qwen2.5:3b`)** | Provides a fast, local, lightweight open LLM behind an OpenAI-compatible API interface, enabling local offline demonstration without paid third-party API dependencies. |
| **Retrieval-Augmented Generation (RAG)** | Restricts LLM prompts to a bounded, retrieved set of evidence, keeping generated resolutions grounded in authoritative source text to prevent hallucination. |
| **Citation Validation** | Programmatically inspects generated response references and verifies every citation against the actual retrieved evidence set, rejecting fictitious or unretrieved document references. |
| **Abstention & Escalation** | Enforces deterministic vector similarity and lexical score floors before LLM generation. Automatically abstains or recommends escalation when retrieved knowledge evidence is insufficient. |

---

## Active API Endpoints

The FastAPI backend exposes the following active endpoints:

- `GET /healthz` - Health check returning `{"status": "ok"}`.
- `POST /v1/retrieval/semantic` - Dense vector nearest-neighbor search over historical tickets.
- `POST /v1/retrieval/hybrid` - Hybrid search (semantic + full-text RRF fusion) over historical tickets.
- `POST /v1/knowledge/search` - Hybrid RRF search over the authoritative telecom knowledge base.
- `POST /v1/complaints/understand` - Standalone complaint taxonomy classification (`intent`, `category`, `product`, `severity`, `sentiment`).
- `POST /v1/resolutions` - End-to-end grounded RAG resolution generation with retrieval, taxonomy classification, citation validation, and abstention checks.

*Note: Administrative or ingest endpoints such as `/v1/ingest`, `/v1/feedback`, or `/readyz` do not exist in the current codebase.*

---

## Configuration & `.env` Setup

Runtime settings are backed by `app/core/config.py`. Copy `.env.example` to `.env` to configure environment settings:

```bash
cp .env.example .env
```

### Key Environment Variables
- `APP_ENV`: Deployment environment (`development`).
- `DATABASE_URL`: PostgreSQL connection string (default in Compose: `postgresql+psycopg://support:local-development-only@db:5432/support`; host execution: `postgresql+psycopg://support:local-development-only@localhost:5432/support`).
- `EMBEDDING_MODEL`: Hugging Face model identifier (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`).
- `EMBEDDING_MODEL_REVISION`: Optional pinned commit SHA for reproducible embeddings.
- `SEMANTIC_CANDIDATE_LIMIT` & `LEXICAL_CANDIDATE_LIMIT`: Candidate pool sizes for historical ticket retrieval (default: `20`).
- `KNOWLEDGE_SEMANTIC_CANDIDATE_LIMIT` & `KNOWLEDGE_LEXICAL_CANDIDATE_LIMIT`: Candidate pool sizes for KB retrieval (default: `20`).
- `RRF_CONSTANT`: Reciprocal Rank Fusion constant $k$ (default: `60`).
- `LLM_PROVIDER`: LLM mode (`disabled` or `openai-compatible`). Set to `openai-compatible` for local Ollama.
- `LLM_BASE_URL`: Base URL for OpenAI-compatible endpoint (use `http://host.docker.internal:11434/v1` in Docker Compose or `http://localhost:11434/v1` on host).
- `LLM_MODEL`: LLM model name (`qwen2.5:3b`).
- `LLM_API_KEY`: API key for external providers (optional for local Ollama).
- `RESOLUTION_MIN_KNOWLEDGE_SIMILARITY`: Minimum vector similarity floor for KB evidence (default: `0.40`).
- `RESOLUTION_MIN_KNOWLEDGE_LEXICAL_SCORE`: Minimum lexical score floor for KB evidence (default: `0.50`).

> [!IMPORTANT]
> Secrets, credentials, `.env` files, and raw customer data must never be committed to Git repositories.

---

## Local Development & Ingestion Tooling

### 1. Host Database Setup & Migrations
```powershell
# Start PostgreSQL container
docker compose up -d db

# Install development Python package
pip install -e ".[dev]"

# Set database connection and apply Alembic migrations
$env:DATABASE_URL = "postgresql+psycopg://support:local-development-only@localhost:5432/support"
alembic upgrade head

# Run FastAPI backend locally
uvicorn app.main:app --reload
```

### 2. Historical Ticket Ingestion
Loads the `train` split of the **61,765 historical ticket** dataset into PostgreSQL:
```powershell
$env:DATABASE_URL = "postgresql+psycopg://support:local-development-only@localhost:5432/support"
python -m app.ingestion.cli "D:\College\customer-support-tickets"
```
*(For a bounded smoke test, pass `--limit 10`.)*

### 3. Historical Ticket Embeddings Generation
Generates 384-dimensional embeddings for ticket subject and body:
```powershell
pip install -e ".[embeddings,dev]"
$env:DATABASE_URL = "postgresql+psycopg://support:local-development-only@localhost:5432/support"
alembic upgrade head
python -m app.embeddings.cli --batch-size 64
```

### 4. Telecom Knowledge Base Ingestion
Ingests the 45-document synthetic-curated telecom knowledge base seed:
```powershell
pip install -e ".[embeddings,dev]"
$env:DATABASE_URL = "postgresql+psycopg://support:local-development-only@localhost:5432/support"
alembic upgrade head
python -m app.knowledge.cli
```

### 5. Evaluation Baseline CLI
Runs evaluation baselines across complaint understanding, retrieval, and abstention test suites:
```powershell
python -m app.evaluation.cli
```
Reports are written to `evaluation/reports/`. *Note: Baseline suites are smoke-testing tools for development, not production benchmark evidence.*

---

## Project Structure

- `app/domain`: Core domain models, taxonomy definitions, and port interfaces (`ports.py`).
- `app/ingestion`: Row validation, normalization, and CLI for historical ticket dataset ingestion.
- `app/embeddings`: Embeddings generation CLI and batch workers.
- `app/knowledge`: Telecom knowledge base models and ingestion CLI.
- `app/services`: Application orchestration (semantic retrieval, hybrid retrieval, complaint understanding, resolution generation).
- `app/infrastructure`: Concrete adapters for persistence (SQLAlchemy + pgvector), embeddings (SentenceTransformers), and LLM generation (OpenAI-compatible client).
- `app/api`: FastAPI HTTP endpoints and request/response models.
- `app/core`: Application configuration (`config.py`).
- `frontend`: React + Vite frontend UI workspace.
- `migrations`: Alembic database schema migrations.
- `tests`: Unit and API integration test suites.
- `docs`: Architecture specifications and evaluation documentation.

---

See [AGENTS.md](AGENTS.md) for development rules and project constraints.
