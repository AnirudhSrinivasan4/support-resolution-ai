"""Adapter for Hugging Face datasets saved with ``save_to_disk``."""

from pathlib import Path

from datasets import DatasetDict, load_from_disk

from app.ingestion.service import DatasetSnapshot


class HuggingFaceSavedDatasetLoader:
    """Load and expose only the train split of a saved DatasetDict."""

    def load_train(self, dataset_path: str | Path) -> DatasetSnapshot:
        saved = load_from_disk(str(dataset_path))
        if not isinstance(saved, DatasetDict):
            raise ValueError(
                "Expected a saved DatasetDict with a 'train' split; "
                "got a saved Dataset instead."
            )
        if "train" not in saved:
            raise ValueError("Saved DatasetDict does not contain a 'train' split.")

        train = saved["train"]
        fingerprint = getattr(train, "_fingerprint", None)
        return DatasetSnapshot(
            columns=train.column_names,
            rows=iter(train),
            revision=str(fingerprint) if fingerprint else None,
        )
