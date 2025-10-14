// frontend\src\types.ts
export interface ChatTopic {
  topic: string;
  last_at: string; // ISO string from backend
  count: number;
}

export interface ReportByTopic {
  id: number;
  topic: string;
  research: string;
  share_url?: string;
}

export type HistoryAction = "share" | "rename" | "archive" | "delete";

export interface HistoryActionPayload {
  kind: "report";
  id: number;
  action: HistoryAction;
  value?: string; // used for rename
}
