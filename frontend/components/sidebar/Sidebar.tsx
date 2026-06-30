"use client";

import { getInitials } from "@/lib/patient";

export type SidebarTab =
  | "chat"
  | "appointments"
  | "inbox"
  | "reports"
  | "profile";

interface SidebarProps {
  active: SidebarTab;
  onChange: (tab: SidebarTab) => void;
  patientName: string;
  unreadCount: number;
}

const NAV_ITEMS: { id: SidebarTab; label: string; icon: string }[] = [
  { id: "chat", label: "Chat", icon: "i-chat" },
  { id: "appointments", label: "Appointments", icon: "i-calendar" },
  { id: "inbox", label: "Inbox", icon: "i-inbox" },
  { id: "reports", label: "Lab reports", icon: "i-flask" },
  { id: "profile", label: "Profile", icon: "i-user" },
];

function Icon({ name }: { name: string }) {
  const common = "h-4 w-4";
  switch (name) {
    case "i-chat":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M21 12c0 4.4-4 8-9 8-1.1 0-2.2-.2-3.2-.5L3 21l1.6-4.8C3.6 14.9 3 13.5 3 12c0-4.4 4-8 9-8s9 3.6 9 8Z" strokeLinejoin="round" />
        </svg>
      );
    case "i-calendar":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="3" y="5" width="18" height="16" rx="2" />
          <path d="M3 9h18M8 3v4M16 3v4" />
        </svg>
      );
    case "i-inbox":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M3 12h4l2 3h6l2-3h4" />
          <rect x="3" y="6" width="18" height="13" rx="2" />
        </svg>
      );
    case "i-flask":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M9 3h6M10 3v6L5 18a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3" />
        </svg>
      );
    case "i-user":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="8" r="3.5" />
          <path d="M5 21c0-3.9 3.1-7 7-7s7 3.1 7 7" />
        </svg>
      );
    default:
      return null;
  }
}

export default function Sidebar({
  active,
  onChange,
  patientName,
  unreadCount,
}: SidebarProps) {
  return (
    <aside className="flex w-full flex-col overflow-hidden rounded-[32px] border border-white/70 bg-white/90 shadow-[8px_0_40px_rgba(15,23,42,0.05)] backdrop-blur lg:w-64">
      <div className="border-b border-slate-100 px-4 py-5">
        <div className="flex items-center gap-3 rounded-3xl bg-slate-50 p-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 via-blue-600 to-indigo-600 text-sm font-semibold text-white shadow-lg shadow-blue-200">
            A
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold tracking-tight text-slate-900">Ally AI</p>
            <p className="text-xs text-slate-500">Hospital assistant</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive = item.id === active;
          return (
            <button
              key={item.id}
              onClick={() => onChange(item.id)}
              className={`flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm transition ${
                isActive
                  ? "bg-gradient-to-r from-sky-600 to-blue-600 text-white shadow-lg shadow-blue-200"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon name={item.icon} />
              <span className="flex-1 text-left font-medium">{item.label}</span>
              {item.id === "inbox" && unreadCount > 0 && (
                <span className={`rounded-full px-2 py-1 text-[11px] font-semibold leading-none ${
                  isActive ? "bg-white/20 text-white" : "bg-sky-100 text-sky-700"
                }`}>
                  {unreadCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-slate-100 p-4">
        <div className="flex items-center gap-3 rounded-3xl bg-slate-50 p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700 text-xs font-semibold">
            {getInitials(patientName)}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-slate-900">{patientName}</p>
            <p className="text-xs text-slate-500">Secure patient session</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
