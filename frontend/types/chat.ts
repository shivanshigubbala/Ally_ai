// Mirrors backend/models/session_state.py (IC-13 envelope).
// Keep these in sync with the backend — they are the source of truth.

export type WSEventType =
  | "text"
  | "text_delta"
  | "thinking"
  | "dept_select"
  | "doctor_select"
  | "slot_select"
  | "lab_notification"
  | "report_ready";

export interface WSEvent {
  type: WSEventType;
  payload: Record<string, unknown>;
}

export type ClientEventType = "text" | "select";

export interface ClientEvent {
  type: ClientEventType;
  payload: Record<string, unknown>;
}

export interface Slot {
  id: string;
  doctor_id: string;
  start_time: string;
}

export interface LabTest {
  name: string;
  reason: string;
}

// ---- Derived UI-side models ---------------------------------------------

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  from?: string;
}

export type CardKind = "slot_select" | "lab_notification";

export interface ChatCard {
  id: string;
  kind: CardKind;
  slots?: Slot[];
  doctorName?: string;
  tests?: LabTest[];
  sessionId?: string;
  resolved?: boolean;
}

export type InboxKind = "appointment_booked" | "report_ready";

export interface InboxNotification {
  id: string;
  kind: InboxKind;
  title: string;
  body: string;
  createdAt: number;
  read: boolean;
  decision?: "pending" | "accepted" | "rejected";
  reportId?: string;
}

export interface LabReport {
  id: string;
  doctorName: string;
  tests: LabTest[];
  createdAt: number;
}