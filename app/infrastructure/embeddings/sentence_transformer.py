"""Configurable local Sentence Transformers adapter."""

from collections.abc import Sequence
from typing import Any


class SentenceTransformerEmbeddingProvider:
    """Encode batches with a configurable Sentence Transformers model."""

    def __init__(
        self,
        model_name: str,
        *,
        revision: str | None = None,
        batch_size: int = 64,
        model_factory: Any | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if model_factory is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    "Install the local model dependency with "
                    '`pip install -e ".[embeddings]"'
                ) from error
            model_factory = SentenceTransformer

        model_options = {"revision": revision} if revision else {}
        self._model = model_factory(model_name, **model_options)
        dimension_reader = getattr(self._model, "get_embedding_dimension", None)
        if dimension_reader is None:
            dimension_reader = self._model.get_sentence_embedding_dimension
        dimension = dimension_reader()
        if not isinstance(dimension, int) or dimension < 1:
            raise ValueError("loaded model did not report a positive embedding dimension")
        self._dimension = dimension
        self._batch_size = batch_size
        self._model_identifier = f"{model_name}@{revision}" if revision else model_name

    @property
    def model_identifier(self) -> str:
        return self._model_identifier

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        if not texts:
            return ()
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist() if hasattr(vectors, "tolist") else vectors
