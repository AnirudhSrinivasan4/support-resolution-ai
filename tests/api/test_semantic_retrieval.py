"""HTTP validation and response contract for semantic retrieval."""

from fastapi.testclient import TestClient

from app.api.routes import retrieval
from app.domain.models import SemanticTicketResult
from app.main import app
from app.services.semantic_retrieval import SemanticRetrievalResponse

client = TestClient(app)


class FakeService:
    def retrieve(self, query: str, *, top_k: int) -> SemanticRetrievalResponse:
        return SemanticRetrievalResponse(
            query=query.strip(),
            model_identifier="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            results=(
                SemanticTicketResult(
                    ticket_id=42,
                    subject="Password reset",
                    body="Reset email is delayed",
                    answer="Check the spam folder.",
                    queue="Account",
                    ticket_type="Incident",
                    priority="normal",
                    language="en",
                    tags=("login", "email"),
                    similarity=0.91,
                    source_dataset="public/support-sample",
                    source_split="train",
                    source_record_id="42",
                    source_revision="abc123",
                ),
            )[:top_k],
        )


def test_semantic_retrieval_endpoint_returns_typed_result(monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "_get_service", lambda: FakeService())

    response = client.post(
        "/v1/retrieval/semantic",
        json={"query": "  password reset email  ", "top_k": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "password reset email"
    assert payload["results"][0]["answer"] == "Check the spam folder."
    assert payload["results"][0]["similarity"] == 0.91
    assert payload["results"][0]["source"]["record_id"] == "42"
    assert "embedding" not in payload["results"][0]


def test_semantic_retrieval_endpoint_validates_query_and_top_k() -> None:
    assert client.post("/v1/retrieval/semantic", json={"query": "   "}).status_code == 422
    assert client.post(
        "/v1/retrieval/semantic", json={"query": "help", "top_k": 21}
    ).status_code == 422
