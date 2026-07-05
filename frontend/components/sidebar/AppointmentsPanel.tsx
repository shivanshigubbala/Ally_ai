"use client";

import { useEffect, useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { getBackendBase } from "@/lib/backend";
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
  consultationChart: string | null;
  userId: string | null;
  hasPendingTests?: boolean;
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
  disabled,
}: {
  messages: ChatMessage[];
  thinking: string | null;
  onSend: (content: string) => void;
  disabled?: boolean;
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
          disabled={disabled}
          placeholder={disabled ? "Please accept or decline the recommended tests in the Notifications tab..." : "Reply to the doctor..."}
          onKeyDown={handleKeyDown}
          className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-sky-300 focus:bg-white focus:ring-4 focus:ring-sky-100 disabled:opacity-60 disabled:cursor-not-allowed"
        />
      </div>
    </div>
  );
}

/** Pre-consultation step: ask the user if they have prior records to upload */
function PreConsultationUpload({
  doctorReady,
  userId,
  onProceed,
}: {
  doctorReady: DoctorReadyInfo;
  userId: string | null;
  onProceed: (files: string[]) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [processingMessage, setProcessingMessage] = useState<string | null>(null);

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    setUploadError(null);

    const newNames: string[] = [];
    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(
          `${getBackendBase()}/upload-document/${encodeURIComponent(userId || "")}/${encodeURIComponent(doctorReady.appointmentId)}`,
          { method: "POST", body: formData }
        );
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Upload failed" }));
          setUploadError(`${file.name}: ${err.detail || "Upload failed"}`);
        } else {
          newNames.push(file.name);
        }
      } catch {
        setUploadError(`${file.name}: Could not reach server`);
      }
    }
    setUploadedFiles((prev) => [...prev, ...newNames]);
    setUploading(false);
    // Reset input so the same file can be re-uploaded if needed
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const checkAllIndexed = async () => {
    try {
      const res = await fetch(
        `http://localhost:8000/uploaded-files/${encodeURIComponent(userId || "")}/${encodeURIComponent(doctorReady.appointmentId)}`
      );
      if (!res.ok) return false;
      const data = await res.json();
      const files = data.files || [];
      if (files.length === 0) return true;
      return files.every((f: any) => (f.status || "") === "indexed");
    } catch {
      return false;
    }
  };

  return (
    <div className="space-y-5">
      <div className="mb-5">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">Before you start</h1>
        <p className="mt-1 text-sm text-slate-500">
          Let the doctor know if you have any prior medical records.
        </p>
      </div>

      {/* Upload card */}
      <div className="max-w-2xl rounded-3xl border border-sky-100 bg-gradient-to-b from-sky-50 to-white p-6 shadow-sm">
        {/* Icon + question */}
        <div className="flex items-start gap-4 mb-5">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-sky-100 text-sky-600">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-6 w-6">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round" />
              <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
              <line x1="12" y1="18" x2="12" y2="12" strokeLinecap="round" />
              <line x1="9" y1="15" x2="15" y2="15" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <p className="text-base font-semibold text-slate-900">
              Have you visited another doctor for this issue?
            </p>
            <p className="mt-1.5 text-sm leading-6 text-slate-600">
              If you have any previous reports, prescriptions, or test results, you can upload them
              now so {doctorReady.doctorName} can review them during your consultation.
            </p>
          </div>
        </div>

        {/* Uploaded files list */}
        {uploadedFiles.length > 0 && (
          <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 space-y-1.5">
            {uploadedFiles.map((name, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-emerald-800">
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 shrink-0 text-emerald-500">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414L8.414 15 4.293 10.879a1 1 0 011.414-1.414L8.414 12.172l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">{name}</span>
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {uploadError && (
          <p className="mb-3 text-xs text-rose-600 bg-rose-50 rounded-xl px-3 py-2">{uploadError}</p>
        )}

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center gap-2 rounded-2xl border border-sky-200 bg-white px-5 py-3 text-sm font-semibold text-sky-700 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {uploading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-sky-300 border-t-sky-600" />
                Uploading…
              </>
            ) : (
              <>
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                  <path d="M4 16v1a2 2 0 002 2h8a2 2 0 002-2v-1M10 3v9m0-9L7 6m3-3l3 3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {uploadedFiles.length > 0 ? "Upload more files" : "Upload files"}
              </>
            )}
          </button>

          <button
            disabled={uploading}
            onClick={async () => {
              // Check indexing status before proceeding
              setProcessingMessage(null);
              const ok = await checkAllIndexed();
              if (ok) {
                onProceed(uploadedFiles);
              } else {
                setProcessingMessage("We are still processing your uploads. Please wait a moment.");
              }
            }}
            className="flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-200 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {uploadedFiles.length > 0 ? (
              <>
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 000 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clipRule="evenodd" />
                </svg>
                Start Consultation
              </>
            ) : (
              <>
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 000 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clipRule="evenodd" />
                </svg>
                No, start without files
              </>
            )}
          </button>
        </div>

        {processingMessage && (
          <p className="mt-3 text-sm text-amber-600">{processingMessage}</p>
        )}

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.csv,.png,.jpg,.jpeg"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {/* Supported formats note */}
      <p className="mt-3 ml-1 text-xs text-slate-400">
        Supported: PDF, TXT, CSV, PNG, JPG
      </p>
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
  consultationChart,
  userId,
  hasPendingTests,
}: AppointmentsPanelProps) {
  const activeSlotCard = slotCards.find((card) => !card.resolved) || slotCards[0];
  /** Whether the pre-consultation upload step has been completed */
  const [uploadStepDone, setUploadStepDone] = useState(false); // allow uploads before starting consultation

  // Reset upload step whenever a new appointment becomes ready
  useEffect(() => {
    if (doctorReady) setUploadStepDone(false);
  }, [doctorReady?.appointmentId]);

  const renderConsultationChart = () => {
    return (
      <div className="mt-6 max-w-2xl">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-3">
          Intake Consultation Chart
        </h3>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          {consultationChart ? (
            <div className="prose prose-slate max-w-none space-y-2">
              {parseMarkdown(consultationChart)}
            </div>
          ) : (
            <div className="flex items-center gap-3 py-2 text-slate-500 text-sm">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-sky-500"></span>
              </span>
              <span>Generating consultation chart... please wait.</span>
            </div>
          )}
        </div>
      </div>
    );
  };

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
            disabled={hasPendingTests}
          />
        </div>
      </div>
    );
  }

  // Show PreConsultationUpload or Start Consultation when doctor is ready
  if (doctorReady) {
    if (!uploadStepDone) {
      return (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 sm:px-6 py-6">
          <PreConsultationUpload
            doctorReady={doctorReady}
            userId={userId}
            onProceed={(files) => {
              setUploadStepDone(true);
              onStartConsultation();
            }}
          />
          {renderConsultationChart()}
        </div>
      );
    }

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
                Consultation pending for {doctorReady.department || "your selected department"}. Appointment confirmed. Tap below to begin the consultation.
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

        {renderConsultationChart()}
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

        {renderConsultationChart()}

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

function parseMarkdown(md: string) {
  const lines = md.split("\n");
  return lines.map((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return <div key={idx} className="h-2" />;
    }

    if (trimmed.startsWith("###")) {
      return (
        <h4 key={idx} className="mt-4 mb-2 text-sm font-semibold text-slate-800 uppercase tracking-wider">
          {parseBoldText(trimmed.substring(3).trim())}
        </h4>
      );
    }
    if (trimmed.startsWith("##")) {
      return (
        <h3 key={idx} className="mt-5 mb-2 text-base font-bold text-slate-900 border-b border-slate-100 pb-1">
          {parseBoldText(trimmed.substring(2).trim())}
        </h3>
      );
    }
    if (trimmed.startsWith("#")) {
      return (
        <h2 key={idx} className="mt-6 mb-3 text-lg font-bold text-slate-900 border-b border-slate-200 pb-1.5">
          {parseBoldText(trimmed.substring(1).trim())}
        </h2>
      );
    }

    if (trimmed.startsWith("-") || trimmed.startsWith("*")) {
      return (
        <li key={idx} className="ml-4 list-disc text-sm text-slate-600 py-1">
          {parseBoldText(trimmed.substring(1).trim())}
        </li>
      );
    }

    return (
      <p key={idx} className="text-sm text-slate-600 leading-6 my-1">
        {parseBoldText(trimmed)}
      </p>
    );
  });
}

function parseBoldText(text: string) {
  const parts = text.split(/\*\*([^*]+)\*\*/g);
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      return <strong key={i} className="font-bold text-slate-900">{part}</strong>;
    }
    return part;
  });
}
