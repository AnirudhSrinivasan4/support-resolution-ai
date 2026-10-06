const EXAMPLES = [
  "E4037 appears when I scan the eSIM QR code.",
  "Someone moved my number to a new SIM without my permission.",
  "I was charged twice for the same recharge.",
];

interface ComplaintInputProps {
  complaint: string;
  loading: boolean;
  onComplaintChange: (value: string) => void;
  onSubmit: () => void;
}

export function ComplaintInput({ complaint, loading, onComplaintChange, onSubmit }: ComplaintInputProps) {
  return (
    <section className="panel complaint-panel" aria-labelledby="complaint-title">
      <div className="section-heading complaint-heading">
        <div>
          <p className="eyebrow">New case</p>
          <h2 id="complaint-title">Customer complaint</h2>
          <p className="panel-description">Enter the customer's message to prepare a grounded response for review.</p>
        </div>
        <span className="field-required">Required</span>
      </div>
      <label className="sr-only" htmlFor="complaint">Customer complaint</label>
      <textarea
        id="complaint"
        name="complaint"
        value={complaint}
        onChange={(event) => onComplaintChange(event.target.value)}
        placeholder="Describe the customer's issue..."
        maxLength={4000}
        rows={5}
        disabled={loading}
        aria-describedby="complaint-hint complaint-count"
      />
      <div className="input-meta">
        <span id="complaint-hint">Include relevant details such as error messages or when the issue occurs.</span>
        <span id="complaint-count">{complaint.length}/4000</span>
      </div>
      <div className="example-row" aria-label="Example complaints">
        <span className="example-label">Try an example</span>
        <div className="example-chips">
          {EXAMPLES.map((example) => (
            <button
              className="example-chip"
              key={example}
              type="button"
              disabled={loading}
              onClick={() => onComplaintChange(example)}
            >
              {example}
            </button>
          ))}
        </div>
      </div>
      <div className="submit-row">
        <span className="privacy-note"><span aria-hidden="true">◈</span> For support-agent use</span>
        <button className="primary-button" type="button" disabled={!complaint.trim() || loading} onClick={onSubmit}>
          {loading ? <><span className="button-spinner" aria-hidden="true" /> Analyzing…</> : <>Analyze &amp; Resolve <span aria-hidden="true">→</span></>}
        </button>
      </div>
    </section>
  );
}
