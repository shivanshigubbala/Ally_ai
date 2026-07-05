"use client";

import { useEffect, useRef } from "react";
import type { ChatCard, ChatMessage } from "@/types/chat";
import MedicalTeamIllustration from "@/components/illustration/MedicalTeamIllustration";

interface ChatThreadProps {
  messages: ChatMessage[];
  doctorMessages: ChatMessage[];
  cards: ChatCard[];
  thinking: string | null;
  doctorThinking: string | null;
  connected: boolean;
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

      {card.intakeSummary && (
        <div className="mb-4 rounded-2xl border border-sky-100 bg-sky-50/70 p-3 text-xs text-slate-600">
          <p className="font-semibold text-slate-700">Intake summary</p>
          <p className="mt-1 whitespace-pre-line">{card.intakeSummary}</p>
        </div>
      )}

      <div className="mb-3 flex items-center justify-between text-xs text-slate-500">
        <span>Suggested department</span>
        <span className="rounded-full bg-emerald-100 px-2.5 py-1 font-semibold text-emerald-700">
          {card.recommendedDepartment ? card.recommendedDepartment : "General Physician"}
        </span>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {(card.doctors || []).map((doctor) => {
          const available = doctor.available !== false;
          const recommended = card.recommendedDepartment && doctor.department_id === card.recommendedDepartment;
          return (
            <button
              key={doctor.id}
              disabled={!available}
              onClick={() => onSelectDoctor(card.id, doctor.id)}
              className={`rounded-2xl border px-4 py-3 text-left text-sm transition ${
                available
                  ? recommended
                    ? "border-emerald-300 bg-emerald-50 text-slate-900 shadow-sm"
                    : "border-sky-200 bg-sky-50 text-slate-900 hover:-translate-y-0.5 hover:border-sky-300 hover:bg-white"
                  : "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium">{doctor.name}</div>
                {recommended && <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-700">Suggested</span>}
              </div>
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
  connected,
  onLabDecision,
}: {
  card: ChatCard;
  connected: boolean;
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
          disabled={card.resolved || !connected}
          onClick={() => onLabDecision(card.id, card.sessionId || "", "reject")}
          className={`rounded-2xl border px-4 py-2.5 text-sm font-medium transition ${
            card.resolved || !connected
              ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
              : "border-rose-200 bg-rose-50 text-rose-700 hover:-translate-y-0.5 hover:bg-white"
          }`}
        >
          No, not now
        </button>
        <button
          disabled={card.resolved || !connected}
          onClick={() => onLabDecision(card.id, card.sessionId || "", "accept")}
          className={`rounded-2xl px-4 py-2.5 text-sm font-medium transition ${
            card.resolved || !connected
              ? "cursor-not-allowed bg-slate-200 text-slate-400"
              : "bg-gradient-to-r from-sky-600 to-blue-600 text-white shadow-lg shadow-blue-200 hover:-translate-y-0.5"
          }`}
        >
          Yes, proceed
        </button>
      </div>
      {!connected && (
        <p className="mt-3 text-sm text-rose-600">
          Reconnecting to Ally... please wait before responding.
        </p>
      )}
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

      <div className={`max-w-[min(100%,36rem)] min-w-0 ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`rounded-3xl px-4 py-3 text-sm leading-6 shadow-sm break-words whitespace-pre-wrap ${
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
  doctorMessages,
  cards,
  thinking,
  doctorThinking,
  connected,
  onSelectDoctor,
  onSelectSlot,
  onLabDecision,
}: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const allMessages = [...messages, ...doctorMessages].sort(
    (a, b) => (a.timestamp || 0) - (b.timestamp || 0)
  );

  // Scroll to bottom instantly on first render
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  // Smooth scroll on new messages/cards
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allMessages, cards, thinking, doctorThinking]);

  const doctorCards = cards.filter((card) => card.kind === "doctor_select" && !card.resolved);
  const slotCards = cards.filter((card) => card.kind === "slot_select" && !card.resolved);
  const labCards = cards.filter((card) => card.kind === "lab_notification" && !card.resolved);
  const emptyState =
    messages.length === 0 && doctorMessages.length === 0 && cards.filter(c => !c.resolved).length === 0 &&
    !thinking && !doctorThinking;

  return (
    <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto px-4 py-5 sm:px-6 flex flex-col">
      {/* Spacer: pushes content to the bottom when there are few messages */}
      <div className="flex-1" />

      <div className="space-y-5">
        {emptyState ? (
          <div className="grid gap-6 overflow-hidden rounded-[2rem] border border-cyan-100 bg-[linear-gradient(180deg,#f8fdff_0%,#eefafd_100%)] p-5 shadow-[0_18px_45px_rgba(15,23,42,0.06)] lg:grid-cols-[1.1fr_0.9fr]">
            <div className="flex flex-col justify-center">
              <div className="inline-flex w-fit rounded-full bg-cyan-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-800">
                Ally Receptionist
              </div>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                Hi, I&apos;m Ally. I&apos;ll help you get started.
              </h2>
              <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600 sm:text-base">
                Tell me what you need, and I&apos;ll guide you through the next step, whether that is booking, continuing an appointment, or connecting you to the right care path.
              </p>

              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {[
                  "Book an appointment",
                  "Continue a consultation",
                  "Check inbox updates",
                  "View reports and follow-up",
                ].map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-white/80 bg-white/80 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/80 bg-white/85 p-4 shadow-[0_18px_40px_rgba(8,47,73,0.08)]">
              <MedicalTeamIllustration />
            </div>
          </div>
        ) : null}

        {allMessages.map((m) => (
          <Bubble key={m.id} message={m} isUser={m.role === "user"} />
        ))}

        {doctorCards.map((card) => (
          <DoctorCard key={card.id} card={card} onSelectDoctor={onSelectDoctor} />
        ))}

        {slotCards.map((card) => (
          <SlotCard key={card.id} card={card} onSelectSlot={onSelectSlot} />
        ))}

        {labCards.map((card) => (
          <LabCard
            key={card.id}
            card={card}
            connected={connected}
            onLabDecision={onLabDecision}
          />
        ))}

        {(thinking || doctorThinking) && (
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
