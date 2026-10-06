import { useEffect, useState } from "react";
import { ApiError, checkApiHealth, createResolution } from "../api/resolutions";
import { ComplaintInput } from "../components/ComplaintInput";
import { EvidenceSection } from "../components/EvidenceSection";
import { Header } from "../components/Header";
import { AbstentionCard, EscalationCard, ResolutionCard, UnderstandingCard } from "../components/ResolutionPanels";
import { EmptyState, ErrorState, LoadingState } from "../components/StatusStates";
import { WorkflowBar } from "../components/WorkflowBar";
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

  const currentWorkflowStage = loading
    ? "loading"
    : response?.abstained
    ? "abstained"
    : response
    ? "resolved"
    : error
    ? "error"
    : "input";

  return (
    <div className="app-shell">
      <Header apiStatus={apiStatus} />

      <main id="main" className="main-content">
        <div className="page-heading">
          <div className="page-title-group">
            <div className="eyebrow-wrapper">
              <span className="eyebrow-pill">CUSTOMER OPERATIONS DESK</span>
              <span className="environment-pill">PROD-US-EAST</span>
            </div>
            <h1>AI Support Resolution Assistant</h1>
            <p className="page-subtitle">
              Intelligent triage, grounded resolution drafting, and evidence verification for enterprise support agents.
            </p>
          </div>

          <div className="workspace-badge">
            <svg viewBox="0 0 20 20" fill="currentColor" className="badge-icon" aria-hidden="true">
              <path fillRule="evenodd" d="M6 6V5a3 3 0 013-3h2a3 3 0 013 3v1h2a2 2 0 012 2v3.57A22.952 22.952 0 0110 13a22.95 22.95 0 01-8-1.43V8a2 2 0 012-2h2zm2-1a1 1 0 011-1h2a1 1 0 011 1v1H8V5zm1 5a1 1 0 011-1h.01a1 1 0 110 2H10a1 1 0 01-1-1z" clipRule="evenodd" />
              <path d="M2 13.692V16a2 2 0 002 2h12a2 2 0 002-2v-2.308A24.974 24.974 0 0110 15c-2.796 0-5.487-.46-8-1.308z" />
            </svg>
            <span>Tier-2 Agent Console</span>
          </div>
        </div>

        <WorkflowBar currentStage={currentWorkflowStage} />

        <div className="workspace-grid">
          <div className="primary-column">
            <ComplaintInput
              complaint={complaint}
              loading={loading}
              onComplaintChange={setComplaint}
              onSubmit={() => void submitComplaint()}
            />

            {error && <ErrorState message={error} onDismiss={() => setError(null)} />}

            {loading && <LoadingState />}

            {!loading && !resultVisible && !error && <EmptyState />}

            {!loading && response && (
              <div className="results-container">
                {response.abstained ? (
                  <AbstentionCard escalation={response.escalation} />
                ) : (
                  <ResolutionCard resolution={response.resolution} steps={response.steps} />
                )}

                {!response.abstained && <EscalationCard guidance={response.escalation} />}

                <EvidenceSection citations={response.citations} />
              </div>
            )}
          </div>

          {response && (
            <aside className="secondary-column" aria-label="Complaint triage summary">
              <UnderstandingCard data={response.complaint_understanding} />
              <div className="agent-policy-note">
                <div className="note-header">
                  <svg viewBox="0 0 20 20" fill="currentColor" className="note-icon" aria-hidden="true">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <strong>Agent Policy Standard</strong>
                </div>
                <p>
                  Always verify cited Knowledge Base articles before communicating resolutions directly to customers. AI outputs are advisory.
                </p>
              </div>
            </aside>
          )}
        </div>

        <footer className="page-footer">
          <div className="footer-left">
            <span className="footer-dot" />
            <span>Support Operations Platform v2.4 · Grounded LLM Pipeline</span>
          </div>
          <div className="footer-right">
            <span>Confidential · Internal Agent Use Only</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
