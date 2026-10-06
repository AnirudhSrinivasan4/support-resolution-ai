import { useState } from "react";
import type { ComplaintUnderstanding, Severity, Sentiment } from "../types/resolution";

export function formatLabel(value: string): string {
  const special: Record<string, string> = {
    esim: "eSIM",
    fifth_generation_mobile: "5G Mobile",
    sim: "SIM",
  };
  const key = value.toLowerCase();
  const match = special[key];
  if (match) return match;
  return value
    .split("_")
    .map((part) => {
      const pKey = part.toLowerCase();
      return special[pKey] ?? (part.charAt(0).toUpperCase() + part.slice(1));
    })
    .join(" ");
}

export function getSeverityBadge(severity: Severity) {
  const severityMap: Record<Severity, { label: string; icon: string; className: string }> = {
    low: { label: "LOW SEVERITY", icon: "🟢", className: "severity-low" },
    medium: { label: "MEDIUM SEVERITY", icon: "🟡", className: "severity-medium" },
    high: { label: "HIGH SEVERITY", icon: "🟠", className: "severity-high" },
    critical: { label: "CRITICAL SEVERITY", icon: "🚨", className: "severity-critical" },
    unknown: { label: "UNKNOWN SEVERITY", icon: "⚪", className: "severity-unknown" },
  };
  const current = severityMap[severity] ?? severityMap.unknown;
  return (
    <span className={`severity-badge ${current.className}`}>
      <span className="severity-icon" aria-hidden="true">{current.icon}</span>
      <span>{current.label}</span>
    </span>
  );
}

export function getSentimentBadge(sentiment: Sentiment) {
  const sentimentMap: Record<Sentiment, { label: string; icon: string; className: string }> = {
    positive: { label: "Positive", icon: "😊", className: "sentiment-positive" },
    neutral: { label: "Neutral", icon: "😐", className: "sentiment-neutral" },
    frustrated: { label: "Frustrated", icon: "😤", className: "sentiment-frustrated" },
    angry: { label: "Angry", icon: "😡", className: "sentiment-angry" },
    negative: { label: "Negative", icon: "😟", className: "sentiment-negative" },
    unknown: { label: "Unknown", icon: "❓", className: "sentiment-unknown" },
  };
  const current = sentimentMap[sentiment] ?? sentimentMap.unknown;
  return (
    <span className={`sentiment-badge ${current.className}`}>
      <span aria-hidden="true">{current.icon}</span>
      <span>{current.label}</span>
    </span>
  );
}

export function UnderstandingCard({ data }: { data: ComplaintUnderstanding }) {
  return (
    <section className="panel understanding-panel" aria-labelledby="understanding-title">
      <div className="panel-header-row">
        <div>
          <span className="eyebrow">AI Automated Triage</span>
          <h2 id="understanding-title">Complaint Understanding</h2>
        </div>
        {getSeverityBadge(data.severity)}
      </div>

      <div className="understanding-grid">
        <div className="understanding-item">
          <span className="understanding-label">Intent Classification</span>
          <div className="understanding-value-chip intent-chip">
            <svg viewBox="0 0 20 20" fill="currentColor" className="chip-icon" aria-hidden="true">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
            <strong>{formatLabel(data.intent)}</strong>
          </div>
        </div>

        <div className="understanding-item">
          <span className="understanding-label">Domain Category</span>
          <div className="understanding-value-chip">
            <span className="chip-bullet" />
            <span>{formatLabel(data.category)}</span>
          </div>
        </div>

        <div className="understanding-item">
          <span className="understanding-label">Affected Product</span>
          <div className="understanding-value-chip">
            <span className="chip-bullet" />
            <span>{formatLabel(data.product)}</span>
          </div>
        </div>

        <div className="understanding-item">
          <span className="understanding-label">Customer Sentiment</span>
          <div className="understanding-sentiment-wrapper">
            {getSentimentBadge(data.sentiment)}
          </div>
        </div>
      </div>
    </section>
  );
}

export function ResolutionCard({ resolution, steps }: { resolution: string; steps: string[] }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const fullText = `${resolution}\n\nResolution Steps:\n` + steps.map((s, i) => `${i + 1}. ${s}`).join("\n");
    void navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="panel resolution-panel" aria-labelledby="resolution-title">
      <div className="resolution-card-header">
        <div className="section-heading-group">
          <div className="eyebrow-wrapper">
            <span className="eyebrow-star" aria-hidden="true">★</span>
            <span className="eyebrow">Agent Guidance · Grounded Draft</span>
          </div>
          <h2 id="resolution-title">Recommended Customer Resolution</h2>
        </div>

        <div className="resolution-actions">
          <span className="grounded-badge">
            <span className="badge-dot" aria-hidden="true" />
            Grounded AI Output
          </span>
          <button
            type="button"
            className="copy-button"
            onClick={handleCopy}
            title="Copy resolution to clipboard"
          >
            {copied ? (
              <>
                <svg viewBox="0 0 20 20" fill="currentColor" className="copy-icon" aria-hidden="true">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span>Copied!</span>
              </>
            ) : (
              <>
                <svg viewBox="0 0 20 20" fill="currentColor" className="copy-icon" aria-hidden="true">
                  <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                  <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
                </svg>
                <span>Copy Draft</span>
              </>
            )}
          </button>
        </div>
      </div>

      <div className="resolution-body">
        <div className="resolution-summary-box">
          <p className="resolution-copy">{resolution}</p>
        </div>

        {steps.length > 0 && (
          <div className="steps-section">
            <div className="steps-header">
              <h3 className="steps-title">Actionable Step-by-Step Sequence</h3>
              <span className="steps-count-pill">{steps.length} Steps</span>
            </div>
            <ol className="steps-list">
              {steps.map((step, index) => (
                <li key={`${index}-${step}`} className="step-card">
                  <div className="step-number-badge" aria-hidden="true">
                    <span>{String(index + 1).padStart(2, "0")}</span>
                  </div>
                  <div className="step-content">
                    <p className="step-text">{step}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </section>
  );
}

export function EscalationCard({ guidance }: { guidance: string }) {
  if (!guidance || guidance.trim().length === 0) return null;

  return (
    <section className="escalation-panel" aria-labelledby="escalation-title">
      <div className="escalation-badge-header">
        <div className="escalation-icon-wrapper" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="currentColor" className="escalation-icon">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </div>
        <div>
          <span className="eyebrow escalation-eyebrow">Operational Guidance &amp; Escalation Criteria</span>
          <h2 id="escalation-title">Escalation Protocol</h2>
        </div>
      </div>
      <div className="escalation-content">
        <p>{guidance}</p>
      </div>
    </section>
  );
}

export function AbstentionCard({ escalation }: { escalation: string }) {
  return (
    <section className="abstention-panel" role="status" aria-labelledby="abstention-title">
      <div className="abstention-header">
        <div className="abstention-shield-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <div>
          <span className="eyebrow abstention-eyebrow">AI Safety Guardrail Triggered</span>
          <h2 id="abstention-title">Insufficient Evidence — Abstention Policy Engaged</h2>
        </div>
      </div>

      <div className="abstention-body">
        <p className="abstention-explanation">
          The resolution engine intentionally abstained from generating an automated procedure because the retrieved evidence did not meet the confidence or policy verification threshold.
        </p>

        {escalation && (
          <div className="abstention-escalation-box">
            <strong>Escalation Action Required:</strong>
            <p>{escalation}</p>
          </div>
        )}
      </div>
    </section>
  );
}
