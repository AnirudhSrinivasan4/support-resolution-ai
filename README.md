# Intelligent Support Ticket Resolution Assistant

A production-minded prototype for helping support agents understand a complaint, find relevant support evidence, and review a grounded resolution draft. The system is intended to abstain or escalate when its evidence is insufficient.

## Current state

The current milestone adds saved Hugging Face dataset ingestion, SQLAlchemy persistence, and an Alembic migration. Complaint analysis, embeddings, retrieval, reranking, LLM calls, and resolution generation are still out of scope.

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

## Project map

- `app/domain`: shared domain types and provider/storage protocols.
- `app/ingestion`: row validation, normalization, and ingestion orchestration.
- `app/services`: future use-case orchestration outside ingestion.
- `app/infrastructure/datasets`: Hugging Face saved-dataset adapter.
- `app/infrastructure/persistence`: SQLAlchemy models, database setup, and repository.
- `app/api`: HTTP routes and request/response boundary.
- `app/core`: runtime settings and cross-cutting application concerns.
- `tests`: unit and API test suites.
- `docs`: architecture and evaluation plans.
- `migrations`: Alembic schema revisions.

See [architecture](docs/architecture.md), [evaluation](docs/evaluation.md), and [development rules](AGENTS.md).
