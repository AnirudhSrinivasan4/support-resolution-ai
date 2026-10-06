"""Knowledge ingestion and retrieval tests using deterministic local adapters."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Sequence

import pytest
from sqlalchemy import select

from app.domain.models import TelecomKnowledgeDocument
from app.domain.models import KnowledgeLexicalHit, KnowledgeSemanticHit
from app.infrastructure.datasets.knowledge_seed_json import load_knowledge_seed
from app.infrastructure.persistence.database import create_database_engine, create_session_factory
from app.infrastructure.persistence.knowledge_document_repository import (
    SQLAlchemyKnowledgeDocumentRepository,
)
from app.infrastructure.persistence.knowledge_embedding_repository import (
    SQLAlchemyKnowledgeEmbeddingRepository,
)
from app.infrastructure.persistence.models import (
    Base,
    KnowledgeDocumentEmbeddingRecord,
    KnowledgeDocumentRecord,
)
from app.knowledge.ingestion import ingest_knowledge_documents, ingest_knowledge_seed
from app.services.knowledge_retrieval import KnowledgeRetrievalService

SEED = Path(__file__).parents[2] / "knowledge_base" / "seeds" / "v1" / "documents.json"


class FakeProvider:
    model_identifier = "test/knowledge"
    dimension = 384

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        self.calls.append(list(texts))
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        vector = [0.0] * 384
        normalized = text.lower()
        vector[0] = float("esim" in normalized or "e-sim" in normalized or "digital sim" in normalized)
        vector[1] = float("activation" in normalized or "activate" in normalized)
        vector[2] = float("payment" in normalized or "deducted" in normalized)
        vector[3] = float("roaming" in normalized)
        vector[4] = 1.0
        return vector


def _setup():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = create_session_factory(engine)
    docs = SQLAlchemyKnowledgeDocumentRepository(sessions, engine.dialect.name)
    vectors = SQLAlchemyKnowledgeEmbeddingRepository(sessions, engine)
    return engine, sessions, docs, vectors


def test_seed_is_curated_versioned_and_contains_e4037() -> None:
    docs = load_knowledge_seed(SEED)
    assert 30 <= len(docs) <= 50
    e4037 = next(document for document in docs if "E4037" in document.content)
    assert e4037.source == "synthetic-curated"
    assert "E4037" in e4037.title + " " + e4037.content


def test_ingestion_is_idempotent_and_updates_hash_and_vector() -> None:
    engine, sessions, docs_repo, vector_repo = _setup()
    provider = FakeProvider()
    document = load_knowledge_seed(SEED)[0]
    try:
        first = ingest_knowledge_documents([document], docs_repo, vector_repo, provider)
        second = ingest_knowledge_documents([document], docs_repo, vector_repo, provider)
        changed = replace(document, content=document.content + " Updated procedure.")
        third = ingest_knowledge_documents([changed], docs_repo, vector_repo, provider)
        assert (first.inserted, first.embedded, first.reused) == (1, 1, 0)
        assert (second.unchanged, second.embedded, second.reused) == (1, 0, 1)
        assert (third.updated, third.embedded) == (1, 1)
        assert len(provider.calls) == 2
        with sessions() as session:
            record = session.scalar(select(KnowledgeDocumentRecord))
            embedding = session.scalar(select(KnowledgeDocumentEmbeddingRecord))
            assert record is not None and record.content == changed.content
            assert embedding is not None and embedding.content_hash == record.content_hash
    finally:
        engine.dispose()


def test_seed_ingestion_rejects_empty_or_missing_content(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"schema_version": "1.0", "documents": [{
        "document_id": "x", "title": "title", "content": "", "category": "c",
        "product": "p", "severity": "low", "escalation_conditions": "none",
        "source": "synthetic-curated", "version": "v1"
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="empty content"):
        load_knowledge_seed(path)
    missing = json.loads(path.read_text(encoding="utf-8"))
    del missing["documents"][0]["content"]
    path.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required fields: content"):
        load_knowledge_seed(path)
    with pytest.raises(ValueError, match="could not read knowledge seed"):
        load_knowledge_seed(tmp_path / "missing.json")


def test_semantic_retrieval_uses_only_current_kb_vectors() -> None:
    engine, sessions, docs_repo, vector_repo = _setup()
    provider = FakeProvider()
    try:
        ingest_knowledge_seed(SEED, docs_repo, vector_repo, provider, batch_size=10)
        seed_docs = load_knowledge_seed(SEED)

        class SemanticFake:
            def search_by_embedding(self, *, embedding, model_identifier, dimension, limit):
                matches = [
                    document for document in seed_docs
                    if embedding[0] and "esim" in (document.category + " " + document.title).lower()
                    or embedding[2] and "payment" in document.category.lower()
                ]
                return [KnowledgeSemanticHit(document, 0.9) for document in matches[:limit]]

        class LexicalFake:
            def search_by_text(self, *, query, limit):
                normalized = query.lower()
                matches = [document for document in seed_docs if any(
                    term in (document.title + " " + document.content).lower()
                    for term in normalized.split()
                )]
                return [KnowledgeLexicalHit(document, 1.0) for document in matches[:limit]]

        service = KnowledgeRetrievalService(provider, LexicalFake(), SemanticFake())
        esim = service.search("My digital SIM will not activate", top_k=5)
        assert esim.results
        assert any(
            "esim" in (hit.document.category + " " + hit.document.title).lower()
            for hit in esim.results
        )
        payment = service.search("payment failed but money deducted", top_k=5)
        assert payment.results
        assert any("payment" in hit.document.category.lower() or "billing" in hit.document.category.lower()
                   for hit in payment.results)
    finally:
        engine.dispose()


def test_lexical_exact_identifier_query_preserves_identifier() -> None:
    from app.infrastructure.persistence.lexical_ticket_search_repository import build_lexical_query

    assert "E4037" in build_lexical_query("E4037 eSIM activation failed")


def test_lexical_repository_returns_exact_identifier_match() -> None:
    from app.infrastructure.persistence.knowledge_document_repository import (
        SQLAlchemyKnowledgeDocumentRepository,
    )
    from app.infrastructure.persistence.models import KnowledgeDocumentRecord
    from sqlalchemy.dialects import postgresql

    document = TelecomKnowledgeDocument(
        "telecom-v1.esim.error-e4037", "E4037 eSIM activation", "E4037 procedure",
        "eSIM", "eSIM", "medium", "Escalate if repeated", "synthetic-curated", "v1"
    )
    record = KnowledgeDocumentRecord(
        document_id=document.document_id, title=document.title, content=document.content,
        category=document.category, product=document.product, severity=document.severity,
        escalation_conditions=document.escalation_conditions, source=document.source,
        version=document.version, content_hash="a" * 64,
    )

    class Rows:
        def all(self):
            return [(record, 0.9)]

    class Session:
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def execute(self, statement):
            self.statement = statement
            return Rows()

    session = Session()
    repository = SQLAlchemyKnowledgeDocumentRepository(lambda: session, "postgresql")
    results = repository.search_by_text(query="E4037 eSIM activation failed", limit=5)
    compiled = session.statement.compile(dialect=postgresql.dialect())
    assert results[0].document.document_id == document.document_id
    assert "websearch_to_tsquery" in str(compiled)
    assert any("E4037" in str(value) for value in compiled.params.values())


def test_seed_ingestion_reuses_vectors_on_second_run() -> None:
    engine, _sessions, docs_repo, vector_repo = _setup()
    provider = FakeProvider()
    try:
        first = ingest_knowledge_seed(SEED, docs_repo, vector_repo, provider, batch_size=9)
        second = ingest_knowledge_seed(SEED, docs_repo, vector_repo, provider, batch_size=9)
        assert first.processed == first.inserted == first.embedded
        assert second.unchanged == second.reused == first.processed
        assert second.embedded == 0
    finally:
        engine.dispose()
