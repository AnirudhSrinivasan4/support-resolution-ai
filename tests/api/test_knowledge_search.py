"""Validation and response shape for the KB endpoint."""

from fastapi.testclient import TestClient

from app.api.routes import knowledge
from app.domain.models import (
    KnowledgeSearchHit,
    TelecomKnowledgeDocument,
)
from app.main import app
from app.services.knowledge_retrieval import KnowledgeSearchResponse

client = TestClient(app)


class FakeKnowledgeService:
    def search(self, query: str, *, top_k: int) -> KnowledgeSearchResponse:
        document = TelecomKnowledgeDocument(
            document_id="telecom-v1.esim.error-e4037",
            title="E4037 eSIM activation error",
            content="Verify the profile and retry once.",
            category="eSIM activation",
            product="eSIM",
            severity="medium",
            escalation_conditions="Escalate if it persists.",
            source="synthetic-curated",
            version="telecom-kb-v1",
        )
        return KnowledgeSearchResponse(
            query=query.strip(), model_identifier="test/model", rrf_constant=60,
            semantic_candidate_limit=20, lexical_candidate_limit=20,
            results=(KnowledgeSearchHit(document, 0.03, 1, 0.8, 1, 0.5),)[:top_k],
        )


def test_knowledge_endpoint_returns_sources_without_vectors(monkeypatch) -> None:
    monkeypatch.setattr(knowledge, "_get_service", lambda: FakeKnowledgeService())
    response = client.post(
        "/v1/knowledge/search", json={"query": " E4037 eSIM activation failed ", "top_k": 5}
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["document_id"] == "telecom-v1.esim.error-e4037"
    assert result["source"] == "synthetic-curated"
    assert result["semantic_rank"] == result["lexical_rank"] == 1
    assert "embedding" not in result


def test_knowledge_endpoint_validates_query_and_top_k() -> None:
    assert client.post("/v1/knowledge/search", json={"query": "  "}).status_code == 422
    assert client.post(
        "/v1/knowledge/search", json={"query": "help", "top_k": 21}
    ).status_code == 422
