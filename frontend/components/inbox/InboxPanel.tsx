"use client";

import type { InboxNotification } from "@/types/chat";

interface InboxPanelProps {
  notifications: InboxNotification[];
  connected: boolean;
  onMarkRead: (id: string) => void;
  onViewReports: () => void;
  onViewAppointments: () => void;
  onLabDecision: (cardId: string, sessionId: string, decision: "accept" | "reject") => void;
}

function timeAgo(ts: number): string {
  const diffMin = Math.round((Date.now() - ts) / 60000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr} hr ago`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay} day ago`;
}

function KindIcon({ kind }: { kind: InboxNotification["kind"] }) {
  const className =
    kind === "appointment_booked"
      ? "bg-emerald-100 text-emerald-700"
      : kind === "lab_suggested"
      ? "bg-amber-100 text-amber-700"
      : "bg-sky-100 text-sky-700";

  return (
    <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${className}`}>
      {kind === "appointment_booked" ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
          <path d="M8 12.5 11 15.5 16 9.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />
        </svg>
      ) : kind === "lab_suggested" ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
          <path d="M6 6h12v12H6z" />
          <path d="M9 9h6" />
          <path d="M9 13h6" />
          <path d="M9 17h6" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
          <path d="M4 6.5h16v11H4z" />
          <path d="m4 7.5 8 6 8-6" />
        </svg>
      )}
    </div>
  );
}

export default function InboxPanel({
  notifications,
  connected,
  onMarkRead,
  onViewReports,
  onViewAppointments,
  onLabDecision,
}: InboxPanelProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 sm:px-6 py-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Inbox</h1>
          <p className="mt-1 text-sm text-slate-500">
            Stay on top of appointment updates and new lab results.
          </p>
        </div>
      </div>

      {notifications.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-200 bg-white/90 p-8 text-sm text-slate-500 shadow-sm">
          Nothing here yet. Notifications about your appointments and lab reports will show up here.
        </div>
      ) : (
        <div className="space-y-4">
          {notifications.map((n) => (
            <div
              key={n.id}
              onClick={() => onMarkRead(n.id)}
              className={`w-full rounded-3xl border p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
                n.read
                  ? "border-slate-200 bg-white"
                  : "border-sky-200 bg-sky-50/70"
              }`}
            >
              <div className="flex items-start gap-4">
                <KindIcon kind={n.kind} />

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-900">{n.title}</p>
                    <span className="text-[11px] uppercase tracking-[0.12em] text-slate-400">
                      {timeAgo(n.createdAt)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{n.body}</p>

                  {n.kind === "lab_notification" && n.decision === "pending" && n.cardId && n.sessionId && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onLabDecision(n.cardId || "", n.sessionId || "", "reject");
                        }}
                        className="inline-flex rounded-full bg-white px-4 py-2 text-xs font-semibold text-rose-700 shadow-sm ring-1 ring-rose-200 transition hover:-translate-y-0.5"
                      >
                        Decline tests
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onLabDecision(n.cardId || "", n.sessionId || "", "accept");
                        }}
                        className="inline-flex rounded-full bg-sky-600 px-4 py-2 text-xs font-semibold text-white shadow-sm shadow-blue-200 transition hover:-translate-y-0.5"
                      >
                        Accept tests
                      </button>
                    </div>
                  )}

                  {n.kind === "lab_notification" && n.decision && n.decision !== "pending" && (
                    <p className="mt-3 text-xs font-semibold text-slate-500">
                      {n.decision === "accepted" ? "Tests accepted" : "Tests declined"}
                    </p>
                  )}

                  {n.kind === "report_ready" && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewReports();
                        }}
                        className="inline-flex rounded-full bg-white px-4 py-2 text-xs font-semibold text-sky-700 shadow-sm ring-1 ring-sky-200 transition hover:-translate-y-0.5"
                      >
                        Go to lab reports
                      </button>
                      {n.reportUrl && (
                        <a
                          href={n.reportUrl}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex rounded-full bg-sky-600 px-4 py-2 text-xs font-semibold text-white shadow-sm shadow-blue-200 transition hover:-translate-y-0.5"
                        >
                          {n.title.toLowerCase().includes("prescription") ? "Download Prescription" : "Download PDF"}
                        </a>
                      )}
                    </div>
                  )}
                  {n.kind === "appointment_booked" && (
                    <div className="mt-4">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewAppointments();
                        }}
                        className="inline-flex rounded-full bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm shadow-emerald-200 transition hover:-translate-y-0.5"
                      >
                        Start Consultation
                      </button>
                    </div>
                  )}
                  {n.kind === "lab_suggested" && (
                    <div className="mt-4 rounded-3xl border border-slate-200 bg-slate-50 p-4">
                      <div className="mb-4">
                        <p className="text-sm font-semibold text-slate-900">Recommended lab tests</p>
                        <p className="mt-1 text-xs text-slate-500">Review the suggested tests before continuing.</p>
                      </div>
                      <div className="space-y-3">
                        {(n.tests || []).map((test, index) => (
                          <div key={index} className="rounded-2xl bg-white p-3 shadow-sm">
                            <p className="text-sm font-medium text-slate-900">{test.name}</p>
                            <p className="mt-1 text-xs leading-5 text-slate-500">{test.reason}</p>
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 grid gap-2 sm:grid-cols-2">
                        <button
                          type="button"
                          disabled={!connected}
                          onClick={(e) => {
                            e.stopPropagation();
                            onLabDecision(n.cardId || "", n.reportId || "", "reject");
                          }}
                          className={`inline-flex w-full justify-center rounded-full border px-4 py-2 text-xs font-semibold shadow-sm transition ${
                            connected
                              ? "border-rose-200 bg-rose-50 text-rose-700 hover:-translate-y-0.5"
                              : "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                          }`}
                        >
                          No, not now
                        </button>
                        <button
                          type="button"
                          disabled={!connected}
                          onClick={(e) => {
                            e.stopPropagation();
                            onLabDecision(n.cardId || "", n.reportId || "", "accept");
                          }}
                          className={`inline-flex w-full justify-center rounded-full px-4 py-2 text-xs font-semibold shadow-sm transition ${
                            connected
                              ? "bg-gradient-to-r from-sky-600 to-blue-600 text-white hover:-translate-y-0.5"
                              : "cursor-not-allowed bg-slate-200 text-slate-400"
                          }`}
                        >
                          Yes, proceed
                        </button>
                      </div>
                      {!connected && (
                        <p className="mt-3 text-xs text-rose-600">
                          Reconnecting to Ally... please wait before responding.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
