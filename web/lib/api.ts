import type { Evidence, EvidenceGraph, Investigation, ObjectMatch, Timeline, User } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const TOKEN_KEY = "echotrace_access_token";

export function getToken() {
  return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: (body: { name: string; email: string; password: string }) =>
    request<{ user: User; access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: { email: string; password: string }) =>
    request<{ user: User; access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  me: () => request<User>("/auth/me"),
  investigations: () => request<Investigation[]>("/investigations"),
  investigation: (id: string) => request<Investigation>(`/investigations/${id}`),
  createInvestigation: (body: Record<string, string>) =>
    request<Investigation>("/investigations", { method: "POST", body: JSON.stringify(body) }),
  upload: (id: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<Evidence>(`/investigations/${id}/evidence`, { method: "POST", body });
  },
  process: (id: string) => request(`/investigations/${id}/process`, { method: "POST" }),
  status: (id: string) => request<{ status: string; evidence: Array<{ evidence_id: string; processing_status: string }> }>(`/investigations/${id}/status`),
  synchronize: (id: string, reference_evidence_id?: string) =>
    request(`/investigations/${id}/synchronize`, {
      method: "POST",
      body: JSON.stringify({ reference_evidence_id, max_offset_seconds: 60 }),
    }),
  timeline: (id: string) => request<Timeline>(`/investigations/${id}/timeline`),
  objects: (id: string) => request<Array<Record<string, unknown>>>(`/investigations/${id}/objects`),
  matches: (id: string) => request<ObjectMatch[]>(`/investigations/${id}/objects/matches`),
  reviewMatch: (id: string, matchId: string, decision: "confirmed" | "rejected") =>
    request(`/investigations/${id}/objects/matches/${matchId}`, {
      method: "PATCH",
      body: JSON.stringify({ decision }),
    }),
  correctEvent: (id: string, eventId: string, body: Record<string, unknown>) =>
    request(`/investigations/${id}/timeline/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  correctObject: (id: string, evidenceId: string, trackId: number, canonical_identity: string, note: string) =>
    request(`/investigations/${id}/objects/tracks/${evidenceId}/${trackId}`, {
      method: "PATCH",
      body: JSON.stringify({ canonical_identity, note }),
    }),
  adjustSync: (id: string, evidenceId: string, offset_seconds: number, note: string) =>
    request(`/investigations/${id}/evidence/${evidenceId}/synchronization`, {
      method: "PATCH",
      body: JSON.stringify({ offset_seconds, note }),
    }),
  summary: (id: string) =>
    request<{ summary: string; confidence: number; citations: unknown[]; warning: string }>(
      `/investigations/${id}/summary`,
    ),
  ask: (id: string, question: string) =>
    request<{ answer: string; confidence: number; citations: unknown[]; warning: string }>(
      `/investigations/${id}/ask`,
      { method: "POST", body: JSON.stringify({ question }) },
    ),
  graph: (id: string) => request<EvidenceGraph>(`/investigations/${id}/graph`),
  blob: async (path: string) => {
    const token = getToken();
    const response = await fetch(`${API_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error("Unable to load protected evidence");
    return URL.createObjectURL(await response.blob());
  },
};
