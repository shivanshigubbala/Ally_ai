"use client";

import { useEffect, useRef, type KeyboardEvent } from "react";
import type { ChatCard, ChatMessage, DoctorReadyInfo } from "@/types/chat";

interface AppointmentsPanelProps {
  doctorName: string | null;
  booked: boolean;
  slotCards: ChatCard[];
  onSelectSlot: (cardId: string, slotId: string, doctorId: string) => void;
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
    <div className="flex min-h-0 flex-col rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 py-4 sm:px-5">
        <h3 className="text-sm font-semibold text-slate-900">Live consultation</h3>
        <p className="mt-1 text-xs text-slate-500">Chat with the doctor once the appointment is active.</p>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 sm:px-5">
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
  onSelectSlot,
  doctorReady,
  doctorMessages,
  doctorThinking,
  consultationActive,
  onStartConsultation,
  onSendDoctorMessage,
}: AppointmentsPanelProps) {
  const activeSlotCard = slotCards.find((card) => !card.resolved) || slotCards[0];

  if (consultationActive) {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 sm:px-6 py-6">
        <div className="mb-5">
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">
            Consultation with {doctorName || "Dr. Shankar"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Use the message box below to continue the live doctor conversation.
          </p>
        </div>

        <div className="space-y-4">
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
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 sm:px-6 py-6">
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

      </div>
    );
  }

  if (booked) {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 sm:px-6 py-6">
        <div className="mb-5">
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Appointments</h1>
          <p className="mt-1 text-sm text-slate-500">
            Your appointment is confirmed. The doctor is not online yet, so please wait here for the call.
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
                The reception has booked your appointment. We will notify you as soon as the doctor is ready.
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
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 sm:px-6 py-6">
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
      </div>
    </div>
  );
}
