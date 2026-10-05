"""Small domain contracts shared by future service and adapter layers."""

from dataclasses import dataclass, field
from typing import Literal, Mapping, Sequence

SourceKind = Literal["historical_ticket", "knowledge_article"]


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """A retrievable historical ticket or knowledge-base document."""

    source_id: str
    kind: SourceKind
    title: str
    content: str
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Search input with text and an optional precomputed dense vector."""

    text: str
    embedding: Sequence[float] | None = None
    limit: int = 10
    filters: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A source document and its retrieval score."""

    document: SourceDocument
    score: float


@dataclass(frozen=True, slots=True)
class ComplaintAnalysis:
    """Structured complaint fields; class names remain data-driven."""

    intent: str | None = None
    product: str | None = None
    severity: str | None = None
    sentiment: str | None = None
    confidence: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResolutionStep:
    """One proposed action with identifiers for supporting sources."""

    instruction: str
    citation_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolutionDraft:
    """Draft advice or an explicit abstention for agent review."""

    steps: tuple[ResolutionStep, ...] = ()
    abstained: bool = False
    escalation_reason: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalTicketTag:
    """A non-empty source tag and its original one-based tag column position."""

    position: int
    value: str


@dataclass(frozen=True, slots=True)
class HistoricalTicket:
    """A historical support ticket with stable source provenance."""

    source_dataset: str
    source_split: str
    source_record_id: str
    source_revision: str | None
    subject: str | None
    body: str | None
    answer: str | None
    ticket_type: str | None
    queue: str | None
    priority: str | None
    language: str | None
    version: str | None
    tags: tuple[HistoricalTicketTag, ...] = ()


@dataclass(frozen=True, slots=True)
class IngestionBatchResult:
    """Counts for one persisted batch."""

    processed: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0

    def __add__(self, other: "IngestionBatchResult") -> "IngestionBatchResult":
        return IngestionBatchResult(
            processed=self.processed + other.processed,
            inserted=self.inserted + other.inserted,
            updated=self.updated + other.updated,
            unchanged=self.unchanged + other.unchanged,
        )
