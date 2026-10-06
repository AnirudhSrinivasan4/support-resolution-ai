"""End-to-end resolution orchestration with a fake LLM and fake retrievers."""

from typing import Any, Mapping

import pytest

from app.domain.models import (
    ComplaintAnalysis,
    HybridTicketResult,
    KnowledgeSearchHit,
    SemanticTicketResult,
    TelecomKnowledgeDocument,
)
from app.services.hybrid_retrieval import HybridRetrievalResponse
from app.core.config import settings
from app.services.complaint_understanding import ComplaintUnderstandingService
from app.services.knowledge_retrieval import KnowledgeSearchResponse
from app.services.resolution import (
    INSUFFICIENT_RESOLUTION,
    ResolutionGenerationError,
    ResolutionService,
)


def _knowledge_hit(*, similarity: float = 0.82, lexical_score: float | None = 0.5):
    doc = TelecomKnowledgeDocument(
        document_id="telecom-v1.esim.error-e4037",
        title="E4037 error during eSIM activation",
        content="Record E4037, confirm eligibility, and retry activation only once.",
        category="eSIM activation",
        product="eSIM",
        severity="medium",
        escalation_conditions="Escalate if E4037 returns after one retry.",
        source="synthetic-curated",
        version="telecom-kb-2026-10-06-v1",
    )
    return KnowledgeSearchHit(
        document=doc,
        fused_score=0.03,
        semantic_rank=1,
        semantic_score=similarity,
        lexical_rank=1 if lexical_score is not None else None,
        lexical_score=lexical_score,
    )


def _historical_hit():
    ticket = SemanticTicketResult(
        ticket_id=17,
        subject="Activation code issue",
        body="Customer could not activate a new profile.",
        answer="Agent response: check line eligibility.",
        queue="Mobile",
        ticket_type="Incident",
        priority="normal",
        language="en",
        tags=("activation",),
        similarity=0.74,
        source_dataset="public/customer-support-tickets",
        source_split="train",
        source_record_id="31",
        source_revision="revision-1",
    )
    return HybridTicketResult(ticket, 0.02, 1, 0.74, 2, 0.03)


class FakeKnowledgeRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.requested_limits: list[int] = []

    def search(self, query: str, *, top_k: int = 5):
        self.requested_limits.append(top_k)
        return KnowledgeSearchResponse(query, "test/embedder", 60, 20, 20, tuple(self.hits))


class FakeHistoricalRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.requested_limits: list[int] = []

    def retrieve(self, query: str, *, top_k: int = 5):
        self.requested_limits.append(top_k)
        return HybridRetrievalResponse(query, "test/embedder", tuple(self.hits))


class FakeLLM:
    def __init__(self, response: Mapping[str, Any] | None = None, error: Exception | None = None):
        self.response = response or {
            "resolution": "The profile may be provisioned incorrectly.",
            "steps": [
                {
                    "instruction": "Confirm line eligibility and retry activation once.",
                    "citations": ["telecom-v1.esim.error-e4037"],
                },
                {
                    "instruction": "Review the similar prior case as context only.",
                    "citations": ["historical-ticket:17"],
                },
            ],
            "escalation": "Escalate if E4037 returns after the retry.",
            "citations": ["telecom-v1.esim.error-e4037", "historical-ticket:17"],
            "abstained": False,
        }
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def generate_structured(self, *, system_prompt, user_prompt, schema):
        self.calls.append({"system": system_prompt, "user": user_prompt, "schema": schema})
        if self.error:
            raise self.error
        return self.response


class FakeAnalyzer:
    def __init__(self):
        self.calls: list[str] = []

    def understand(self, complaint: str) -> ComplaintAnalysis:
        self.calls.append(complaint)
        return ComplaintAnalysis("troubleshoot", "connectivity", "broadband", "medium", "frustrated")


def _service(llm: FakeLLM, *, knowledge_hits=None, historical_hits=None, analyzer=None):
    knowledge = FakeKnowledgeRetriever(
        [_knowledge_hit()] if knowledge_hits is None else knowledge_hits
    )
    historical = FakeHistoricalRetriever(
        [_historical_hit()] if historical_hits is None else historical_hits
    )
    return (
        ResolutionService(
            knowledge_retriever=knowledge,
            historical_retriever=historical,
            complaint_analyzer=analyzer or FakeAnalyzer(),
            llm_provider=llm,
            knowledge_limit=2,
            historical_limit=3,
        ),
        knowledge,
        historical,
    )


def test_resolution_pipeline_constructs_prioritized_evidence_and_validates_citations() -> None:
    llm = FakeLLM()
    service, knowledge, historical = _service(llm)
    result = service.resolve("E4037 eSIM activation failed after scanning the QR code")

    assert result.abstained is False
    assert result.complaint_understanding.intent == "troubleshoot"
    assert result.resolution == "The profile may be provisioned incorrectly."
    assert [citation.source_type for citation in result.citations] == [
        "knowledge", "historical_ticket"
    ]
    assert result.citations[0].source_id == "telecom-v1.esim.error-e4037"
    assert result.citations[1].source_id == "historical-ticket:17"
    assert knowledge.requested_limits == [2]
    assert historical.requested_limits == [3]
    prompt = llm.calls[0]["user"]
    assert "AUTHORITATIVE KNOWLEDGE BASE EVIDENCE" in prompt
    assert "HISTORICAL SUPPORT CASE EVIDENCE" in prompt
    assert "historical_agent_response_unverified" in prompt
    assert "E4037" in prompt
    assert "prefer authoritative knowledge" in llm.calls[0]["system"].lower()


def test_invalid_citation_fails_safely() -> None:
    llm = FakeLLM()
    llm.response = {**llm.response, "citations": ["invented-source"]}
    service, _, _ = _service(llm)
    with pytest.raises(ResolutionGenerationError, match="not retrieved"):
        service.resolve("E4037 eSIM activation failed")


def test_missing_relevant_kb_evidence_abstains_without_calling_llm() -> None:
    llm = FakeLLM()
    service, _, history = _service(
        llm, knowledge_hits=[_knowledge_hit(similarity=0.12, lexical_score=0.4)]
    )
    result = service.resolve("My washing machine is leaking")
    assert result.abstained is True
    assert result.resolution == INSUFFICIENT_RESOLUTION
    assert result.steps == ()
    assert result.citations == ()
    assert history.requested_limits == [3]
    assert llm.calls == []


def test_llm_failure_is_reported_as_generation_failure() -> None:
    service, _, _ = _service(FakeLLM(error=TimeoutError("provider timed out")))
    with pytest.raises(ResolutionGenerationError, match="generation failed"):
        service.resolve("E4037 eSIM activation failed")


def test_empty_complaint_is_rejected_before_retrieval() -> None:
    service, knowledge, history = _service(FakeLLM())
    with pytest.raises(ValueError, match="non-whitespace"):
        service.resolve("  ")
    assert knowledge.requested_limits == []
    assert history.requested_limits == []


def test_resolution_runs_structured_understanding_before_retrieval_and_generation() -> None:
    events: list[str] = []

    class SequencedLLM:
        def __init__(self):
            self.calls = 0

        def generate_structured(self, *, system_prompt, user_prompt, schema):
            self.calls += 1
            events.append("understanding" if "intent" in schema["properties"] else "generation")
            if "intent" in schema["properties"]:
                return {
                    "intent": "esim_activation", "category": "esim", "product": "esim",
                    "severity": "medium", "sentiment": "frustrated",
                }
            return {
                "resolution": "Confirm eligibility and retry once.",
                "steps": [{"instruction": "Confirm eligibility.", "citations": ["telecom-v1.esim.error-e4037"]}],
                "escalation": "Escalate if the error returns.",
                "citations": ["telecom-v1.esim.error-e4037"], "abstained": False,
            }

    class OrderedKnowledge(FakeKnowledgeRetriever):
        def search(self, query: str, *, top_k: int = 5):
            events.append("retrieval")
            return super().search(query, top_k=top_k)

    llm = SequencedLLM()
    analyzer = ComplaintUnderstandingService(llm, settings.complaint_taxonomy)
    knowledge = OrderedKnowledge([_knowledge_hit()])
    service = ResolutionService(
        knowledge_retriever=knowledge,
        historical_retriever=FakeHistoricalRetriever([_historical_hit()]),
        complaint_analyzer=analyzer,
        llm_provider=llm,
        knowledge_limit=2,
        historical_limit=3,
    )
    result = service.resolve("E4037 eSIM activation failed")

    assert events == ["understanding", "retrieval", "generation"]
    assert result.complaint_understanding.intent == "esim_activation"
    assert result.citations[0].source_id == "telecom-v1.esim.error-e4037"
