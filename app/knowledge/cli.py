"""Command-line ingestion for the committed curated telecom knowledge seed."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from app.core.config import settings
from app.infrastructure.embeddings.runtime import get_embedding_provider
from app.infrastructure.persistence.database import create_database_engine, create_session_factory
from app.infrastructure.persistence.knowledge_document_repository import (
    SQLAlchemyKnowledgeDocumentRepository,
)
from app.infrastructure.persistence.knowledge_embedding_repository import (
    SQLAlchemyKnowledgeEmbeddingRepository,
)
from app.knowledge.ingestion import ingest_knowledge_seed

DEFAULT_SEED = Path(__file__).resolve().parents[2] / "knowledge_base" / "seeds" / "v1" / "documents.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the curated telecom KB seed")
    parser.add_argument("seed", nargs="?", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--batch-size", type=int, default=settings.embedding_batch_size)
    args = parser.parse_args()
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("--database-url or DATABASE_URL is required")
    engine = create_database_engine(database_url)
    sessions = create_session_factory(engine)
    result = ingest_knowledge_seed(
        args.seed,
        SQLAlchemyKnowledgeDocumentRepository(sessions, engine.dialect.name),
        SQLAlchemyKnowledgeEmbeddingRepository(sessions, engine),
        get_embedding_provider(),
        batch_size=args.batch_size,
    )
    print(json.dumps({"seed": str(args.seed), **asdict(result)}, default=str))
    engine.dispose()


if __name__ == "__main__":
    main()
