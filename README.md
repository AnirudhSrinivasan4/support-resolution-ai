# Intelligent Support Ticket Resolution Assistant

A production-minded prototype for helping support agents understand a complaint, find relevant support evidence, and review a grounded resolution draft. The system is intended to abstain or escalate when its evidence is insufficient.

## Current state

The current milestones add saved Hugging Face dataset ingestion, separate telecom knowledge ingestion, model-specific embeddings, semantic and hybrid retrieval, and grounded RAG resolution generation backed by PostgreSQL/pgvector. The LLM provider is configurable and disabled unless explicitly enabled.

The historical corpus is a filtered subset of a heterogeneous public customer-support dataset (approximately 61k tickets before filtering). It is **not telecom-specific**. Telecom-specific guidance will live in a separate knowledge base. Historical answers are imperfect historical support evidence, not verified resolutions or ground truth.

## Local development

1. Copy `.env.example` to `.env` and add credentials only to the local `.env` file when a provider is selected.
2. Start PostgreSQL with `docker compose up -d db`.
3. For local Python development, install the project with `pip install -e ".[dev]"`.
4. Set `DATABASE_URL` for a process running on the host, then apply migrations with `alembic upgrade head`.
5. Run the API with `uvicorn app.main:app --reload`, then open `http://localhost:8000/docs` or check `http://localhost:8000/healthz`.

Example PowerShell setup for the local Compose database:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://support:local-development-only@localhost:5432/support"
alembic upgrade head
```

## Historical ticket ingestion

The loader expects a Hugging Face `DatasetDict` saved with `datasets.save_to_disk()`. It loads the `train` split with `datasets.load_from_disk()`. It does not download the dataset or convert it to CSV.

After PostgreSQL is running and the migration has been applied, run the full import explicitly:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://support:local-development-only@localhost:5432/support"
python -m app.ingestion.cli "D:\College\customer-support-tickets"
```

That command reads the existing local dataset in place. Do not copy it under this repository. The `.gitignore` excludes local data and common dataset file formats; the real dataset is not included in the test fixture or repository.

For a bounded smoke run, pass `--limit 10`. The tests use ten synthetic records from `tests/fixtures/synthetic_historical_tickets.json`; they materialize a temporary saved `DatasetDict` and use in-memory SQLite. The fixture is not derived from the public dataset.

## Historical ticket embeddings

The embedding CLI creates vectors from each historical ticket's subject and body. It labels those fields in the input as `Subject:` and `Body:`, omits missing/blank fields, and skips a ticket when both are blank. The historical `answer` is deliberately excluded. Stored source text remains unchanged in `historical_tickets`.

The configurable default is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. The ingested corpus contains both German and English tickets, so this multilingual Sentence Transformers model is a better fit than an English-only model; its model card lists support for 50 languages. Its vector dimension is read from the loaded model rather than assumed. Change `EMBEDDING_MODEL` to select another compatible model. Set `EMBEDDING_MODEL_REVISION` to a pinned model commit for reproducibility and to keep different model revisions in separate embedding records. No paid embedding API is used.

Install the optional local model dependency and run the migration/CLI:

```powershell
pip install -e ".[embeddings,dev]"
$env:DATABASE_URL = "postgresql+psycopg://support:local-development-only@localhost:5432/support"
alembic upgrade head
python -m app.embeddings.cli --batch-size 64
```

PostgreSQL must have the pgvector extension available; this project's Compose database image includes it. The migration enables the extension and adds `historical_ticket_embeddings`, keyed uniquely by ticket and model identifier. Each row also stores model dimension, source-text SHA-256, and timestamps. The pipeline reads tickets by primary-key pages and commits each batch separately. It reuses an embedding only when the model identifier, dimension, and exact subject/body hash match; changed text is regenerated, and an existing vector is removed if the source becomes empty. HNSW cosine indexes are created for the actual loaded model dimension and identifier so the migration does not guess vector width.

The command prints JSON counters (`processed`, `embedded`, `reused`, `skipped_no_text`, `errors`), model identifier, dimension, and runtime. It logs periodic batch progress without ticket contents. Embeddings for different configured model identifiers can coexist, allowing later model changes without overwriting prior vectors. The historical dataset is still a heterogeneous public support corpus, not telecom data, and historical answers remain imperfect evidence.

## Semantic retrieval

POST /v1/retrieval/semantic embeds a complaint with the same configured multilingual Sentence Transformers model used for stored vectors, then asks PostgreSQL/pgvector for the nearest historical tickets. The query and index must share the same model and 384-dimensional vector space; retrieval filters by exact model identifier and dimension so vectors from other models are never mixed. PostgreSQL performs nearest-neighbor search with cosine distance and the matching HNSW cosine index; vectors are not loaded into application memory.

top_k is request-configurable from 1 through 20 (default 5). The returned similarity is 1 - cosine_distance, so larger values mean closer vector directions for this query. It is a ranking signal, not a calibrated confidence, correctness, or resolution-quality score. Historical answers are returned as historical support evidence only.

Example request:

    {"query": "My mobile internet stopped working after switching to 5G", "top_k": 5}

Each result includes the ticket subject/body/answer, queue/type/priority/language, tags, the similarity score, and source dataset/split/record/revision metadata. Raw vectors are never returned. The model loads once on the first retrieval request. The API needs DATABASE_URL and the optional embeddings dependency installed.

## Hybrid retrieval

POST /v1/retrieval/hybrid combines semantic candidates with PostgreSQL full-text candidates over subject and body; historical answers are excluded from lexical matching. PostgreSQL full-text search and a GIN index keep lexical retrieval in the existing database without another search service. The generated search vector uses the simple text configuration to avoid assuming the corpus is English-only and safely coalesces missing subject/body fields. The query builder removes common English/German function words and ORs the remaining terms so paraphrased complaints can still produce lexical candidates; ts_rank_cd rewards matches with more term coverage.

The API fuses the two ordered candidate lists with Reciprocal Rank Fusion (RRF): each result receives 1 / (RRF constant + one-based rank) from each list where it appears. It combines ranks rather than averaging semantic and lexical scores whose scales differ. A ticket in both lists receives both contributions; candidates in only one list remain eligible. fused_score is a ranking value, not confidence. Responses retain modality ranks and scores for inspection.

Defaults are 20 semantic candidates, 20 lexical candidates, final top_k 5 (maximum 20), and RRF constant 60. Configure candidate sizes and RRF_CONSTANT through environment variables. Increasing candidate limits can improve recall at additional query cost.

## Telecom knowledge base

The telecom KB is an independent, versioned source of synthetic curated domain guidance. The committed seed at `knowledge_base/seeds/v1/documents.json` contains 45 demonstration procedures labeled `synthetic-curated`; they are not proprietary carrier procedures. It is stored in `knowledge_documents` with its own `knowledge_document_embeddings` table. This keeps authoritative domain guidance distinct from heterogeneous historical customer-support cases and their imperfect agent answers.

Apply the current migrations, install the optional embedding dependency, and ingest the small committed seed:

```powershell
pip install -e "[embeddings,dev]"
$env:DATABASE_URL = "postgresql+psycopg://support:local-development-only@localhost:5432/support"
alembic upgrade head
python -m app.knowledge.cli
```

The seed may also be supplied as a positional JSON path; `--batch-size` controls embedding batches. Ingestion is idempotent and re-embeds a document only when its content or metadata hash changes. It does not read or update historical ticket embeddings.

POST `/v1/knowledge/search` accepts `{"query":"E4037 eSIM activation failed","top_k":5}`. It returns document content and provenance/version plus semantic and lexical ranks/scores and their RRF score; vectors are never exposed. Exact technical identifiers such as `E4037` benefit from PostgreSQL lexical matching, while semantic embeddings can find eSIM guidance for paraphrases such as “my digital SIM won't activate” that omit the code. Both use PostgreSQL/pgvector already operated by the service, avoiding an additional search database and keeping the demo's stores and operations simple.

The resolution service combines the authoritative telecom KB and historical ticket corpus as distinct source types, preserves their provenance, validates citations against retrieved evidence, and abstains/escalates when relevant KB evidence is insufficient.

## Grounded resolution generation

POST `/v1/resolutions` accepts a complaint and returns a resolution, ordered steps, escalation advice, validated citations, and an `abstained` flag. RAG means retrieval-augmented generation here: retrieval runs first, then only a bounded set of retrieved evidence is given to the LLM. The service uses existing hybrid RRF order for both corpora. It places telecom KB procedures under `AUTHORITATIVE KNOWLEDGE BASE EVIDENCE` and historical cases under `HISTORICAL SUPPORT CASE EVIDENCE`; historical agent answers are explicitly unverified context and cannot override KB procedures.

The prompt restricts factual/procedural claims to supplied evidence and requires stable source IDs for citations. The application checks those IDs against its actual retrieval set, derives citation type/title from that set, and rejects unknown IDs. This validation is necessary because an LLM can emit plausible but nonexistent citations. Before generation, the service deterministically abstains unless a KB hit clears the configured semantic similarity or lexical-score threshold. This prevents historical cases or a nearest-neighbor result with weak relevance from becoming unsupported instructions. No numeric confidence is requested or returned.

The LLM adapter is a small OpenAI Chat Completions-compatible HTTP client behind `LLMProvider`; it does not tie the service to an SDK or vendor. To enable it, set `LLM_PROVIDER=openai-compatible`, `LLM_MODEL` to a model name supported by the endpoint, optionally set `LLM_BASE_URL`, and provide `LLM_API_KEY` through the local environment or secret manager. For a local OpenAI-compatible service the key may be omitted. `LLM_PROVIDER=disabled` is the default; the resolution endpoint returns 503 until configured. Evidence limits default to 5 KB documents and 4 historical tickets (maximum 5 each). KB relevance floors default to semantic similarity 0.40 or lexical score 0.50 and should be tuned with recorded evaluation results.

## Structured complaint understanding

POST `/v1/complaints/understand` returns controlled `intent`, `category`, `product`, `severity`, and `sentiment` labels. Configure the evolving intent/category/product lists with `COMPLAINT_INTENTS`, `COMPLAINT_CATEGORIES`, and `COMPLAINT_PRODUCTS` (comma-separated normalized labels); each list must include `unknown`. The parser validates the provider's structured response and falls back to `unknown` only when the model reports it, rather than accepting an invented class. Deterministic severity overrides mark explicit SIM-swap/security compromise and complete outage reports high, and general inquiries low. These simple rules do not replace policy-based triage, and sentiment is informational only. `POST /v1/resolutions` runs the same parser before retrieval and includes the structured fields in its response. Classification quality remains unevaluated until a reviewed, versioned label set is scored.

## Evaluation baseline

Three small manually curated datasets cover complaint understanding, telecom KB retrieval, and abstention. After configuring the same database, embedding model, and LLM provider as the API, run:

```powershell
python -m app.evaluation.cli
```

The command uses existing application services and writes JSON and Markdown baseline reports under `evaluation/reports/` after successful completion. Select one suite with `--suite complaint_understanding`, `--suite retrieval`, or `--suite abstention`. Metrics and label limitations are documented in [the evaluation guide](evaluation/README.md). These small datasets are not production-quality benchmark evidence; no answer correctness or hallucination metric is reported.

## Project map

- `app/domain`: shared domain types and provider/storage protocols.
- `app/ingestion`: row validation, normalization, and ingestion orchestration.
- `app/services`: semantic and hybrid retrieval orchestration.
- `app/infrastructure/datasets`: Hugging Face saved-dataset adapter.
- `app/infrastructure/persistence`: SQLAlchemy models, database setup, and repository.
- `app/api`: HTTP routes and request/response boundary.
- `app/core`: runtime settings and cross-cutting application concerns.
- `tests`: unit and API test suites.
- `docs`: architecture and evaluation plans.
- `migrations`: Alembic schema revisions.

See [architecture](docs/architecture.md), [evaluation](docs/evaluation.md), and [development rules](AGENTS.md).
