"use client";

import { useEffect, useRef } from "react";
import type { ChatCard, ChatMessage } from "@/types/chat";

interface ChatThreadProps {
  messages: ChatMessage[];
  cards: ChatCard[];
  thinking: string | null;
  onSelectSlot: (cardId: string, slotId: string, doctorId: string) => void;
  onLabDecision: (
    cardId: string,
    sessionId: string,
    decision: "accept" | "reject"
  ) => void;
}

function formatSlotTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
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
  onSelectSlot: ChatThreadProps["onSelectSlot"];
}) {
  return (
    <div className="ml-10 max-w-md border border-gray-200 rounded-xl p-4 bg-white">
      <p className="text-sm text-gray-700 mb-3">
        Available slots{card.doctorName ? ` with ${card.doctorName}` : ""}:
      </p>
      <div className="flex flex-wrap gap-2">
        {(card.slots || []).map((slot) => (
          <button
            key={slot.id}
            disabled={card.resolved}
            onClick={() => onSelectSlot(card.id, slot.id, slot.doctor_id)}
            className={`text-xs px-3 py-1.5 rounded-lg border ${
              card.resolved
                ? "border-gray-200 text-gray-400 cursor-not-allowed"
                : "border-blue-300 text-blue-700 hover:bg-blue-50"
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
    <div className="ml-10 max-w-md border border-gray-200 rounded-xl p-4 bg-white">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-7 h-7 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-sm">
          ⚗
        </span>
        <p className="text-sm font-medium text-gray-900">
          Recommended lab tests
        </p>
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
          onClick={() =>
            onLabDecision(card.id, card.sessionId || "", "reject")
          }
          className={`flex-1 text-sm px-3 py-1.5 rounded-lg border ${
            card.resolved
              ? "border-gray-200 text-gray-400 cursor-not-allowed"
              : "border-gray-300 text-gray-700 hover:bg-gray-50"
          }`}
        >
          Not now
        </button>
        <button
          disabled={card.resolved}
          onClick={() =>
            onLabDecision(card.id, card.sessionId || "", "accept")
          }
          className={`flex-1 text-sm px-3 py-1.5 rounded-lg ${
            card.resolved
              ? "bg-gray-200 text-gray-400 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          Accept tests
        </button>
      </div>
    </div>
  );
}

export default function ChatThread({
  messages,
  cards,
  thinking,
  onSelectSlot,
  onLabDecision,
}: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, cards, thinking]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
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
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-semibold shrink-0">
              {m.from ? "MD" : "AI"}
            </div>
            <div className="bg-gray-100 rounded-2xl px-4 py-2.5 max-w-[75%] text-sm text-gray-800">
              {m.content}
            </div>
          </div>
        );
      })}

      {cards.map((card) =>
        card.kind === "slot_select" ? (
          <SlotCard key={card.id} card={card} onSelectSlot={onSelectSlot} />
        ) : (
          <LabCard key={card.id} card={card} onLabDecision={onLabDecision} />
        )
      )}

      {thinking && (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-semibold shrink-0">
            AI
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
  );
}