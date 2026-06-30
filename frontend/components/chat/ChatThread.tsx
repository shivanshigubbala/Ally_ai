"use client";

import { useEffect, useRef } from "react";
import type { ChatCard, ChatMessage } from "@/types/chat";

interface ChatThreadProps {
  messages: ChatMessage[];
  cards: ChatCard[];
  thinking: string | null;
  onSelectDoctor: (cardId: string, doctorId: string) => void;
  onSelectSlot: (cardId: string, slotId: string, doctorId: string) => void;
  onLabDecision: (
    cardId: string,
    sessionId: string,
    decision: "accept" | "reject"
  ) => void;
}

function formatSlotTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      weekday: "short",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatMessageTime(timestamp?: number): string | null {
  if (!timestamp) return null;
  return new Date(timestamp).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function MessageAvatar({ label, accent = "blue" }: { label: string; accent?: "blue" | "emerald" }) {
  const palette =
    accent === "emerald"
      ? "bg-emerald-100 text-emerald-700"
      : "bg-sky-100 text-sky-700";

  return (
    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl ${palette} text-xs font-semibold shadow-sm`}>
      {label}
    </div>
  );
}

function DoctorCard({
  card,
  onSelectDoctor,
}: {
  card: ChatCard;
  onSelectDoctor: ChatThreadProps["onSelectDoctor"];
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 text-sm font-semibold">
          D
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">Choose a doctor</p>
          <p className="text-xs text-slate-500">Pick the clinician who should review your case.</p>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {(card.doctors || []).map((doctor) => {
          const available = doctor.available !== false;
          return (
            <button
              key={doctor.id}
              disabled={!available}
              onClick={() => onSelectDoctor(card.id, doctor.id)}
              className={`rounded-2xl border px-4 py-3 text-left text-sm transition ${
                available
                  ? "border-sky-200 bg-sky-50 text-slate-900 hover:-translate-y-0.5 hover:border-sky-300 hover:bg-white"
                  : "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
              }`}
            >
              <div className="font-medium">{doctor.name}</div>
              <div className="mt-0.5 text-xs text-slate-500">
                {doctor.department_id || "Cardiology"}
                {!available ? " - unavailable" : " - available"}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SlotCard({
  card,
  onSelectSlot,
}: {
  card: ChatCard;
  onSelectSlot: ChatThreadProps["onSelectSlot"];
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-700 text-sm font-semibold">
          C
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">
            Available appointment slots
          </p>
          <p className="text-xs text-slate-500">
            {card.doctorName ? `With ${card.doctorName}` : "Choose a time that works for you."}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(card.slots || []).map((slot) => (
          <button
            key={slot.id}
            disabled={card.resolved}
            onClick={() => onSelectSlot(card.id, slot.id, slot.doctor_id)}
            className={`rounded-full border px-3.5 py-2 text-xs font-medium transition ${
              card.resolved
                ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                : "border-sky-200 bg-sky-50 text-sky-700 hover:-translate-y-0.5 hover:border-sky-300 hover:bg-white"
            }`}
          >
            {formatSlotTime(slot.start_time)}
          </button>
        ))}
      </div>
    </div>
  );
}

function LabCard({
  card,
  onLabDecision,
}: {
  card: ChatCard;
  onLabDecision: ChatThreadProps["onLabDecision"];
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 text-sm font-semibold">
          L
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">
            Recommended lab tests
          </p>
          <p className="text-xs text-slate-500">
            Review the suggested tests before continuing.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {(card.tests || []).map((test, i) => (
          <div key={i} className="rounded-2xl bg-slate-50 px-4 py-3">
            <p className="text-sm font-medium text-slate-900">{test.name}</p>
            <p className="mt-0.5 text-xs leading-5 text-slate-500">{test.reason}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          disabled={card.resolved}
          onClick={() => onLabDecision(card.id, card.sessionId || "", "reject")}
          className={`rounded-2xl border px-4 py-2.5 text-sm font-medium transition ${
            card.resolved
              ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
              : "border-rose-200 bg-rose-50 text-rose-700 hover:-translate-y-0.5 hover:bg-white"
          }`}
        >
          No, not now
        </button>
        <button
          disabled={card.resolved}
          onClick={() => onLabDecision(card.id, card.sessionId || "", "accept")}
          className={`rounded-2xl px-4 py-2.5 text-sm font-medium transition ${
            card.resolved
              ? "cursor-not-allowed bg-slate-200 text-slate-400"
              : "bg-gradient-to-r from-sky-600 to-blue-600 text-white shadow-lg shadow-blue-200 hover:-translate-y-0.5"
          }`}
        >
          Yes, proceed
        </button>
      </div>
    </div>
  );
}

function Bubble({
  message,
  isUser,
}: {
  message: ChatMessage;
  isUser: boolean;
}) {
  const time = formatMessageTime(message.timestamp);

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <MessageAvatar
          label={message.from ? "Dr" : "AI"}
          accent={message.from ? "emerald" : "blue"}
        />
      )}

      <div className={`max-w-[min(100%,36rem)] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`rounded-3xl px-4 py-3 text-sm leading-6 shadow-sm ${
            isUser
              ? "bg-gradient-to-r from-sky-600 to-blue-600 text-white"
              : "border border-slate-200 bg-white text-slate-800"
          }`}
        >
          {message.content}
        </div>
        {time && (
          <span className={`mt-1 text-[11px] uppercase tracking-[0.12em] ${
            isUser ? "text-sky-200" : "text-slate-400"
          }`}>
            {time}
          </span>
        )}
      </div>

      {isUser && <MessageAvatar label="You" accent="blue" />}
    </div>
  );
}

export default function ChatThread({
  messages,
  cards,
  thinking,
  onSelectDoctor,
  onSelectSlot,
  onLabDecision,
}: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, cards, thinking]);

  const doctorCards = cards.filter((card) => card.kind === "doctor_select");
  const slotCards = cards.filter((card) => card.kind === "slot_select");
  const labCards = cards.filter((card) => card.kind === "lab_notification");

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-5">
      <div className="space-y-5">
        {messages.map((m) => (
          <Bubble key={m.id} message={m} isUser={m.role === "user"} />
        ))}

        {doctorCards.map((card) => (
          <DoctorCard key={card.id} card={card} onSelectDoctor={onSelectDoctor} />
        ))}

        {slotCards.map((card) => (
          <SlotCard key={card.id} card={card} onSelectSlot={onSelectSlot} />
        ))}

        {labCards.map((card) => (
          <LabCard key={card.id} card={card} onLabDecision={onLabDecision} />
        ))}

        {thinking && (
          <div className="flex items-start gap-3">
            <MessageAvatar label="AI" accent="blue" />
            <div className="rounded-3xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <div className="flex items-center gap-1.5 text-slate-400 text-sm">
                <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400" />
                <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400 [animation-delay:150ms]" />
                <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400 [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
