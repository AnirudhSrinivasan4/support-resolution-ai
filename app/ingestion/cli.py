"""Command-line entry point for importing a saved Hugging Face dataset."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from app.domain.models import IngestionBatchResult
from app.ingestion.normalize import DATASET_ID
from app.ingestion.service import ingest_train_snapshot
from app.infrastructure.datasets.huggingface_saved_dataset import (
    HuggingFaceSavedDatasetLoader,
)
from app.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.historical_ticket_repository import (
    SQLAlchemyHistoricalTicketRepository,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest the train split of a Hugging Face dataset saved to disk."
    )
    parser.add_argument(
        "dataset_path",
        type=Path,
        help="Path passed to datasets.load_from_disk().",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="SQLAlchemy URL; defaults to the DATABASE_URL environment variable.",
    )
    parser.add_argument(
        "--source-dataset",
        default=DATASET_ID,
        help="Stable dataset provenance label (override for synthetic fixtures).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional maximum number of train rows to ingest.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Rows per database transaction (default: 500).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.database_url:
        parser.error("provide --database-url or set DATABASE_URL")

    snapshot = HuggingFaceSavedDatasetLoader().load_train(args.dataset_path)
    engine = create_database_engine(args.database_url)
    try:
        repository = SQLAlchemyHistoricalTicketRepository(
            create_session_factory(engine), engine
        )
        result: IngestionBatchResult = ingest_train_snapshot(
            snapshot,
            repository,
            source_dataset=args.source_dataset,
            source_split="train",
            limit=args.limit,
            batch_size=args.batch_size,
        )
        print(
            json.dumps(
                {
                    "source_dataset": args.source_dataset,
                    "source_split": "train",
                    **asdict(result),
                },
                sort_keys=True,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
