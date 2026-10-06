import { useEffect, useState } from "react";
import { ApiError, checkApiHealth, createResolution } from "../api/resolutions";
import { ComplaintInput } from "../components/ComplaintInput";
import { AbstentionCard, EscalationCard, EvidenceCard, ResolutionCard, UnderstandingCard } from "../components/ResolutionPanels";
import { EmptyState, ErrorState, LoadingState } from "../components/StatusStates";
import type { ResolutionResponse } from "../types/resolution";

type ApiStatus = "checking" | "available" | "unavailable";

export function ResolutionPage() {
  const [complaint, setComplaint] = useState("");
  const [response, setResponse] = useState<ResolutionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let active = true;
    const check = async () => {
      const available = await checkApiHealth();
      if (active) setApiStatus(available ? "available" : "unavailable");
    };
    void check();
    const timer = window.setInterval(() => void check(), 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  async function submitComplaint() {
    const value = complaint.trim();
    if (!value || loading) return;
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      setResponse(await createResolution(value));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "An unexpected error occurred. Please retry.");
    } finally {
      setLoading(false);
    }
  }

  const resultVisible = response !== null;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <a className="brand" href="#main" aria-label="AI Support Resolution Assistant home">
            <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M6 8.5A3.5 3.5 0 0 1 9.5 5h13A3.5 3.5 0 0 1 26 8.5v9a3.5 3.5 0 0 1-3.5 3.5H16l-6 5v-5h-.5A3.5 3.5 0 0 1 6 17.5v-9Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><path d="M11 11h10M11 15h7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg></span>
            <span className="brand-copy"><strong>Support Desk</strong><span>Resolution workspace</span></span>
          </a>
          <div className={`api-status api-status-${apiStatus}`} role="status" aria-live="polite">
            <span className="status-dot" aria-hidden="true" />
            <span>{apiStatus === "checking" ? "Checking API" : apiStatus === "available" ? "API available" : "API unavailable"}</span>
          </div>
        </div>
      </header>

      <main id="main" className="main-content">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Customer operations</p>
            <h1>AI Support Resolution Assistant</h1>
            <p>AI-assisted customer support resolution with grounded evidence.</p>
          </div>
          <div className="workspace-label"><span aria-hidden="true">▦</span> Agent workspace</div>
        </div>

        <div className="workspace-grid">
          <div className="primary-column">
            <ComplaintInput complaint={complaint} loading={loading} onComplaintChange={setComplaint} onSubmit={() => void submitComplaint()} />
            {error && <ErrorState message={error} onDismiss={() => setError(null)} />}
            {loading && <LoadingState />}
            {!loading && !resultVisible && !error && <EmptyState />}
            {!loading && response && (
              <>
                {response.abstained ? (
                  <AbstentionCard escalation={response.escalation} />
                ) : (
                  <ResolutionCard resolution={response.resolution} steps={response.steps} />
                )}
                {!response.abstained && <EscalationCard guidance={response.escalation} />}
                <EvidenceCard citations={response.citations} />
              </>
            )}
          </div>
          {response && (
            <aside className="secondary-column" aria-label="Complaint triage">
              <UnderstandingCard data={response.complaint_understanding} />
              <div className="agent-note"><span aria-hidden="true">ⓘ</span><p>Review the suggested guidance and sources before responding to the customer.</p></div>
            </aside>
          )}
        </div>
        <footer className="page-footer"><span>AI-generated guidance requires agent review.</span><span>Support Resolution Assistant</span></footer>
      </main>
    </div>
  );
}
