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
  const common = "w-4 h-4";
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
    <aside className="w-56 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
      <div className="flex items-center gap-2 px-4 py-4 border-b border-gray-200">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white text-sm font-semibold">
          A
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900">Ally AI</p>
          <p className="text-xs text-gray-500">Hospital assistant</p>
        </div>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = item.id === active;
          return (
            <button
              key={item.id}
              onClick={() => onChange(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-blue-100 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <Icon name={item.icon} />
              <span className="flex-1 text-left">{item.label}</span>
              {item.id === "inbox" && unreadCount > 0 && (
                <span className="text-[11px] bg-blue-600 text-white rounded-full px-1.5 py-0.5 leading-none">
                  {unreadCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="px-3 py-3 border-t border-gray-200 flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-green-100 text-green-700 text-xs font-semibold flex items-center justify-center">
          {getInitials(patientName)}
        </div>
        <p className="text-xs text-gray-600 truncate">{patientName}</p>
      </div>
    </aside>
  );
}