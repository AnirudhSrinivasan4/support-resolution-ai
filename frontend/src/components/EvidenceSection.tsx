import { useId, useState } from "react";
import type { ResolutionCitation } from "../types/resolution";

interface EvidenceSectionProps {
  citations: ResolutionCitation[];
}

export function EvidenceSection({ citations }: EvidenceSectionProps) {
  const [activeTab, setActiveTab] = useState<"all" | "knowledge" | "historical_ticket">("all");
  const knowledgeBaseId = useId();
  const historicalTicketsId = useId();

  const kbCitations = citations.filter((c) => c.source_type === "knowledge");
  const ticketCitations = citations.filter((c) => c.source_type === "historical_ticket");

  return (
    <section className="panel evidence-panel" aria-labelledby="evidence-title">
      <div className="evidence-panel-header">
        <div className="section-heading-group">
          <div className="eyebrow-wrapper">
            <svg viewBox="0 0 20 20" fill="currentColor" className="eyebrow-icon" aria-hidden="true">
              <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.969 7.969 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
            </svg>
            <span className="eyebrow">Audit &amp; Grounding Evidence</span>
          </div>
          <h2 id="evidence-title">Retrieved Evidence &amp; Citation Sources</h2>
          <p className="panel-description">
            All AI recommendations are strictly grounded in verified policy documentation and contextual historical tickets.
          </p>
        </div>

        <div className="citation-counters-group">
          <span className="counter-badge counter-kb" title="Authoritative Knowledge Base sources">
            <span className="counter-dot" />
            {kbCitations.length} Knowledge Base
          </span>
          <span className="counter-badge counter-ticket" title="Historical Support Case sources">
            <span className="counter-dot" />
            {ticketCitations.length} Historical Tickets
          </span>
        </div>
      </div>

      {citations.length > 0 && (
        <div className="evidence-tab-bar" role="tablist" aria-label="Evidence categories">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "all"}
            aria-controls="evidence-all-panel"
            className={`tab-btn ${activeTab === "all" ? "is-active" : ""}`}
            onClick={() => setActiveTab("all")}
          >
            All Evidence ({citations.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "knowledge"}
            aria-controls={knowledgeBaseId}
            className={`tab-btn tab-btn-kb ${activeTab === "knowledge" ? "is-active" : ""}`}
            onClick={() => setActiveTab("knowledge")}
          >
            Authoritative KB ({kbCitations.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "historical_ticket"}
            aria-controls={historicalTicketsId}
            className={`tab-btn tab-btn-ticket ${activeTab === "historical_ticket" ? "is-active" : ""}`}
            onClick={() => setActiveTab("historical_ticket")}
          >
            Historical Tickets ({ticketCitations.length})
          </button>
        </div>
      )}

      {citations.length === 0 ? (
        <div className="evidence-empty-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="empty-evidence-icon" aria-hidden="true">
            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p>No citation sources returned for this case.</p>
        </div>
      ) : (
        <div className="evidence-grid">
          {/* AUTHORITATIVE KNOWLEDGE BASE SECTION */}
          {(activeTab === "all" || activeTab === "knowledge") && (
            <div className="evidence-category-column" id={knowledgeBaseId} role="tabpanel" tabIndex={0}>
              <div className="category-column-header kb-header">
                <div className="category-title-group">
                  <span className="category-icon" aria-hidden="true">📘</span>
                  <div>
                    <h3>AUTHORITATIVE KNOWLEDGE BASE</h3>
                    <p className="category-subtitle">Curated procedural guidance &amp; official policy</p>
                  </div>
                </div>
                <span className="kb-badge-count">{kbCitations.length} Documents</span>
              </div>

              {kbCitations.length === 0 ? (
                <div className="no-citations-subtext">No authoritative Knowledge Base articles cited for this response.</div>
              ) : (
                <div className="citation-cards-list">
                  {kbCitations.map((citation) => (
                    <article className="citation-card card-authoritative-kb" key={`kb-${citation.source_id}`}>
                      <div className="citation-card-top">
                        <span className="source-tag source-tag-kb">
                          <span className="tag-icon" aria-hidden="true">✓</span>
                          AUTHORITATIVE
                        </span>
                        <span className="doc-id-pill">ID: <code>{citation.source_id}</code></span>
                      </div>
                      <h4 className="citation-card-title">{citation.title}</h4>
                      <div className="citation-card-footer">
                        <span className="source-type-label">Official Procedure Document</span>
                        <span className="verified-shield" title="Verified against active knowledge repository">
                          Verified Policy 🛡️
                        </span>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* HISTORICAL SUPPORT TICKETS SECTION */}
          {(activeTab === "all" || activeTab === "historical_ticket") && (
            <div className="evidence-category-column" id={historicalTicketsId} role="tabpanel" tabIndex={0}>
              <div className="category-column-header ticket-header">
                <div className="category-title-group">
                  <span className="category-icon" aria-hidden="true">📜</span>
                  <div>
                    <h3>HISTORICAL SUPPORT CASES</h3>
                    <p className="category-subtitle">Contextual reference tickets (supporting evidence)</p>
                  </div>
                </div>
                <span className="ticket-badge-count">{ticketCitations.length} Tickets</span>
              </div>

              {ticketCitations.length === 0 ? (
                <div className="no-citations-subtext">No historical support cases cited for this response.</div>
              ) : (
                <div className="citation-cards-list">
                  {ticketCitations.map((citation) => (
                    <article className="citation-card card-historical-ticket" key={`ticket-${citation.source_id}`}>
                      <div className="citation-card-top">
                        <span className="source-tag source-tag-ticket">
                          HISTORICAL CASE
                        </span>
                        <span className="doc-id-pill">Ticket: <code>#{citation.source_id}</code></span>
                      </div>
                      <h4 className="citation-card-title">{citation.title}</h4>
                      <div className="citation-card-footer">
                        <span className="source-type-label">Past Customer Interaction</span>
                        <span className="contextual-tag" title="Historical ticket context, not binding policy">
                          Contextual Reference 💬
                        </span>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="evidence-disclaimer-box">
        <svg viewBox="0 0 20 20" fill="currentColor" className="info-icon" aria-hidden="true">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
        <div className="disclaimer-text">
          <strong>Evidence Hierarchy Notice:</strong> Knowledge Base articles represent authoritative, compliance-approved procedures. Historical tickets serve as secondary reference context and do not supersede official policy.
        </div>
      </div>
    </section>
  );
}
