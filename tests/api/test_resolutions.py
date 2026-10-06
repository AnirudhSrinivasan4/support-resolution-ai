"""HTTP contract for the grounded resolution route; no real model calls."""

from fastapi.testclient import TestClient

from app.api.routes import resolutions
from app.domain.models import ComplaintAnalysis, ResolutionCitation, ResolutionStep
from app.main import app
from app.services.resolution import ResolutionResult

client = TestClient(app)


class FakeResolutionService:
    def resolve(self, complaint: str) -> ResolutionResult:
        return ResolutionResult(
            complaint_understanding=ComplaintAnalysis(
                "troubleshoot", "connectivity", "broadband", "high", "frustrated"
            ),
            resolution="Verify the line and retry activation once.",
            steps=(ResolutionStep("Check line eligibility.", ("kb-e4037",)),),
            escalation="Escalate if E4037 returns.",
            citations=(ResolutionCitation("knowledge", "kb-e4037", "E4037 activation"),),
            abstained=False,
        )


def test_resolution_endpoint_returns_structured_cited_response(monkeypatch) -> None:
    monkeypatch.setattr(resolutions, "_get_resolution_service", lambda: FakeResolutionService())
    response = client.post(
        "/v1/resolutions", json={"complaint": "E4037 eSIM activation failed"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolution"].startswith("Verify the line")
    assert payload["steps"] == ["Check line eligibility."]
    assert payload["escalation"] == "Escalate if E4037 returns."
    assert payload["complaint_understanding"] == {
        "intent": "troubleshoot", "category": "connectivity", "product": "broadband",
        "severity": "high", "sentiment": "frustrated",
    }
    assert payload["citations"] == [
        {"source_type": "knowledge", "source_id": "kb-e4037", "title": "E4037 activation"}
    ]
    assert "confidence" not in payload


def test_resolution_endpoint_validates_complaint(monkeypatch) -> None:
    monkeypatch.setattr(resolutions, "_get_resolution_service", lambda: FakeResolutionService())
    assert client.post("/v1/resolutions", json={"complaint": "  "}).status_code == 422
    assert client.post("/v1/resolutions", json={"complaint": "x" * 4001}).status_code == 422
