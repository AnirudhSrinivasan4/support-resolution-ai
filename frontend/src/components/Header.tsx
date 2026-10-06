import { ThemeToggle } from "./ThemeToggle";

type ApiStatus = "checking" | "available" | "unavailable";

interface HeaderProps {
  apiStatus: ApiStatus;
}

export function Header({ apiStatus }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="header-inner">
        <div className="brand-group">
          <a className="brand" href="#main" aria-label="Support Resolution Assistant Home">
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 3L3 9v7c0 7.5 5.5 14.5 13 16 7.5-1.5 13-8.5 13-16V9L16 3z" />
                <path d="M11 15l3.5 3.5L21 11" />
              </svg>
            </span>
            <div className="brand-copy">
              <div className="brand-title-row">
                <strong>RESOLVE<span className="brand-highlight">AI</span></strong>
                <span className="brand-badge">ENTERPRISE</span>
              </div>
              <span className="brand-subtitle">AI-Assisted Support Operations Desk</span>
            </div>
          </a>
        </div>

        <div className="header-actions">
          <div className={`api-status api-status-${apiStatus}`} role="status" aria-live="polite">
            <span className="status-dot-wrapper" aria-hidden="true">
              <span className="status-dot" />
              {apiStatus === "available" && <span className="status-pulse" />}
            </span>
            <span className="status-text">
              {apiStatus === "checking"
                ? "Connecting..."
                : apiStatus === "available"
                ? "API Connected"
                : "Service Unavailable"}
            </span>
          </div>

          <div className="header-divider" aria-hidden="true" />

          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
