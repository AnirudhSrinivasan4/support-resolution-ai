export type Severity = "low" | "medium" | "high" | "critical" | "unknown";
export type Sentiment =
  | "positive"
  | "neutral"
  | "frustrated"
  | "angry"
  | "negative"
  | "unknown";

export interface ComplaintUnderstanding {
  intent: string;
  category: string;
  product: string;
  severity: Severity;
  sentiment: Sentiment;
}

export interface ResolutionCitation {
  source_type: "knowledge" | "historical_ticket";
  source_id: string;
  title: string;
}

export interface ResolutionResponse {
  complaint_understanding: ComplaintUnderstanding;
  resolution: string;
  steps: string[];
  escalation: string;
  citations: ResolutionCitation[];
  abstained: boolean;
}

export interface ResolutionRequest {
  complaint: string;
}
