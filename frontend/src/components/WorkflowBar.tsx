interface WorkflowBarProps {
  currentStage: "input" | "loading" | "resolved" | "abstained" | "error";
}

export function WorkflowBar({ currentStage }: WorkflowBarProps) {
  const steps = [
    { id: "complaint", label: "1. Customer Complaint", desc: "Triage & Entry" },
    { id: "understanding", label: "2. AI Understanding", desc: "Intent & Severity" },
    { id: "resolution", label: "3. Resolution", desc: "Grounded Steps" },
    { id: "evidence", label: "4. Evidence & Sources", desc: "Authoritative KB vs Ticket" },
    { id: "escalation", label: "5. Escalation Review", desc: "Operational Guidance" },
  ];

  const isActive = (stepId: string) => {
    if (currentStage === "loading") return stepId === "complaint" || stepId === "understanding";
    if (currentStage === "resolved" || currentStage === "abstained") return true;
    return stepId === "complaint";
  };

  return (
    <div className="workflow-bar-container" aria-label="Resolution Pipeline Stage">
      <div className="workflow-bar">
        {steps.map((step, idx) => {
          const active = isActive(step.id);
          return (
            <div key={step.id} className={`workflow-step ${active ? "is-active" : ""}`}>
              <div className="step-indicator">
                <span className="step-number">{idx + 1}</span>
                {active && <span className="step-active-glow" aria-hidden="true" />}
              </div>
              <div className="step-content">
                <span className="step-label">{step.label}</span>
                <span className="step-desc">{step.desc}</span>
              </div>
              {idx < steps.length - 1 && (
                <div className="step-connector" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
