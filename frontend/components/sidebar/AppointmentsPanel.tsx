"use client";

import { useEffect, useRef, type KeyboardEvent } from "react";
import type { ChatCard, ChatMessage, DoctorReadyInfo } from "@/types/chat";

interface AppointmentsPanelProps {
  doctorName: string | null;
  booked: boolean;
  slotCards: ChatCard[];
  labCards: ChatCard[];
  onSelectSlot: (cardId: string, slotId: string, doctorId: string) => void;
  onLabDecision: (cardId: string, sessionId: string, decision: "accept" | "reject") => void;
  doctorReady: DoctorReadyInfo | null;
  doctorMessages: ChatMessage[];
  doctorThinking: string | null;
  consultationActive: boolean;
  onStartConsultation: () => void;
  onSendDoctorMessage: (content: string) => void;
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

function SlotCard({
  card,
  onSelectSlot,
}: {
  card: ChatCard;
  onSelectSlot: AppointmentsPanelProps["onSelectSlot"];
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 text-sm font-semibold">
          S
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">Appointment slots</p>
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
  onLabDecision: AppointmentsPanelProps["onLabDecision"];
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 text-sm font-semibold">
          L
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">Recommended lab tests</p>
          <p className="text-xs text-slate-500">Review the suggested tests before continuing.</p>
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

function DoctorChat({
  messages,
  thinking,
  onSend,
}: {
  messages: ChatMessage[];
  thinking: string | null;
  onSend: (content: string) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && inputRef.current?.value.trim()) {
      onSend(inputRef.current.value);
      inputRef.current.value = "";
    }
  };

  return (
    <div className="rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 py-4 sm:px-5">
        <h3 className="text-sm font-semibold text-slate-900">Live consultation</h3>
        <p className="mt-1 text-xs text-slate-500">Chat with the doctor once the appointment is active.</p>
      </div>

      <div className="max-h-[28rem] overflow-y-auto px-4 py-4 sm:px-5">
        <div className="space-y-4">
          {messages.map((m) => {
            const isUser = m.role === "user";
            return (
              <div key={m.id} className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                {!isUser && (
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-xs font-semibold text-emerald-700">
                    MD
                  </div>
                )}
                <div className={`max-w-[min(100%,32rem)] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
                  <div
                    className={`rounded-3xl px-4 py-3 text-sm leading-6 shadow-sm ${
                      isUser
                        ? "bg-gradient-to-r from-sky-600 to-blue-600 text-white"
                        : "border border-slate-200 bg-white text-slate-800"
                    }`}
                  >
                    {m.content}
                  </div>
                </div>
                {isUser && (
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-sky-100 text-xs font-semibold text-sky-700">
                    You
                  </div>
                )}
              </div>
            );
          })}

          {thinking && (
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-xs font-semibold text-emerald-700">
                MD
              </div>
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

      <div className="border-t border-slate-100 p-4">
        <input
          ref={inputRef}
          type="text"
          placeholder="Reply to the doctor..."
          onKeyDown={handleKeyDown}
          className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-sky-300 focus:bg-white focus:ring-4 focus:ring-sky-100"
        />
      </div>
    </div>
  );
}

export default function AppointmentsPanel({
  doctorName,
  booked,
  slotCards,
  labCards,
  onSelectSlot,
  onLabDecision,
  doctorReady,
  doctorMessages,
  doctorThinking,
  consultationActive,
  onStartConsultation,
  onSendDoctorMessage,
}: AppointmentsPanelProps) {
  const activeSlotCard = slotCards.find((card) => !card.resolved) || slotCards[0];
  const activeLabCards = labCards.filter((card) => !card.resolved);

  if (consultationActive) {
    return (
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        <div className="mb-5">
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">
            Consultation with {doctorName || "Dr. Shankar"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Use the message box below to continue the live doctor conversation.
          </p>
        </div>

        <div className="space-y-4">
          {activeLabCards.map((card) => (
            <LabCard key={card.id} card={card} onLabDecision={onLabDecision} />
          ))}
          <DoctorChat
            messages={doctorMessages}
            thinking={doctorThinking}
            onSend={onSendDoctorMessage}
          />
        </div>
      </div>
    );
  }

  if (doctorReady) {
    return (
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        <div className="mb-5">
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Appointments</h1>
          <p className="mt-1 text-sm text-slate-500">
            Your appointment is confirmed and ready to start.
          </p>
        </div>

        <div className="max-w-2xl rounded-3xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
                <path d="M8 12.5 11 15.5 16 9.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-base font-semibold text-slate-900">
                {doctorReady.doctorName}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                Appointment confirmed. Tap below to begin the consultation.
              </p>
              <button
                onClick={onStartConsultation}
                className="mt-4 inline-flex rounded-2xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-200 transition hover:-translate-y-0.5"
              >
                Start Consultation
              </button>
            </div>
          </div>
        </div>

        {activeLabCards.length > 0 && (
          <div className="mt-5 space-y-4">
            {activeLabCards.map((card) => (
              <LabCard key={card.id} card={card} onLabDecision={onLabDecision} />
            ))}
          </div>
        )}
      </div>
    );
  }

  if (booked) {
    return (
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        <div className="mb-5">
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Appointments</h1>
          <p className="mt-1 text-sm text-slate-500">
            Your doctor is being prepared for the consultation.
          </p>
        </div>

        <div className="max-w-2xl rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
                <path d="M8 12.5 11 15.5 16 9.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />
              </svg>
            </div>
            <div>
              <p className="text-base font-semibold text-slate-900">
                {doctorName || "Doctor"}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                Appointment confirmed. Your doctor will appear here when ready.
              </p>
            </div>
          </div>
        </div>

        {activeSlotCard && !activeSlotCard.resolved && (
          <div className="mt-5">
            <SlotCard card={activeSlotCard} onSelectSlot={onSelectSlot} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 min-h-0">
      <div className="mb-5">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">Appointments</h1>
        <p className="mt-1 text-sm text-slate-500">
          Complete the booking flow in chat and we&apos;ll surface the next step here.
        </p>
      </div>

      <div className="space-y-4">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-semibold text-slate-900">Waiting for your appointment</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            The receptionist is helping you book your appointment. Continue the conversation in the Chat tab until your doctor is ready.
          </p>
        </div>

        {activeSlotCard && !activeSlotCard.resolved && (
          <SlotCard card={activeSlotCard} onSelectSlot={onSelectSlot} />
        )}

        {activeLabCards.map((card) => (
          <LabCard key={card.id} card={card} onLabDecision={onLabDecision} />
        ))}
      </div>
    </div>
  );
}
