import { useEffect, useState } from "react";

export function LoadingState() {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    "Analyzing complaint text & classifying intent",
    "Searching Knowledge Base & historical case corpus",
    "Validating citation grounding & policy safety",
    "Formatting step-by-step resolution plan",
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 1500);
    return () => clearInterval(timer);
  }, [steps.length]);

  return (
    <section className="panel loading-panel" role="status" aria-live="polite" aria-label="Processing resolution">
      <div className="loading-content-wrapper">
        <div className="spinner-container">
          <div className="large-spinner-ring" />
          <div className="spinner-center-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
          </div>
        </div>

        <div className="loading-text-group">
          <div className="loading-badge">
            <span className="pulsing-pulse" />
            <span>AI RESOLUTION PIPELINE IN PROGRESS</span>
          </div>
          <h2>Preparing Grounded Support Plan</h2>
          <p className="loading-description">
            The AI engine is retrieving official policies and matching historical cases to produce an audit-verified response.
          </p>

          <div className="loading-steps-progress">
            {steps.map((stepText, idx) => {
              const isDone = idx < activeStep;
              const isCurrent = idx === activeStep;
              return (
                <div
                  key={stepText}
                  className={`loading-step-item ${isDone ? "is-done" : isCurrent ? "is-current" : "is-pending"}`}
                >
                  <span className="step-check-icon">
                    {isDone ? "✓" : isCurrent ? "•" : String(idx + 1)}
                  </span>
                  <span className="step-text-label">{stepText}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

export function ErrorState({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <section className="error-panel" role="alert" aria-label="Error alert">
      <div className="error-icon-box" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>

      <div className="error-details">
        <strong>Request Execution Error</strong>
        <p>{message}</p>
      </div>

      <button type="button" className="error-dismiss-btn" aria-label="Dismiss error" onClick={onDismiss}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </section>
  );
}

export function EmptyState() {
  return (
    <section className="empty-state-panel" aria-label="Ready for input">
      <div className="empty-state-inner">
        <div className="empty-icon-shield" aria-hidden="true">
          <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M24 4L6 12v12c0 11.5 8 22.5 18 24 10-1.5 18-12.5 18-24V12L24 4z" />
            <path d="M16 22l6 6 10-10" />
          </svg>
        </div>

        <div className="empty-text-content">
          <span className="empty-eyebrow">READY FOR INTAKE</span>
          <h2>AI-Assisted Service Desk Console</h2>
          <p>
            Enter a customer complaint or select a pre-loaded incident scenario above to generate an audit-ready, grounded resolution with verified evidence citations.
          </p>

          <div className="empty-features-grid">
            <div className="feature-item">
              <span className="feature-bullet">1</span>
              <div>
                <strong>Automated Triage</strong>
                <p>Extracts Intent, Category, Product, Sentiment, &amp; Severity</p>
              </div>
            </div>

            <div className="feature-item">
              <span className="feature-bullet">2</span>
              <div>
                <strong>Grounded Guidance</strong>
                <p>Generates step-by-step agent instructions with copy actions</p>
              </div>
            </div>

            <div className="feature-item">
              <span className="feature-bullet">3</span>
              <div>
                <strong>Evidence Hierarchy</strong>
                <p>Separates Authoritative KB from Historical Support Cases</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
