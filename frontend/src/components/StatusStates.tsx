export function LoadingState() {
  return (
    <section className="panel loading-panel" role="status" aria-live="polite">
      <span className="large-spinner" aria-hidden="true" />
      <div>
        <h2>Preparing grounded resolution</h2>
        <p>Analyzing the complaint and preparing evidence for agent review. This may take a moment.</p>
      </div>
    </section>
  );
}

export function ErrorState({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <section className="error-panel" role="alert">
      <span className="error-mark" aria-hidden="true">!</span>
      <div><strong>We couldn’t complete the request</strong><p>{message}</p></div>
      <button type="button" className="icon-button" aria-label="Dismiss error" onClick={onDismiss}>×</button>
    </section>
  );
}

export function EmptyState() {
  return (
    <section className="empty-state" aria-label="Getting started">
      <div className="empty-icon" aria-hidden="true">
        <svg viewBox="0 0 48 48" fill="none"><path d="M10 13.5A4.5 4.5 0 0 1 14.5 9h19a4.5 4.5 0 0 1 4.5 4.5v14a4.5 4.5 0 0 1-4.5 4.5H24l-9 7v-7h-.5a4.5 4.5 0 0 1-4.5-4.5v-14Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/><path d="M17 19h14M17 25h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
      </div>
      <div>
        <p className="eyebrow">Ready when you are</p>
        <h2>AI-assisted support resolution</h2>
        <p>Enter a customer complaint to understand the issue, retrieve relevant evidence, and prepare a grounded resolution with citations.</p>
      </div>
    </section>
  );
}
