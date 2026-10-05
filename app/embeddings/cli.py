"""Run the local embedding pipeline over persisted historical tickets."""

import argparse
import json
import logging
import os
import time
from dataclasses import asdict

from app.core.config import settings
from app.embeddings.service import embed_historical_tickets
from app.infrastructure.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.ticket_embedding_repository import (
    SQLAlchemyTicketEmbeddingRepository,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create model-versioned semantic vectors for historical tickets."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="SQLAlchemy URL; defaults to DATABASE_URL.",
    )
    parser.add_argument("--model", default=settings.embedding_model)
    parser.add_argument("--revision", default=settings.embedding_model_revision)
    parser.add_argument(
        "--batch-size", type=int, default=settings.embedding_batch_size
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.database_url:
        parser.error("provide --database-url or set DATABASE_URL")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    started_at = time.perf_counter()
    provider = SentenceTransformerEmbeddingProvider(
        args.model, revision=args.revision, batch_size=args.batch_size
    )
    engine = create_database_engine(args.database_url)
    try:
        repository = SQLAlchemyTicketEmbeddingRepository(
            create_session_factory(engine), engine
        )
        result = embed_historical_tickets(
            repository, provider, batch_size=args.batch_size
        )
    finally:
        engine.dispose()

    print(
        json.dumps(
            {
                **asdict(result),
                "model": provider.model_identifier,
                "dimension": provider.dimension,
                "runtime_seconds": round(time.perf_counter() - started_at, 3),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
