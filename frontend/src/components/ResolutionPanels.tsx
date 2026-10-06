import type { ComplaintUnderstanding, ResolutionCitation } from "../types/resolution";

export function formatLabel(value: string): string {
  const special: Record<string, string> = {
    esim: "eSIM",
    fifth_generation_mobile: "5G Mobile",
    sim: "SIM",
  };
  if (special[value]) return special[value];
  return value
    .split("_")
    .map((part) => special[part] ?? part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function UnderstandingCard({ data }: { data: ComplaintUnderstanding }) {
  const values = [
    ["Intent", formatLabel(data.intent)],
    ["Category", formatLabel(data.category)],
    ["Product", formatLabel(data.product)],
    ["Sentiment", formatLabel(data.sentiment)],
  ] as const;

  return (
    <section className="panel understanding-panel" aria-labelledby="understanding-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Triage</p>
          <h2 id="understanding-title">AI understanding</h2>
        </div>
        <span className={`severity-badge severity-${data.severity}`}>{formatLabel(data.severity)}</span>
      </div>
      <dl className="understanding-grid">
        {values.map(([label, value]) => (
          <div className="understanding-item" key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function ResolutionCard({ resolution, steps }: { resolution: string; steps: string[] }) {
  return (
    <section className="panel resolution-panel" aria-labelledby="resolution-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Agent guidance</p>
          <h2 id="resolution-title">Recommended resolution</h2>
        </div>
        <span className="draft-label"><span aria-hidden="true" /> Grounded draft</span>
      </div>
      <p className="resolution-copy">{resolution}</p>
      {steps.length > 0 && (
        <div className="steps-block">
          <h3>Resolution steps</h3>
          <ol className="steps-list">
            {steps.map((step, index) => <li key={`${index}-${step}`}>{step}</li>)}
          </ol>
        </div>
      )}
    </section>
  );
}

export function EscalationCard({ guidance }: { guidance: string }) {
  return (
    <section className="escalation-panel" aria-labelledby="escalation-title">
      <div className="escalation-icon" aria-hidden="true">!</div>
      <div>
        <p className="eyebrow">Operational guidance</p>
        <h2 id="escalation-title">Escalation guidance</h2>
        <p>{guidance}</p>
      </div>
    </section>
  );
}

export function EvidenceCard({ citations }: { citations: ResolutionCitation[] }) {
  return (
    <section className="panel evidence-panel" aria-labelledby="evidence-title">
      <div className="section-heading evidence-heading">
        <div>
          <p className="eyebrow">Grounding</p>
          <h2 id="evidence-title">Evidence &amp; sources</h2>
        </div>
        <span className="source-count">{citations.length} {citations.length === 1 ? "source" : "sources"}</span>
      </div>
      {citations.length === 0 ? (
        <p className="muted-copy">No sources were returned for this case.</p>
      ) : (
        <ul className="citation-list">
          {citations.map((citation) => {
            const authoritative = citation.source_type === "knowledge";
            return (
              <li className="citation-item" key={`${citation.source_type}-${citation.source_id}`}>
                <span className={`source-kind ${authoritative ? "source-kind-knowledge" : "source-kind-history"}`}>
                  {authoritative ? "Knowledge Base" : "Historical Ticket"}
                </span>
                <div className="citation-details">
                  <strong>{citation.title}</strong>
                  <span>Source ID: <code>{citation.source_id}</code></span>
                </div>
                <span className="citation-chevron" aria-hidden="true">↗</span>
              </li>
            );
          })}
        </ul>
      )}
      <p className="evidence-note">
        Knowledge Base sources provide curated procedural guidance. Historical tickets are supporting context, not verified policy.
      </p>
    </section>
  );
}

export function AbstentionCard({ escalation }: { escalation: string }) {
  return (
    <section className="abstention-panel" role="status" aria-labelledby="abstention-title">
      <div className="abstention-mark" aria-hidden="true">i</div>
      <div>
        <p className="eyebrow">Review required</p>
        <h2 id="abstention-title">Insufficient evidence</h2>
        <p>Unable to provide a grounded resolution for this complaint. Please have a support agent review the case.</p>
        <p className="abstention-escalation">{escalation}</p>
      </div>
    </section>
  );
}
