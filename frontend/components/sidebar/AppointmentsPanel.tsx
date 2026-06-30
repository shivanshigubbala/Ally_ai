"use client";

import { useEffect, useRef } from "react";
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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && inputRef.current?.value.trim()) {
      onSend(inputRef.current.value);
      inputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.map((m) => {
          if (m.role === "user") {
            return (
              <div key={m.id} className="flex justify-end">
                <div className="bg-blue-600 text-white rounded-2xl px-4 py-2.5 max-w-[75%] text-sm">
                  {m.content}
                </div>
              </div>
            );
          }
          return (
            <div key={m.id} className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-semibold shrink-0">
                MD
              </div>
              <div className="bg-white border border-gray-200 rounded-2xl px-4 py-2.5 max-w-[75%] text-sm text-gray-800">
                {m.content}
              </div>
            </div>
          );
        })}
        {thinking && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-semibold shrink-0">
              MD
            </div>
            <div className="flex items-center gap-1 text-gray-400 text-sm">
              <span className="animate-pulse">●</span>
              <span className="animate-pulse [animation-delay:150ms]">●</span>
              <span className="animate-pulse [animation-delay:300ms]">●</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-gray-200 p-4">
        <input
          ref={inputRef}
          type="text"
          placeholder="Reply to Dr. Shankar..."
          onKeyDown={handleKeyDown}
          className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm outline-none focus:border-blue-400"
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
  const activeCard = slotCards[0];

function LabCard({
  card,
  onLabDecision,
}: {
  card: ChatCard;
  onLabDecision: AppointmentsPanelProps["onLabDecision"];
}) {
  return (
    <div className="mb-4 ml-10 max-w-md border border-gray-200 rounded-xl p-4 bg-white">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-7 h-7 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-sm">
          ⚗
        </span>
        <p className="text-sm font-medium text-gray-900">Recommended lab tests</p>
      </div>
      <div className="space-y-2 mb-4">
        {(card.tests || []).map((test, i) => (
          <div key={i} className="bg-gray-50 rounded-lg px-3 py-2">
            <p className="text-sm font-medium text-gray-900">{test.name}</p>
            <p className="text-xs text-gray-500">{test.reason}</p>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          disabled={card.resolved}
          onClick={() => onLabDecision(card.id, card.sessionId || "", "reject")}
          aria-label="Reject tests"
          className={`flex-1 text-sm px-3 py-1.5 rounded-lg border ${
            card.resolved
              ? "border-gray-200 text-gray-400 cursor-not-allowed"
              : "border-red-300 text-red-700 hover:bg-red-50"
          }`}
        >
          ✕ No
        </button>
        <button
          disabled={card.resolved}
          onClick={() => onLabDecision(card.id, card.sessionId || "", "accept")}
          aria-label="Accept tests"
          className={`flex-1 text-sm px-3 py-1.5 rounded-lg ${
            card.resolved
              ? "bg-gray-200 text-gray-400 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          ✓ Yes
        </button>
      </div>
    </div>
  );
}

  if (consultationActive) {
    return (
      <div className="flex-1 flex flex-col min-h-0">
        <div className="px-6 py-4 border-b border-gray-200">
          <h1 className="text-base font-semibold text-gray-900">
            Consultation with {doctorName || "Dr. Shankar"}
          </h1>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {labCards.map((card) => (
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
      <div className="flex-1 overflow-y-auto p-6">
        <h1 className="text-base font-semibold text-gray-900 mb-4">
          Appointments
        </h1>
        <div className="max-w-lg border border-green-200 rounded-xl p-6 bg-green-50">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center text-green-700">
              ✓
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                {doctorReady.doctorName}
              </p>
              <p className="text-xs text-gray-500">
                Appointment confirmed - ready for consultation
              </p>
            </div>
          </div>
          <button
            onClick={onStartConsultation}
            className="w-full text-sm px-4 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium"
          >
            Start Consultation
          </button>
        </div>
      </div>
    );
  }

  if (booked) {
    return (
      <div className="flex-1 overflow-y-auto p-6">
        <h1 className="text-base font-semibold text-gray-900 mb-4">
          Appointments
        </h1>
        <div className="max-w-lg border border-gray-200 rounded-xl p-4 flex items-center gap-3 bg-white">
          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center text-green-700">
            ✓
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">
              {doctorName || "Doctor"}
            </p>
            <p className="text-xs text-gray-500">
              Appointment confirmed. Your doctor will be online here when ready.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 min-h-0">
      <h1 className="text-base font-semibold text-gray-900 mb-4">
        Appointments
      </h1>

      <div className="max-w-lg space-y-4">
        <div className="border border-gray-200 rounded-xl p-4 bg-white">
          <p className="text-sm font-medium text-gray-900">Waiting for your appointment</p>
          <p className="text-sm text-gray-500 mt-1">
            The receptionist is helping you book your appointment. Continue the conversation in the Chat tab until your doctor is ready.
          </p>
        </div>
      </div>
    </div>
  );
}
