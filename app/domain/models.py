"""Small domain contracts shared by future service and adapter layers."""

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Literal, Mapping, Sequence

SourceKind = Literal["historical_ticket", "knowledge_article"]
_NORMALIZED_LABEL = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


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
    """Validated, controlled complaint classification for support triage."""

    intent: str
    category: str
    product: str
    severity: str
    sentiment: str


@dataclass(frozen=True, slots=True)
class ComplaintTaxonomy:
    """Allowed normalized classes; intent/category/product can be configured."""

    intents: tuple[str, ...]
    categories: tuple[str, ...]
    products: tuple[str, ...]
    severities: tuple[str, ...] = ("low", "medium", "high", "critical", "unknown")
    sentiments: tuple[str, ...] = (
        "positive", "neutral", "frustrated", "angry", "negative", "unknown"
    )

    def __post_init__(self) -> None:
        for label, values in (
            ("intents", self.intents),
            ("categories", self.categories),
            ("products", self.products),
            ("severities", self.severities),
            ("sentiments", self.sentiments),
        ):
            if not values or len(values) != len(set(values)):
                raise ValueError(f"{label} must be a non-empty list of unique values")
            if "unknown" not in values:
                raise ValueError(f"{label} must include unknown")
            if any(not _NORMALIZED_LABEL.fullmatch(value) for value in values):
                raise ValueError(f"{label} values must be lowercase normalized identifiers")


@dataclass(frozen=True, slots=True)
class ResolutionStep:
    """One proposed action with identifiers for supporting sources."""

    instruction: str
    citation_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolutionDraft:
    """Grounded advice or an explicit abstention for agent review."""

    resolution: str = ""
    steps: tuple[ResolutionStep, ...] = ()
    citations: tuple["ResolutionCitation", ...] = ()
    escalation: str = ""
    abstained: bool = False
    escalation_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ResolutionCitation:
    """A validated reference to a retrieved source."""

    source_type: Literal["knowledge", "historical_ticket"]
    source_id: str
    title: str


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


@dataclass(frozen=True, slots=True)
class TicketEmbeddingCandidate:
    """Ticket text and any matching-model embedding metadata needed for reuse."""

    ticket_id: int
    subject: str | None
    body: str | None
    existing_source_text_hash: str | None = None
    existing_dimension: int | None = None


@dataclass(frozen=True, slots=True)
class TicketEmbedding:
    """A vector derived from one ticket's subject and body."""

    ticket_id: int
    model_identifier: str
    dimension: int
    source_text_hash: str
    vector: Sequence[float]


@dataclass(frozen=True, slots=True)
class EmbeddingBatchResult:
    """Progress counters from a bounded embedding run."""

    processed: int = 0
    embedded: int = 0
    reused: int = 0
    skipped_no_text: int = 0
    errors: int = 0

    def __add__(self, other: "EmbeddingBatchResult") -> "EmbeddingBatchResult":
        return EmbeddingBatchResult(
            processed=self.processed + other.processed,
            embedded=self.embedded + other.embedded,
            reused=self.reused + other.reused,
            skipped_no_text=self.skipped_no_text + other.skipped_no_text,
            errors=self.errors + other.errors,
        )


@dataclass(frozen=True, slots=True)
class SemanticTicketResult:
    """Historical ticket returned by semantic search, without its raw vector."""

    ticket_id: int
    subject: str | None
    body: str | None
    answer: str | None
    queue: str | None
    ticket_type: str | None
    priority: str | None
    language: str | None
    tags: tuple[str, ...]
    similarity: float
    source_dataset: str
    source_split: str
    source_record_id: str
    source_revision: str | None


@dataclass(frozen=True, slots=True)
class LexicalTicketResult:
    """Historical ticket returned by PostgreSQL full-text search."""

    ticket_id: int
    subject: str | None
    body: str | None
    answer: str | None
    queue: str | None
    ticket_type: str | None
    priority: str | None
    language: str | None
    tags: tuple[str, ...]
    lexical_score: float
    source_dataset: str
    source_split: str
    source_record_id: str
    source_revision: str | None


@dataclass(frozen=True, slots=True)
class HybridTicketResult:
    """RRF-ranked result with original modality ranks and raw modality scores."""

    ticket: SemanticTicketResult | LexicalTicketResult
    fused_score: float
    semantic_rank: int | None
    semantic_score: float | None
    lexical_rank: int | None
    lexical_score: float | None


@dataclass(frozen=True, slots=True)
class TelecomKnowledgeDocument:
    """Curated authoritative telecom guidance, separate from historical tickets."""

    document_id: str
    title: str
    content: str
    category: str
    product: str
    severity: str
    escalation_conditions: str
    source: str
    version: str


def telecom_knowledge_content_hash(document: TelecomKnowledgeDocument) -> str:
    """Hash all curated fields so any metadata or procedure edit invalidates vectors."""
    canonical = {
        "document_id": document.document_id,
        "title": document.title,
        "content": document.content,
        "category": document.category,
        "product": document.product,
        "severity": document.severity,
        "escalation_conditions": document.escalation_conditions,
        "source": document.source,
        "version": document.version,
    }
    payload = json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class KnowledgeIngestionResult:
    processed: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    embedded: int = 0
    reused: int = 0


@dataclass(frozen=True, slots=True)
class KnowledgeEmbeddingCandidate:
    document: TelecomKnowledgeDocument
    content_hash: str
    existing_content_hash: str | None = None
    existing_dimension: int | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeDocumentEmbedding:
    document_id: str
    model_identifier: str
    dimension: int
    content_hash: str
    vector: Sequence[float]


@dataclass(frozen=True, slots=True)
class KnowledgeSemanticHit:
    document: TelecomKnowledgeDocument
    similarity: float


@dataclass(frozen=True, slots=True)
class KnowledgeLexicalHit:
    document: TelecomKnowledgeDocument
    lexical_score: float


@dataclass(frozen=True, slots=True)
class KnowledgeSearchHit:
    document: TelecomKnowledgeDocument
    fused_score: float
    semantic_rank: int | None
    semantic_score: float | None
    lexical_rank: int | None
    lexical_score: float | None
