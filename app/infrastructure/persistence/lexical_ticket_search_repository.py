"""PostgreSQL full-text search adapter for historical ticket complaints."""

import re
from collections.abc import Sequence

from sqlalchemy import Text, cast, func, literal, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.domain.models import LexicalTicketResult
from app.infrastructure.persistence.models import HistoricalTicketRecord

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "but",
    "by", "can", "could", "did", "do", "does", "for", "from", "had", "has",
    "have", "he", "her", "here", "hers", "him", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "me", "my", "not", "of", "on", "or",
    "our", "ours", "she", "so", "such", "than", "that", "the", "their",
    "them", "there", "these", "they", "this", "those", "through", "to",
    "was", "we", "were", "what", "when", "where", "which", "while", "who",
    "will", "with", "would", "you", "your", "same",
    "aber", "als", "also", "am", "an", "auch", "auf", "aus", "bei", "bin",
    "bis", "da", "das", "dass", "dein", "dem", "den", "der", "des", "die",
    "dies", "doch", "durch", "ein", "eine", "einer", "eines", "er", "es",
    "für", "hat", "ich", "im", "in", "ist", "kann", "kein", "mit", "mich",
    "mir", "nach", "nicht", "noch", "oder", "sein", "sich", "sie", "und",
    "uns", "vom", "von", "war", "was", "weil", "werden", "wie", "wir", "zu",
    "zum", "zur",
}


def build_lexical_query(query: str) -> str:
    """Build a safe OR query from complaint terms to favor recall on paraphrases."""
    terms = [
        term
        for term in re.findall(r"[\w]+", query, flags=re.UNICODE)
        if len(term) > 1 and term.casefold() not in _STOP_WORDS
    ]
    return " OR ".join(f'"{term}"' for term in terms)


class SQLAlchemyLexicalTicketSearchRepository:
    """Search subject/body only; historical answers are not complaint-search text."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def search_by_text(self, *, query: str, limit: int) -> Sequence[LexicalTicketResult]:
        normalized_query = query.strip()
        if not normalized_query:
            return ()
        if limit < 1:
            raise ValueError("limit must be positive")

        lexical_query = build_lexical_query(normalized_query)
        if not lexical_query:
            return ()
        text_query = func.websearch_to_tsquery(
            literal("simple", type_=REGCONFIG()),
            cast(literal(lexical_query), Text()),
        )
        rank = func.ts_rank_cd(HistoricalTicketRecord.search_vector, text_query)
        statement = (
            select(HistoricalTicketRecord, rank.label("lexical_score"))
            .options(selectinload(HistoricalTicketRecord.tags))
            .where(HistoricalTicketRecord.search_vector.op("@@")(text_query))
            .order_by(rank.desc(), HistoricalTicketRecord.id.asc())
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).all()

        return tuple(
            LexicalTicketResult(
                ticket_id=ticket.id,
                subject=ticket.subject,
                body=ticket.body,
                answer=ticket.answer,
                queue=ticket.queue,
                ticket_type=ticket.ticket_type,
                priority=ticket.priority,
                language=ticket.language,
                tags=tuple(
                    tag.value for tag in sorted(ticket.tags, key=lambda item: item.position)
                ),
                lexical_score=float(lexical_score),
                source_dataset=ticket.source_dataset,
                source_split=ticket.source_split,
                source_record_id=ticket.source_record_id,
                source_revision=ticket.source_revision,
            )
            for ticket, lexical_score in rows
        )
