"use client";

import type { InboxNotification } from "@/types/chat";

interface InboxPanelProps {
  notifications: InboxNotification[];
  onMarkRead: (id: string) => void;
  onViewReports: () => void;
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
      : "bg-sky-100 text-sky-700";

  return (
    <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${className}`}>
      {kind === "appointment_booked" ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
          <path d="M8 12.5 11 15.5 16 9.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />
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
  onMarkRead,
  onViewReports,
}: InboxPanelProps) {
  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
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

                  {n.kind === "report_ready" && (
                    <div className="mt-4">
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
