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
  | "report_ready"
  | "doctor_ready"
  | "upload_received"
  | "upload_indexed"
  | "emergency_alert"
  | "consultation_chart";

export interface WSEvent {
  type: WSEventType;
  payload: Record<string, unknown>;
}

export type ClientEventType = "text" | "select" | "start_consultation";

export interface ClientEvent {
  type: ClientEventType;
  payload: Record<string, unknown>;
}

export type MessageContext = "receptionist" | "doctor";

export interface DoctorReadyInfo {
  appointmentId: string;
  doctorName: string;
  doctorId: string;
  department?: string;
  consultationStatus?: string;
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
  timestamp?: number;
}

export type CardKind = "slot_select" | "doctor_select" | "lab_notification";

export interface ChatCard {
  id: string;
  kind: CardKind;
  slots?: Slot[];
  doctors?: Array<{ id: string; name: string; department_id: string; available?: boolean }>;
  doctorName?: string;
  tests?: LabTest[];
  sessionId?: string;
  resolved?: boolean;
  recommendedDepartment?: string;
  departmentConfidence?: number;
  intakeSummary?: string;
}

export type InboxKind = "appointment_booked" | "lab_notification" | "report_ready" | "lab_suggested" | "upload_received" | "upload_indexed";

export interface InboxNotification {
  id: string;
  kind: InboxKind;
  title: string;
  body: string;
  createdAt: number;
  read: boolean;
  appointmentId?: string;
  decision?: "pending" | "accepted" | "rejected";
  reportId?: string;
  cardId?: string;
  sessionId?: string;
  tests?: LabTest[];
  urgent?: boolean;
}

export interface LabReport {
  id: string;
  doctorName: string;
  tests: LabTest[];
  createdAt: number;
  url?: string;
}
