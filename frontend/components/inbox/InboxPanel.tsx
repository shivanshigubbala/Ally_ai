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
  return `${diffHr} hr ago`;
}

export default function InboxPanel({
  notifications,
  onMarkRead,
  onViewReports,
}: InboxPanelProps) {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h1 className="text-base font-semibold text-gray-900 mb-4">Inbox</h1>

      {notifications.length === 0 ? (
        <p className="text-sm text-gray-500">
          Nothing here yet. Notifications about your appointments and lab
          reports will show up here.
        </p>
      ) : (
        <div className="space-y-3 max-w-lg">
          {notifications.map((n) => (
            <div
              key={n.id}
              onClick={() => onMarkRead(n.id)}
              className={`border rounded-xl p-4 cursor-pointer ${
                n.read ? "border-gray-200 bg-white" : "border-blue-200 bg-blue-50"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                    n.kind === "appointment_booked"
                      ? "bg-green-100 text-green-700"
                      : "bg-blue-100 text-blue-700"
                  }`}
                >
                  {n.kind === "appointment_booked" ? "📅" : "📄"}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {n.title}
                  </p>
                  <p className="text-xs text-gray-400">{timeAgo(n.createdAt)}</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 mb-3">{n.body}</p>

              {n.kind === "report_ready" && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewReports();
                  }}
                  className="text-xs font-medium text-blue-700 hover:underline"
                >
                  Go to lab reports →
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}