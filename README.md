# Intelligent Support Ticket Resolution Assistant

A production-minded prototype for helping support agents understand a complaint, find relevant support evidence, and review a grounded resolution draft. The system is intended to abstain or escalate when its evidence is insufficient.

## Current state

This repository contains project scaffolding only: a minimal FastAPI health endpoint, typed domain contracts, test layout, documentation, and local container definitions. It does not yet implement complaint analysis, embeddings, retrieval, reranking, LLM calls, or resolution generation.

The historical corpus is a filtered subset of a heterogeneous public customer-support dataset (approximately 61k tickets before filtering). It is **not telecom-specific**. Telecom-specific guidance will live in a separate knowledge base. Historical answers are imperfect historical support evidence, not verified resolutions or ground truth.

## Local development

1. Copy `.env.example` to `.env` and add credentials only to the local `.env` file when a provider is selected.
2. Start the API and PostgreSQL with `docker compose up --build`.
3. Open the API docs at `http://localhost:8000/docs` or check `http://localhost:8000/healthz`.
4. For local Python development, install the project with `pip install -e ".[dev]"` and run the API with `uvicorn app.main:app --reload`.

The database container is present for the future persistence milestone. The current API does not connect to it and there is no application database schema yet.

## Project map

- `app/domain`: shared domain types and provider/storage protocols.
- `app/services`: future use-case orchestration.
- `app/infrastructure`: future concrete provider and persistence adapters.
- `app/api`: HTTP routes and request/response boundary.
- `app/core`: runtime settings and cross-cutting application concerns.
- `tests`: unit and API test suites.
- `docs`: architecture and evaluation plans.

See [architecture](docs/architecture.md), [evaluation](docs/evaluation.md), and [development rules](AGENTS.md).
