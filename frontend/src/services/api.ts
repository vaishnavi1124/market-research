// frontend/src/services/api.ts
import { ChatTopic, HistoryAction, HistoryActionPayload, ReportByTopic } from "../types";

const API_BASE = ""; // same origin; change if needed

export async function fetchChatHistory(): Promise<ChatTopic[]> {
  const res = await fetch(`${API_BASE}/api/chat-history`);
  if (!res.ok) throw new Error("Failed to load history");
  return res.json();
}

export async function fetchReportByTopic(topic: string): Promise<ReportByTopic | null> {
  const res = await fetch(`${API_BASE}/api/report-by-topic?topic=${encodeURIComponent(topic)}`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchChatThread(topic: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/chat-thread?topic=${encodeURIComponent(topic)}`);
  if (!res.ok) return [];
  return res.json();
}

export async function historyAction(id: number, action: HistoryAction, value?: string) {
  const payload: HistoryActionPayload = { kind: "report", id, action, ...(value ? { value } : {}) };
  const res = await fetch(`${API_BASE}/api/history/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Failed to ${action}`);
  return data;
}
