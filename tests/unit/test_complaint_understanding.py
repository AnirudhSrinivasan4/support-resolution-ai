"""Controlled complaint taxonomy and deterministic severity behavior."""

from collections.abc import Mapping
from typing import Any

import pytest

from app.core.config import settings
from app.domain.models import ComplaintAnalysis
from app.services.complaint_understanding import (
    COMPLAINT_FEW_SHOTS,
    ComplaintUnderstandingError,
    ComplaintUnderstandingService,
)


class FakeLLM:
    def __init__(self, response: Mapping[str, Any] | None = None, error: Exception | None = None):
        self.response = response or {
            "intent": "esim_activation",
            "category": "esim",
            "product": "esim",
            "severity": "medium",
            "sentiment": "frustrated",
        }
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def generate_structured(self, *, system_prompt, user_prompt, schema):
        self.calls.append({"system": system_prompt, "user": user_prompt, "schema": schema})
        if self.error:
            raise self.error
        return self.response


def _service(llm: FakeLLM) -> ComplaintUnderstandingService:
    return ComplaintUnderstandingService(llm, settings.complaint_taxonomy)


def test_valid_structured_output_is_normalized_and_taxonomy_is_sent_to_llm() -> None:
    llm = FakeLLM({
        "intent": " Esim_Activation ", "category": " ESIM ", "product": "eSIM",
        "severity": "MEDIUM", "sentiment": "Frustrated",
    })
    result = _service(llm).understand("E4037 activation failed")
    assert result == ComplaintAnalysis(
        intent="esim_activation", category="esim", product="esim",
        severity="medium", sentiment="frustrated",
    )
    assert "unknown" in llm.calls[0]["schema"]["properties"]["category"]["enum"]
    assert "confidence" not in llm.calls[0]["schema"]["properties"]
    assert llm.calls[0]["schema"]["required"] == [
        "intent", "category", "product", "severity", "sentiment"
    ]
    assert set(llm.calls[0]["schema"]["properties"]) == {
        "intent", "category", "product", "severity", "sentiment"
    }


def test_prompt_defines_taxonomy_boundaries_and_uses_configured_values_in_few_shots() -> None:
    llm = FakeLLM()
    _service(llm).understand("E4037 activation failed")
    prompt = llm.calls[0]["system"]

    for instruction in (
        "Do not use this just because someone asks whether a handset supports eSIM",
        "payment, recharge, or top-up attempt did not complete",
        "charged more than once",
        "Prefer this over connectivity_issue when the border/roaming context is stated",
        "Security indicators take precedence over generic account_access",
        "Too little information to identify a telecom issue",
        "critical: Immediate security/safety",
        "angry: Strong anger",
        "Do not infer anger just because a problem is serious",
        "CONFIGURED ALLOWED VALUES (copy exactly)",
        "Do not add fields, explanations, markdown, or confidence",
    ):
        assert instruction in prompt

    for complaint, expected_output in COMPLAINT_FEW_SHOTS:
        assert complaint in prompt
        assert str(expected_output["intent"]) in prompt
    assert '"I did not authorize moving my number onto a replacement SIM."' in prompt
    assert '"The kitchen blender stopped spinning."' in prompt


def test_few_shots_outside_configured_taxonomy_are_not_presented_as_allowed_labels() -> None:
    from app.domain.models import ComplaintTaxonomy

    taxonomy = ComplaintTaxonomy(
        intents=("esim_activation", "unknown"),
        categories=("esim", "unknown"),
        products=("esim", "unknown"),
    )
    llm = FakeLLM()
    service = ComplaintUnderstandingService(llm, taxonomy)
    service.understand("eSIM activation failed")
    prompt = llm.calls[0]["system"]
    assert "An E4037 error appears while installing a fresh digital SIM profile." in prompt
    assert "Is my handset capable of using a digital SIM card?" not in prompt


def test_few_shot_complaints_do_not_duplicate_labeled_evaluation_inputs() -> None:
    import json
    from pathlib import Path

    dataset_path = Path(__file__).resolve().parents[2] / "evaluation" / "datasets" / "complaint_understanding.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    labeled_complaints = {example["complaint"] for example in dataset["examples"]}
    few_shot_texts = {complaint for complaint, _ in COMPLAINT_FEW_SHOTS}
    assert not labeled_complaints & few_shot_texts


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "arbitrary_class"),
        ("product", "telecom_bundle"),
        ("severity", "urgent"),
        ("sentiment", "furious_customer"),
    ],
)
def test_unsupported_taxonomy_values_are_rejected(field: str, value: str) -> None:
    output = {
        "intent": "esim_activation",
        "category": "esim",
        "product": "esim",
        "severity": "medium",
        "sentiment": "negative",
    }
    output[field] = value
    with pytest.raises(ComplaintUnderstandingError, match=f"unsupported {field}"):
        _service(FakeLLM(output)).understand("The issue is not clear")


def test_unknown_classification_is_valid_when_evidence_is_insufficient() -> None:
    result = _service(FakeLLM({
        "intent": "unknown", "category": "unknown", "product": "unknown",
        "severity": "unknown", "sentiment": "unknown",
    })).understand("A request that does not identify a telecom issue")
    assert result == ComplaintAnalysis("unknown", "unknown", "unknown", "unknown", "unknown")


@pytest.mark.parametrize(
    ("complaint", "intent", "expected"),
    [
        ("I think someone did a SIM swap on my number", "security_concern", "high"),
        ("Our entire network is down; no service anywhere", "connectivity_issue", "high"),
        ("What roaming plans are available?", "general_inquiry", "low"),
    ],
)
def test_deterministic_severity_rules_override_model_estimate(
    complaint: str, intent: str, expected: str
) -> None:
    output = {
        "intent": intent,
        "category": "unknown" if intent == "general_inquiry" else "network",
        "product": "unknown",
        "severity": "low",
        "sentiment": "neutral",
    }
    result = _service(FakeLLM(output)).understand(complaint)
    assert result.severity == expected


def test_malformed_output_and_provider_failure_are_safely_rejected() -> None:
    with pytest.raises(ComplaintUnderstandingError, match="invalid category"):
        _service(FakeLLM({"intent": "unknown"})).understand("Can you help?")
    with pytest.raises(ComplaintUnderstandingError, match="provider failed"):
        _service(FakeLLM(error=TimeoutError("provider timed out"))).understand("Can you help?")
