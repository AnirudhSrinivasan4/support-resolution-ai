import type { ResolutionRequest, ResolutionResponse } from "../types/resolution";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = 120_000;

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

function isResolutionResponse(value: unknown): value is ResolutionResponse {
  if (typeof value !== "object" || value === null) return false;
  const response = value as Partial<ResolutionResponse>;
  const understanding = response.complaint_understanding;
  const severities = ["low", "medium", "high", "critical", "unknown"];
  const sentiments = ["positive", "neutral", "frustrated", "angry", "negative", "unknown"];
  return (
    typeof response.resolution === "string" &&
    Array.isArray(response.steps) &&
    response.steps.every((step) => typeof step === "string") &&
    typeof response.escalation === "string" &&
    Array.isArray(response.citations) &&
    response.citations.every(
      (citation) =>
        typeof citation === "object" &&
        citation !== null &&
        (citation.source_type === "knowledge" || citation.source_type === "historical_ticket") &&
        typeof citation.source_id === "string" &&
        typeof citation.title === "string",
    ) &&
    typeof response.abstained === "boolean" &&
    typeof understanding === "object" &&
    understanding !== null &&
    typeof understanding.intent === "string" &&
    typeof understanding.category === "string" &&
    typeof understanding.product === "string" &&
    typeof understanding.severity === "string" &&
    severities.includes(understanding.severity) &&
    typeof understanding.sentiment === "string" &&
    sentiments.includes(understanding.sentiment)
  );
}

async function readError(response: Response): Promise<ApiError> {
  const messageByStatus: Record<number, string> = {
    400: "The complaint could not be processed. Check it and try again.",
    422: "Please enter a valid complaint and try again.",
    502: "The resolution service could not complete this request. Please retry.",
    503: "The resolution service is temporarily unavailable. Please retry shortly.",
  };
  return new ApiError(
    messageByStatus[response.status] ??
      (response.status >= 500
        ? "The service encountered a problem. Please try again."
        : "The request could not be completed. Please check it and try again."),
    response.status,
  );
}

export async function createResolution(complaint: string): Promise<ResolutionResponse> {
  const request: ResolutionRequest = { complaint };
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/v1/resolutions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError("The request took too long. Please retry.");
    }
    throw new ApiError("Could not reach the support resolution service. Check the connection and retry.");
  }

  if (!response.ok) throw await readError(response);

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError("The service returned an unreadable response. Please retry.");
  }
  if (!isResolutionResponse(payload)) {
    throw new ApiError("The service response was incomplete or invalid. Please retry.");
  }
  return payload;
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/healthz`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(5_000),
    });
    if (!response.ok) return false;
    const payload: unknown = await response.json();
    return (
      typeof payload === "object" &&
      payload !== null &&
      "status" in payload &&
      payload.status === "ok"
    );
  } catch {
    return false;
  }
}
