export interface SessionListItem {
  id: string;
  title: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageRead {
  id: string;
  role: string;
  content: string;
  message_type: string | null;
  metadata_: Record<string, unknown> | null;
  sequence_num: number;
  created_at: string;
}

export interface SessionRead {
  id: string;
  title: string | null;
  agent_config: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  messages: MessageRead[];
}

export interface ChatRequest {
  message: string;
}

export type SSEEventType = "thinking" | "execute" | "solution" | "error" | "done";

export interface SSEEvent {
  event: SSEEventType;
  data: Record<string, unknown>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  type: SSEEventType | "user";
}
