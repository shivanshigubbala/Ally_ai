"use client";

interface ChatHeaderProps {
  connected: boolean;
}

export default function ChatHeader({ connected }: ChatHeaderProps) {
  const name = "Ally Receptionist";
  const initials =
    name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("") || "MD";

  return (
    <div className="px-4 pt-4 sm:px-6 sm:pt-6">
      <div className="rounded-[2rem] border border-white/80 bg-white/95 px-4 py-4 shadow-[0_20px_70px_rgba(15,23,42,0.08)] backdrop-blur sm:px-5 sm:py-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 via-blue-600 to-indigo-600 text-lg font-semibold text-white shadow-lg shadow-blue-200">
              {initials}
              <span className="absolute -bottom-1 -right-1 h-4 w-4 rounded-full border-2 border-white bg-emerald-500" />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-lg sm:text-xl font-semibold tracking-tight text-slate-900">
                  {name}
                </h1>
                <span className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.14em] text-sky-700">
                  Receptionist
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-600">
                Friendly intake, appointment guidance, and handoff support.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                connected
                  ? "bg-emerald-500 shadow-[0_0_0_4px_rgba(16,185,129,0.18)]"
                  : "bg-slate-300"
              }`}
            />
            <div>
              <p className="text-sm font-medium text-slate-900">
                {connected ? "Online now" : "Connecting"}
              </p>
              <p className="text-xs text-slate-500">
                {connected ? "Ready to greet patients" : "Waiting for secure socket connection"}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
