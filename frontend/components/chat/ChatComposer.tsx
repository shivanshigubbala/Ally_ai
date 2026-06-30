"use client";

import { useState, type KeyboardEvent } from "react";

interface ChatComposerProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function ChatComposer({ onSend, disabled }: ChatComposerProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    if (!value.trim()) return;
    onSend(value);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-white/70 bg-white/90 px-4 py-4 backdrop-blur sm:px-6">
      <div className="rounded-[2rem] border border-slate-200 bg-white p-3 shadow-[0_14px_40px_rgba(15,23,42,0.06)]">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="mb-2 block text-xs font-medium uppercase tracking-[0.14em] text-slate-400">
              Message Ally
            </label>
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder="Type a message or ask a follow-up question"
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-cyan-300 focus:bg-white focus:ring-4 focus:ring-cyan-100 disabled:cursor-not-allowed disabled:bg-slate-100"
            />
          </div>

          <button
            onClick={submit}
            disabled={disabled}
            className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#1ea7c6] px-5 text-sm font-semibold text-white shadow-[0_16px_35px_rgba(30,167,198,0.28)] transition hover:-translate-y-0.5 hover:shadow-xl disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-50"
            aria-label="Send message"
          >
            <span>Send</span>
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-400">
          Press Enter to send. Your message stays in this secure Ally AI flow.
        </p>
      </div>
    </div>
  );
}
