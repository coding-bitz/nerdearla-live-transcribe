export interface ChapterData {
  title: string;
  timestamp: number;
}

export interface ExecutiveSummaryData {
  title: string;
  summary: string;
  keyTakeaways: string[];
  resources: string[];
  technicalLevel: "beginner" | "intermediate" | "advanced";
  topics: string[];
  hashtags: string[];
  estimatedReadingTime: string;
  chapters: Array<{ title: string; summary: string }>;
}

export interface AccessibilityData {
  enhancedText: string;
  soundDescriptions: string[];
  speakerTone: string;
}

export interface ErrorPayload {
  type: "error";
  code: string;
  message: string;
  retryable?: boolean;
}

export interface SessionData {
  session_id: string;
  created_at: number;
  status: string;
  source_language: string;
  translation_enabled: boolean;
  target_language: string;
  final_transcripts: Array<{ text: string; timestamp: number }>;
  chapters: ChapterData[];
  summary?: ExecutiveSummaryData | null;
  chunk_count: number;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";

export async function authenticatedFetch(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<Response> {
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
}

export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return res.json();
}

export async function fetchReady(): Promise<{
  status: string;
  models: Record<string, string>;
  redis_connected: boolean;
  environment: string;
}> {
  const res = await fetch(`${API_BASE}/ready`);
  if (!res.ok) throw new Error(`Readiness check failed: HTTP ${res.status}`);
  return res.json();
}

export async function fetchSession(sessionId: string, token?: string | null): Promise<SessionData> {
  const res = await authenticatedFetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {}, token);
  if (!res.ok) throw new Error(`Failed fetching session: HTTP ${res.status}`);
  return res.json();
}

export async function requestSummary(sessionId: string, token?: string | null): Promise<ExecutiveSummaryData> {
  const res = await authenticatedFetch(
    `/api/sessions/${encodeURIComponent(sessionId)}/summary`,
    { method: "POST" },
    token
  );
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(errData.detail || "Summary generation failed");
  }
  return res.json();
}

export async function requestAccessibility(
  sessionId: string,
  text: string,
  token?: string | null,
  audioFeatures?: Record<string, number>
): Promise<AccessibilityData> {
  const res = await authenticatedFetch(
    `/api/sessions/${encodeURIComponent(sessionId)}/accessibility`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, audio_features: audioFeatures }),
    },
    token
  );
  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(errData.detail || "Accessibility enhancement failed");
  }
  return res.json();
}
