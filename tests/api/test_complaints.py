"""HTTP request/response validation for complaint understanding."""

from fastapi.testclient import TestClient

from app.api.routes import complaints
from app.domain.models import ComplaintAnalysis
from app.main import app
from app.core.config import settings
from app.services.complaint_understanding import ComplaintUnderstandingService

client = TestClient(app)


class FakeUnderstandingService:
    def understand(self, complaint: str) -> ComplaintAnalysis:
        return ComplaintAnalysis(
            intent="esim_activation", category="esim", product="esim",
            severity="high", sentiment="frustrated",
        )


def test_complaint_understanding_endpoint_returns_structured_fields(monkeypatch) -> None:
    monkeypatch.setattr(complaints, "_get_service", lambda: FakeUnderstandingService())
    response = client.post(
        "/v1/complaints/understand",
        json={"complaint": "E4037 eSIM activation failed"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "intent": "esim_activation",
        "category": "esim",
        "product": "esim",
        "severity": "high",
        "sentiment": "frustrated",
    }


def test_complaint_understanding_endpoint_validates_input(monkeypatch) -> None:
    monkeypatch.setattr(complaints, "_get_service", lambda: FakeUnderstandingService())
    assert client.post("/v1/complaints/understand", json={"complaint": "  "}).status_code == 422
    assert client.post(
        "/v1/complaints/understand", json={"complaint": "x" * 4001}
    ).status_code == 422


def test_api_examples_cover_representative_complaint_types(monkeypatch) -> None:
    examples = [
        ("E4037 eSIM activation failed", "esim_activation", "esim", "esim", "high"),
        ("My broadband drops every evening around 8; I restarted the router twice.", "connectivity_issue", "network", "broadband", "medium"),
        ("Payment failed but the money was deducted", "payment_failed", "payments", "payments", "medium"),
        ("I keep getting charged for roaming", "roaming_issue", "roaming", "roaming", "medium"),
    ]

    class ScriptedProvider:
        current = None

        def generate_structured(self, *, system_prompt, user_prompt, schema):
            complaint, intent, category, product, severity = self.current
            assert complaint in user_prompt
            return {
                "intent": intent, "category": category, "product": product,
                "severity": severity, "sentiment": "frustrated",
            }

    provider = ScriptedProvider()
    service = ComplaintUnderstandingService(provider, settings.complaint_taxonomy)

    class PerRequestService:
        def understand(self, complaint: str) -> ComplaintAnalysis:
            example = next(item for item in examples if item[0] == complaint)
            provider.current = (*example[:1], *example[1:],)
            return service.understand(complaint)

    monkeypatch.setattr(complaints, "_get_service", lambda: PerRequestService())
    for complaint, intent, category, product, severity in examples:
        response = client.post("/v1/complaints/understand", json={"complaint": complaint})
        assert response.status_code == 200, response.text
        assert response.json()["intent"] == intent
        assert response.json()["category"] == category
        assert response.json()["product"] == product
        assert response.json()["severity"] == severity
