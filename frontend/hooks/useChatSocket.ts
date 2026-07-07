"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ChatCard,
  ChatMessage,
  ClientEvent,
  DoctorReadyInfo,
  InboxNotification,
  LabReport,
  Slot,
  WSEvent,
} from "@/types/chat";

import { getBackendBase, getWsBase } from "@/lib/backend";

const WS_BASE = getWsBase();
const HTTP_BASE = getBackendBase();
const CHAT_STATE_KEY_PREFIX = "ally_chat_state";

function newId(): string {
  return Math.random().toString(36).slice(2, 10);
}

interface UseChatSocketResult {
  messages: ChatMessage[];
  cards: ChatCard[];
  inbox: InboxNotification[];
  reports: LabReport[];
  connected: boolean;
  thinking: string | null;
  doctorName: string | null;
  appointmentPending: boolean;
  appointmentBooked: boolean;
  doctorReady: DoctorReadyInfo | null;
  doctorMessages: ChatMessage[];
  doctorThinking: string | null;
  consultationActive: boolean;
  sendText: (content: string, context?: "receptionist") => void;
  selectDoctor: (cardId: string, doctorId: string) => void;
  resolveSlot: (cardId: string, slotId: string, doctorId: string) => void;
  resolveLabDecision: (
    cardId: string,
    sessionId: string,
    decision: "accept" | "reject"
  ) => void;
  markInboxRead: (id: string) => void;
  startConsultation: () => void;
  sendDoctorMessage: (content: string) => void;
  unreadCount: number;
  addSampleReport: () => void;
  consultationChart: string | null;
}

export function useChatSocket(userId: string | null, patientId?: string | null): UseChatSocketResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [cards, setCards] = useState<ChatCard[]>([]);
  const [inbox, setInbox] = useState<InboxNotification[]>([]);
  const [reports, setReports] = useState<LabReport[]>([]);
  const [connected, setConnected] = useState(false);
  const [thinking, setThinking] = useState<string | null>(null);
  const [doctorName, setDoctorName] = useState<string | null>(null);
  const [appointmentPending, setAppointmentPending] = useState(false);
  const [appointmentBooked, setAppointmentBooked] = useState(false);
  const [doctorReady, setDoctorReady] = useState<DoctorReadyInfo | null>(null);
  const [doctorMessages, setDoctorMessages] = useState<ChatMessage[]>([]);
  const [doctorThinking, setDoctorThinking] = useState<string | null>(null);
  const [consultationActive, setConsultationActive] = useState(false);
  const [consultationChart, setConsultationChart] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const pendingEventsRef = useRef<ClientEvent[]>([]);
  const streamingIdRef = useRef<string | null>(null);
  const doctorStreamingIdRef = useRef<string | null>(null);
  const appointmentBookedRef = useRef(false);
  const doctorNameRef = useRef<string | null>(null);
  const consultationActiveRef = useRef(false);
  const isLoadedRef = useRef(false);

  useEffect(() => {
    isLoadedRef.current = false;
  }, [patientId]);

  useEffect(() => {
    consultationActiveRef.current = consultationActive;
  }, [consultationActive]);

  const pushInbox = useCallback(
    (notif: Omit<InboxNotification, "id" | "createdAt" | "read">) => {
      setInbox((prev) => {
        if (
          notif.kind === "appointment_booked" &&
          prev.some(
            (n) =>
              n.kind === "appointment_booked" &&
              (notif.appointmentId ? n.appointmentId === notif.appointmentId : true)
          )
        ) {
          return prev;
        }
        return [
          { ...notif, id: newId(), createdAt: Date.now(), read: false },
          ...prev,
        ];
      });
    },
    []
  );

  // Load persisted notifications from backend on mount
  useEffect(() => {
    if (!patientId || typeof window === "undefined") return;
    const backendBase = HTTP_BASE;
    if (!backendBase) return;
    fetch(`${backendBase}/notifications/${encodeURIComponent(patientId)}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data?.notifications?.length) return;
        setInbox((prev) => {
          const existingIds = new Set(prev.map((n) => n.id));
          const loaded: InboxNotification[] = (data.notifications as any[]).map((n: any) => {
            let rUrl = n.metadata?.report_url || n.metadata?.download_url || "";
            if (rUrl) {
              rUrl = rUrl
                .replace("://backend:8000", "://localhost:8000")
                .replace("://lab:8082", "://localhost:8082");
              if (rUrl.startsWith("/")) {
                rUrl = `${HTTP_BASE}${rUrl}`;
              }
            }
            return {
              id: n.notification_id || n.id || Math.random().toString(36).slice(2),
              kind: (n.notification_type || "lab_notification").toLowerCase() as InboxNotification["kind"],
              title: n.title || "Notification",
              body: n.message || "",
              createdAt: n.created_at ? new Date(n.created_at).getTime() : Date.now(),
              read: n.status === "READ",
              decision: (n.status === "READ" ? "accepted" : "pending") as InboxNotification["decision"],
              reportUrl: rUrl,
            };
          });
          const fresh = loaded.filter((n) => !existingIds.has(n.id));
          return [...prev, ...fresh].sort((a, b) => b.createdAt - a.createdAt);
        });
      })
      .catch(() => { /* silently ignore if backend unreachable */ });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  const handleEvent = useCallback(
    (evt: WSEvent) => {
      setThinking(null);
      setDoctorThinking(null);

      switch (evt.type) {
        case "upload_received": {
          const filename = (evt.payload.filename as string) || "file";
          pushInbox({
            kind: "upload_received",
            title: "File uploaded",
            body: `Received ${filename}. Processing for the doctor.`,
            decision: "pending",
          });
          break;
        }

        case "upload_indexed": {
          const filename = (evt.payload.filename as string) || "file";
          pushInbox({
            kind: "upload_indexed",
            title: "File ready",
            body: `${filename} is indexed and ready for the doctor.`,
            decision: "accepted",
          });
          break;
        }

        case "thinking": {
          const content = (evt.payload.content as string) || "";
          if (/doctor|dr\.?\s+/i.test(content) || consultationActiveRef.current) {
            setDoctorThinking(content);
          } else {
            setThinking(content);
          }
          break;
        }

        case "text": {
          const content = (evt.payload.content as string) || "";
          const from = evt.payload.from as string | undefined;
          streamingIdRef.current = null;
          doctorStreamingIdRef.current = null;

          if (from) {
            setDoctorMessages((prev) => [
              ...prev,
              { id: newId(), role: "assistant", content, from, timestamp: Date.now() },
            ]);
          } else {
            setMessages((prev) => [
              ...prev,
              { id: newId(), role: "assistant", content, from, timestamp: Date.now() },
            ]);
          }

          const isBookingConfirmation = /appointment|confirmed|booked|ready|appointments tab/i.test(
            content
          );

          if (!appointmentBookedRef.current && !from && isBookingConfirmation) {
            appointmentBookedRef.current = true;
            setAppointmentBooked(true);
            setAppointmentPending(false);
            setCards((prev) =>
              prev.map((c) =>
                c.kind === "doctor_select" || c.kind === "slot_select"
                  ? { ...c, resolved: true }
                  : c
              )
            );
          }
          break;
        }

        case "text_delta": {
          const delta = (evt.payload.delta as string) || "";
          const from = evt.payload.from as string | undefined;
          if (from) {
            setDoctorMessages((prev) => {
              if (
                doctorStreamingIdRef.current &&
                prev.length > 0 &&
                prev[prev.length - 1].id === doctorStreamingIdRef.current
              ) {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: updated[updated.length - 1].content + delta,
                };
                return updated;
              }
              const id = newId();
              doctorStreamingIdRef.current = id;
              return [
                ...prev,
                { id, role: "assistant", content: delta, from, timestamp: Date.now() },
              ];
            });
          } else {
            setMessages((prev) => {
              if (
                streamingIdRef.current &&
                prev.length > 0 &&
                prev[prev.length - 1].id === streamingIdRef.current
              ) {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: updated[updated.length - 1].content + delta,
                };
                return updated;
              }
              const id = newId();
              streamingIdRef.current = id;
              return [
                ...prev,
                { id, role: "assistant", content: delta, timestamp: Date.now() },
              ];
            });
          }
          break;
        }

        case "doctor_select": {
          const options = (evt.payload.options as Array<{id:string;name:string;department_id:string}>) || [];
          const recommendedDepartment = (evt.payload.recommended_department as string | undefined) || undefined;
          const departmentConfidence = (evt.payload.department_confidence as number | undefined) || undefined;
          const intakeSummary = (evt.payload.intake_summary as string | undefined) || undefined;
          setCards((prev) => {
            const existing = prev.find((c) => c.kind === "doctor_select" && !c.resolved);
            if (existing) {
              return prev.map((c) =>
                c.id === existing.id
                  ? { ...c, doctors: options }
                  : c
              );
            }
            return [
              ...prev,
              {
                id: newId(),
                kind: "doctor_select",
                doctors: options,
                recommendedDepartment,
                departmentConfidence,
                intakeSummary,
              },
            ];
          });
          break;
        }

        case "slot_select": {
          const options = (evt.payload.options as Slot[]) || [];
          const docName = evt.payload.doctor_name as string | undefined;
          const recommendedDepartment = (evt.payload.recommended_department as string | undefined) || undefined;
          const departmentConfidence = (evt.payload.department_confidence as number | undefined) || undefined;
          const intakeSummary = (evt.payload.intake_summary as string | undefined) || undefined;
          if (docName) {
            doctorNameRef.current = docName;
            setDoctorName(docName);
          }
          setAppointmentPending(true);
          setAppointmentBooked(false);
          setCards((prev) => {
            const existing = prev.find((c) => c.kind === "slot_select" && !c.resolved);
            if (existing) {
              return prev.map((c) =>
                c.id === existing.id
                  ? { ...c, slots: options, doctorName: docName }
                  : c
              );
            }
            return [
              ...prev,
              {
                id: newId(),
                kind: "slot_select",
                slots: options,
                doctorName: docName,
                recommendedDepartment,
                departmentConfidence,
                intakeSummary,
              },
            ];
          });
          break;
        }

        case "doctor_ready": {
          const appointmentId = evt.payload.appointment_id as string;
          const docName = (evt.payload.doctor_name as string) || doctorNameRef.current || "Dr. Shankar";
          const doctorId = (evt.payload.doctor_id as string) || "";
          const department = (evt.payload.department as string) || undefined;
          const consultationStatus = (evt.payload.consultation_status as string) || "CREATED";
          setDoctorReady({ appointmentId, doctorName: docName, doctorId, department, consultationStatus });
          setDoctorName(docName);
          setAppointmentBooked(true);
          setAppointmentPending(false);
          setCards((prev) =>
            prev.map((c) =>
              c.kind === "doctor_select" || c.kind === "slot_select"
                ? { ...c, resolved: true }
                : c
            )
          );

          setDoctorMessages((prev) => [
            ...prev,
            {
              id: newId(),
              role: "assistant",
              from: docName,
              content: `Your appointment with ${docName} is confirmed. I’m ready to see you in the Appointments tab.`,
              timestamp: Date.now(),
            },
          ]);

          appointmentBookedRef.current = true;
          pushInbox({
            kind: "appointment_booked",
            title: "Appointment confirmed",
            body: `Your appointment with ${docName} is confirmed and ready in Notifications.`,
            appointmentId,
            decision: "pending",
          });
          break;
        }

        case "lab_notification": {
          const waiting = evt.payload.waiting as boolean | undefined;
          if (waiting) break;

          const tests = (evt.payload.tests as { name: string; reason: string }[]) || [];
          const cardId = newId();
          const sessionId = evt.payload.session_id as string;
          const urgent = Boolean(evt.payload.urgent);
          const docName = (evt.payload.doctor_name as string) || doctorNameRef.current || "your doctor";
          const deptName = (evt.payload.department as string) || "your doctor";
          const formattedTests = tests.map((test) => `• ${test.name}: ${test.reason}`).join("\n");

          setDoctorMessages((prev) => [
            ...prev,
            {
              id: newId(),
              role: "assistant",
              from: docName,
              content: `I have recommended the following lab tests:\n${formattedTests}\n\nPlease review and accept or decline them in the Notifications tab.`,
              timestamp: Date.now(),
            },
          ]);

          setCards((prev) => [
            ...prev,
            {
              id: cardId,
              kind: "lab_notification",
              tests,
              sessionId,
              doctorName: docName,
            },
          ]);

          const title = urgent
            ? `Urgent tests requested by ${docName}`
            : `Tests requested by ${docName}`;
          const body = urgent
            ? `${docName} marked this as urgent. Please review and accept or decline the tests.`
            : `${docName} recommended tests. Please review and accept or decline.`;

          pushInbox({
            kind: "lab_notification",
            title,
            body,
            decision: "pending",
            cardId,
            sessionId,
            tests,
            urgent,
          });
          break;
        }

        case "emergency_alert": {
          const content = (evt.payload.content as string) || "";
          pushInbox({
            kind: "lab_notification",
            title: "Urgent cardiology alert",
            body: content || "The cardiology doctor marked this conversation as urgent.",
            decision: "pending",
            urgent: true,
          });
          break;
        }

        case "report_ready": {
          const reportId = (evt.payload.report_id as string) || (evt.payload.inbox_id as string) || newId();
          const doctor =
            (evt.payload.doctor as string) ||
            doctorNameRef.current ||
            "your doctor";
          const tests = (evt.payload.tests as { name: string; reason: string }[]) || [];

          // Accept either explicit URLs or the older /reports/download?id= style.
          let reportUrl = (evt.payload.report_url as string) || (evt.payload.download_url as string) || "";
          if (!reportUrl) {
            // fallback: prefer path-style, but also accept numeric/opaque ids
            reportUrl = `${HTTP_BASE}/reports/${encodeURIComponent(reportId)}`;
          }
          if (reportUrl) {
            reportUrl = reportUrl
              .replace("://backend:8000", "://localhost:8000")
              .replace("://lab:8082", "://localhost:8082");
          }
          const normalizedReportUrl = reportUrl.startsWith("/") ? `${HTTP_BASE}${reportUrl}` : reportUrl;

          const aptId = (evt.payload.appointment_id as string) || (evt.payload.session_id as string) || "";
          setReports((prev) => {
            const filtered = prev.filter(
              (r) =>
                r.id !== `pending-${aptId}` &&
                r.id !== `pending-${reportId}` &&
                r.id !== `pending-${sessionId}` &&
                !r.id.endsWith(`-${aptId}`) &&
                r.id !== reportId
            );
            return [
              {
                id: reportId,
                doctorName: doctor,
                tests,
                createdAt: Date.now(),
                url: normalizedReportUrl,
              },
              ...filtered,
            ];
          });
          pushInbox({
            kind: "report_ready",
            title: "Lab report ready",
            body: `Your results from ${doctor} are ready to view.`,
            reportId,
            reportUrl: normalizedReportUrl,
          });
          break;
        }

        case "consultation_chart": {
          const content = (evt.payload.chart_content as string) || "";
          setConsultationChart(content);
          break;
        }

        default:
          break;
      }
    },
    [pushInbox]
  );

  useEffect(() => {
    if (!userId || typeof window === "undefined") return;
    try {
      const key = patientId ? `${CHAT_STATE_KEY_PREFIX}:${userId}:${patientId}` : `${CHAT_STATE_KEY_PREFIX}:${userId}`;
      const raw = window.localStorage.getItem(key);
      if (!raw) {
        setAppointmentBooked(false);
        appointmentBookedRef.current = false;
        setDoctorReady(null);
        setConsultationActive(false);
        consultationActiveRef.current = false;
        setConsultationChart("");
        setReports([]);
        setInbox([]);
        isLoadedRef.current = true;
        return;
      }
      const saved = JSON.parse(raw) as Partial<{
        appointmentBooked: boolean;
        doctorReady: DoctorReadyInfo | null;
        consultationActive: boolean;
        consultationChart: string | null;
        reports: any[];
        inbox: any[];
      }>;
      if (saved.appointmentBooked) {
        setAppointmentBooked(true);
        appointmentBookedRef.current = true;
      } else {
        setAppointmentBooked(false);
        appointmentBookedRef.current = false;
      }
      setDoctorReady(saved.doctorReady || null);
      if (typeof saved.consultationActive === "boolean") {
        setConsultationActive(saved.consultationActive);
        consultationActiveRef.current = saved.consultationActive;
      } else {
        setConsultationActive(false);
        consultationActiveRef.current = false;
      }
      setConsultationChart(saved.consultationChart || "");
      setReports(Array.isArray(saved.reports) ? saved.reports.filter((r: any) => r.status !== "generating") : []);
      setInbox(Array.isArray(saved.inbox) ? saved.inbox : []);
      isLoadedRef.current = true;
    } catch {
      // ignore malformed persisted state
    }
  }, [userId, patientId]);

  useEffect(() => {
    if (!userId || typeof window === "undefined" || !isLoadedRef.current) return;
    try {
      const key = patientId ? `${CHAT_STATE_KEY_PREFIX}:${userId}:${patientId}` : `${CHAT_STATE_KEY_PREFIX}:${userId}`;
      window.localStorage.setItem(
        key,
        JSON.stringify({
          appointmentBooked,
          doctorReady,
          consultationActive,
          consultationChart,
          reports: reports.filter((r) => r.status !== "generating"),
          inbox,
        })
      );
    } catch {
      // ignore storage failures
    }
  }, [appointmentBooked, consultationActive, consultationChart, doctorReady, userId, patientId, reports, inbox]);

  const connectWebSocket = useCallback(() => {
    if (!userId) return;
    const existing = wsRef.current;
    if (
      existing &&
      (existing.readyState === WebSocket.CONNECTING || existing.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    const params = new URLSearchParams();
    if (patientId) {
      params.set("patient_id", patientId);
    }
    const qs = params.toString();
    const ws = new WebSocket(
      `${WS_BASE}/ws/${encodeURIComponent(userId)}${qs ? `?${qs}` : ""}`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      if (pendingEventsRef.current.length > 0) {
        pendingEventsRef.current.forEach((pendingEvt) => {
          try {
            ws.send(JSON.stringify(pendingEvt));
          } catch {
            // ignore send failures here
          }
        });
        pendingEventsRef.current = [];
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
    };

    ws.onerror = () => {
      setConnected(false);
    };

    ws.onmessage = (event) => {
      try {
        const evt = JSON.parse(event.data) as WSEvent;
        handleEvent(evt);
      } catch {
        // Ignore malformed frames
      }
    };
  }, [handleEvent, patientId, userId]);

  useEffect(() => {
    if (!userId) return;

    setConsultationChart(null);
    connectWebSocket();

    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connectWebSocket, userId]);

  const sendRaw = useCallback(
    (evt: ClientEvent) => {
      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(evt));
        return;
      }

      if (ws?.readyState === WebSocket.CONNECTING) {
        pendingEventsRef.current.push(evt);
        return;
      }

      if (userId) {
        pendingEventsRef.current.push(evt);
        connectWebSocket();
      }
    },
    [connectWebSocket, userId]
  );

  const sendText = useCallback(
    (content: string, context: "receptionist" = "receptionist") => {
      if (!content.trim()) return;
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "user", content, timestamp: Date.now() },
      ]);
      sendRaw({
        type: "text",
        payload: context === "receptionist" ? { content } : { content, context },
      });
    },
    [sendRaw]
  );

  const sendDoctorMessage = useCallback(
    (content: string) => {
      if (!content.trim()) return;
      setDoctorMessages((prev) => [
        ...prev,
        { id: newId(), role: "user", content, timestamp: Date.now() },
      ]);
      sendRaw({
        type: "text",
        payload: { content, context: "doctor" },
      });
    },
    [sendRaw]
  );

  const resolveSlot = useCallback(
    (cardId: string, slotId: string, doctorId: string) => {
      setCards((prev) =>
        prev.map((c) => (c.id === cardId ? { ...c, resolved: true } : c))
      );
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "user", content: "Selected a time slot", timestamp: Date.now() },
      ]);
      sendRaw({
        type: "select",
        payload: { target: "slot", id: slotId, doctor_id: doctorId },
      });
    },
    [sendRaw]
  );

  const selectDoctor = useCallback(
    (cardId: string, doctorId: string) => {
      setConsultationActive(false);
      setDoctorReady(null);
      setAppointmentBooked(false);
      setConsultationChart("");
      setDoctorMessages([]);
      setCards((prev) =>
        prev.map((c) => (c.id === cardId ? { ...c, resolved: true } : c))
      );
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "user", content: "Selected a doctor", timestamp: Date.now() },
      ]);
      sendRaw({
        type: "select",
        payload: { id: doctorId, doctor_id: doctorId, context: "receptionist" },
      });
    },
    [sendRaw]
  );

  const startConsultation = useCallback(() => {
    if (!doctorReady) {
      return;
    }

    setConsultationActive(true);
    setDoctorReady(null);
    setDoctorMessages([]);
    setDoctorThinking(null);
    sendRaw({
      type: "start_consultation",
      payload: { appointment_id: doctorReady.appointmentId },
    });
  }, [doctorReady, sendRaw]);

  const resolveLabDecision = useCallback(
    (cardId: string, sessionId: string, decision: "accept" | "reject") => {
      setCards((prev) =>
        prev.map((c) => (c.id === cardId ? { ...c, resolved: true } : c))
      );
      setInbox((prev) =>
        prev.map((n) =>
          n.cardId === cardId || (sessionId && n.sessionId === sessionId)
            ? {
                ...n,
                read: true,
                decision: decision === "accept" ? "accepted" : "rejected",
              }
            : n
        )
      );

      if (decision === "accept") {
        setReports((prev) => {
          // Prevent duplicates
          if (prev.some((r) => r.id === `pending-${sessionId}`)) return prev;
          return [
            {
              id: `pending-${sessionId}`,
              doctorName: "your doctor",
              tests: [],
              createdAt: Date.now(),
              url: "",
              status: "generating",
            },
            ...prev,
          ];
        });
      }

      setDoctorMessages((prev) => [
        ...prev,
        {
          id: newId(),
          role: "user",
          content: decision === "accept" ? "Accept tests" : "Not now",
          timestamp: Date.now(),
        },
      ]);
      sendRaw({
        type: "select",
        payload: { context: "doctor", decision, session_id: sessionId },
      });
    },
    [sendRaw]
  );

  const markInboxRead = useCallback(
    (id: string) => {
      setInbox((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
      // Persist mark-read to backend (non-critical)
      if (HTTP_BASE) {
        fetch(`${HTTP_BASE}/notifications/${encodeURIComponent(id)}/read`, {
          method: "POST",
        }).catch(() => {});
      }
    },
    []
  );

  const addSampleReport = useCallback(() => {
    const id = `sample-${Math.random().toString(36).slice(2, 8)}`;
    const doc = doctorNameRef.current || "Dr. Shankar";
    const sample = {
      id,
      doctorName: doc,
      tests: [
        { name: "Complete Blood Count (CBC)", reason: "Routine check" },
      ],
      createdAt: Date.now(),
      url: `${HTTP_BASE}/reports/${encodeURIComponent(id)}`,
    };
    setReports((prev) => [sample, ...prev]);
    pushInbox({
      kind: "report_ready",
      title: "Lab report ready",
      body: `Your results from ${doc} are ready to view.`,
      reportId: id,
    });
  }, [pushInbox]);

  const unreadCount = inbox.filter((n) => !n.read).length;

  return {
    messages,
    cards,
    inbox,
    reports,
    connected,
    thinking,
    doctorName,
    appointmentPending,
    appointmentBooked,
    doctorReady,
    doctorMessages,
    doctorThinking,
    consultationActive,
    sendText,
    selectDoctor,
    resolveSlot,
    resolveLabDecision,
    markInboxRead,
    startConsultation,
    sendDoctorMessage,
    unreadCount,
    addSampleReport,
    consultationChart,
  };
}
