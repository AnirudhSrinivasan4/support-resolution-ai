interface ExampleComplaint {
  title: string;
  category: string;
  text: string;
}

const EXAMPLES: ExampleComplaint[] = [
  {
    title: "eSIM Scan Error",
    category: "Cellular / eSIM",
    text: "E4037 appears when I scan the eSIM QR code during setup.",
  },
  {
    title: "Unauthorized SIM Swap",
    category: "Security / Account",
    text: "Someone moved my number to a new SIM without my permission.",
  },
  {
    title: "Billing Double Charge",
    category: "Payments / Billing",
    text: "I was charged twice for the same recharge on my account balance.",
  },
];

interface ComplaintInputProps {
  complaint: string;
  loading: boolean;
  onComplaintChange: (value: string) => void;
  onSubmit: () => void;
}

export function ComplaintInput({ complaint, loading, onComplaintChange, onSubmit }: ComplaintInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Ctrl+Enter or Cmd+Enter for power users
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && complaint.trim() && !loading) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <section className="panel complaint-panel" aria-labelledby="complaint-title">
      <div className="complaint-panel-header">
        <div className="section-heading-group">
          <div className="eyebrow-wrapper">
            <span className="eyebrow-dot" />
            <span className="eyebrow">Primary Action · Customer Intake</span>
          </div>
          <h2 id="complaint-title">Customer Complaint &amp; Incident Record</h2>
          <p className="panel-description">
            Describe the exact issue reported by the customer to generate a grounded, evidence-backed resolution plan.
          </p>
        </div>
        <span className="field-required-badge">Required</span>
      </div>

      <div className="textarea-container">
        <label className="sr-only" htmlFor="complaint">
          Customer complaint description
        </label>
        <textarea
          id="complaint"
          name="complaint"
          value={complaint}
          onChange={(event) => onComplaintChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Customer reports receiving error code E4037 when scanning the eSIM QR code on iPhone 15..."
          maxLength={4000}
          rows={5}
          disabled={loading}
          aria-describedby="complaint-hint complaint-count"
        />

        <div className="textarea-footer">
          <div className="input-hint" id="complaint-hint">
            <svg viewBox="0 0 20 20" fill="currentColor" className="hint-icon" aria-hidden="true">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <span>Tip: Include error codes, device model, or account context for better grounding.</span>
          </div>

          <div className="char-count-badge" id="complaint-count" aria-label={`${complaint.length} of 4000 characters used`}>
            {complaint.length} / 4000
          </div>
        </div>
      </div>

      <div className="example-section" aria-label="Quick complaint scenarios">
        <div className="example-header">
          <span className="example-label">Pre-loaded Incident Scenarios:</span>
        </div>
        <div className="example-chips">
          {EXAMPLES.map((item) => (
            <button
              className={`example-chip ${complaint === item.text ? "is-selected" : ""}`}
              key={item.title}
              type="button"
              disabled={loading}
              onClick={() => onComplaintChange(item.text)}
              title={`Load: ${item.text}`}
            >
              <span className="example-chip-category">{item.category}</span>
              <span className="example-chip-title">{item.title}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="submit-row">
        <div className="security-notice">
          <svg className="shield-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <span>Grounded AI Engine · Strict Policy Verification</span>
        </div>

        <div className="button-group">
          {complaint && (
            <button
              type="button"
              className="clear-button"
              disabled={loading}
              onClick={() => onComplaintChange("")}
              aria-label="Clear input"
            >
              Clear
            </button>
          )}

          <button
            className="primary-button"
            type="button"
            disabled={!complaint.trim() || loading}
            onClick={onSubmit}
          >
            {loading ? (
              <>
                <span className="button-spinner" aria-hidden="true" />
                <span>Analyzing &amp; Grounding...</span>
              </>
            ) : (
              <>
                <span>Analyze &amp; Resolve Complaint</span>
                <svg className="button-arrow" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </>
            )}
          </button>
        </div>
      </div>
    </section>
  );
}
