"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ChatCard,
  ChatMessage,
  ClientEvent,
  InboxNotification,
  LabReport,
  Slot,
  WSEvent,
} from "@/types/chat";

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_BASE_URL?.replace(/\/$/, "") ||
  "ws://localhost:8000";

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
  sendText: (content: string) => void;
  resolveSlot: (cardId: string, slotId: string, doctorId: string) => void;
  resolveLabDecision: (
    cardId: string,
    sessionId: string,
    decision: "accept" | "reject"
  ) => void;
  markInboxRead: (id: string) => void;
  unreadCount: number;
}

export function useChatSocket(userId: string | null): UseChatSocketResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [cards, setCards] = useState<ChatCard[]>([]);
  const [inbox, setInbox] = useState<InboxNotification[]>([]);
  const [reports, setReports] = useState<LabReport[]>([]);
  const [connected, setConnected] = useState(false);
  const [thinking, setThinking] = useState<string | null>(null);
  const [doctorName, setDoctorName] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const streamingIdRef = useRef<string | null>(null);
  const appointmentBookedRef = useRef(false);
  const doctorNameRef = useRef<string | null>(null);

  const pushMessage = useCallback(
    (role: ChatMessage["role"], content: string, from?: string) => {
      setMessages((prev) => [...prev, { id: newId(), role, content, from }]);
    },
    []
  );

  const pushInbox = useCallback(
    (notif: Omit<InboxNotification, "id" | "createdAt" | "read">) => {
      setInbox((prev) => [
        { ...notif, id: newId(), createdAt: Date.now(), read: false },
        ...prev,
      ]);
    },
    []
  );

  const handleEvent = useCallback(
    (evt: WSEvent) => {
      setThinking(null);

      switch (evt.type) {
        case "thinking": {
          setThinking((evt.payload.content as string) || "Ally is typing...");
          break;
        }

        case "text": {
          const content = (evt.payload.content as string) || "";
          const from = evt.payload.from as string | undefined;
          streamingIdRef.current = null;
          pushMessage("assistant", content, from);

          if (
            !appointmentBookedRef.current &&
            /confirmed|booked|see you|right with you|coming online/i.test(
              content
            )
          ) {
            appointmentBookedRef.current = true;
            pushInbox({
              kind: "appointment_booked",
              title: "Appointment booked",
              body: doctorNameRef.current
                ? `Your appointment with ${doctorNameRef.current} is confirmed.`
                : "Your appointment is confirmed.",
              decision: "pending",
            });
          }
          break;
        }

        case "text_delta": {
          const delta = (evt.payload.delta as string) || "";
          const from = evt.payload.from as string | undefined;
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
            return [...prev, { id, role: "assistant", content: delta, from }];
          });
          break;
        }

        case "slot_select": {
          const options = (evt.payload.options as Slot[]) || [];
          const docName = evt.payload.doctor_name as string | undefined;
          if (docName) {
            doctorNameRef.current = docName;
            setDoctorName(docName);
          }
          setCards((prev) => [
            ...prev,
            {
              id: newId(),
              kind: "slot_select",
              slots: options,
              doctorName: docName,
            },
          ]);
          break;
        }

        case "lab_notification": {
          const waiting = evt.payload.waiting as boolean | undefined;
          if (waiting) break;
          setCards((prev) => [
            ...prev,
            {
              id: newId(),
              kind: "lab_notification",
              tests:
                (evt.payload.tests as { name: string; reason: string }[]) ||
                [],
              sessionId: evt.payload.session_id as string,
            },
          ]);
          break;
        }

        case "report_ready": {
          const reportId = (evt.payload.inbox_id as string) || newId();
          const doctor =
            (evt.payload.doctor as string) ||
            doctorNameRef.current ||
            "your doctor";
          setReports((prev) => [
            {
              id: reportId,
              doctorName: doctor,
              tests: [],
              createdAt: Date.now(),
            },
            ...prev,
          ]);
          pushInbox({
            kind: "report_ready",
            title: "Lab report ready",
            body: `Your results from ${doctor} are ready to view.`,
            reportId,
          });
          break;
        }

        default:
          break;
      }
    },
    [pushMessage, pushInbox]
  );

  useEffect(() => {
    if (!userId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/${encodeURIComponent(userId)}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const evt = JSON.parse(event.data) as WSEvent;
        handleEvent(evt);
      } catch {
        // Ignore malformed frames.
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const sendRaw = useCallback((evt: ClientEvent) => {
    wsRef.current?.send(JSON.stringify(evt));
  }, []);

  const sendText = useCallback(
    (content: string) => {
      if (!content.trim()) return;
      pushMessage("user", content);
      sendRaw({ type: "text", payload: { content } });
    },
    [pushMessage, sendRaw]
  );

  const resolveSlot = useCallback(
    (cardId: string, slotId: string, doctorId: string) => {
      setCards((prev) =>
        prev.map((c) => (c.id === cardId ? { ...c, resolved: true } : c))
      );
      pushMessage("user", "Selected a time slot");
      sendRaw({
        type: "select",
        payload: { target: "slot", id: slotId, doctor_id: doctorId },
      });
    },
    [pushMessage, sendRaw]
  );

  const resolveLabDecision = useCallback(
    (cardId: string, sessionId: string, decision: "accept" | "reject") => {
      setCards((prev) =>
        prev.map((c) => (c.id === cardId ? { ...c, resolved: true } : c))
      );
      pushMessage("user", decision === "accept" ? "Accept tests" : "Not now");
      sendRaw({
        type: "select",
        payload: { decision, session_id: sessionId },
      });
    },
    [pushMessage, sendRaw]
  );

  const markInboxRead = useCallback((id: string) => {
    setInbox((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const unreadCount = inbox.filter((n) => !n.read).length;

  return {
    messages,
    cards,
    inbox,
    reports,
    connected,
    thinking,
    doctorName,
    sendText,
    resolveSlot,
    resolveLabDecision,
    markInboxRead,
    unreadCount,
  };
}