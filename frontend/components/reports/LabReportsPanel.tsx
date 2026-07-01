"use client";

import type { LabReport } from "@/types/chat";

interface LabReportsPanelProps {
  reports: LabReport[];
  onAddSampleReport?: () => void;
}

function formatDate(ts: number): string {
  return new Date(ts).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function LabReportsPanel({
  reports,
  onAddSampleReport,
}: LabReportsPanelProps) {
  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Lab reports</h1>
          <p className="mt-1 text-sm text-slate-500">
            View completed tests and download available results.
          </p>
        </div>

        {typeof onAddSampleReport === "function" && (
          <button
            onClick={onAddSampleReport}
            className="inline-flex rounded-full bg-sky-600 px-4 py-2 text-xs font-semibold text-white shadow-sm shadow-blue-200 transition hover:-translate-y-0.5 hover:bg-sky-700"
          >
            Add sample report
          </button>
        )}
      </div>

      {reports.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-200 bg-white/90 p-8 text-sm text-slate-500 shadow-sm">
          No reports yet. Once your doctor orders tests and they&apos;re processed, they&apos;ll appear here.
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((r) => (
            <div
              key={r.id}
              className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
                      <path d="M7 3h7l5 5v13H7z" />
                      <path d="M14 3v5h5" />
                      <path d="M9 13h6M9 17h6" strokeLinecap="round" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      Lab report - {r.id}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {r.doctorName} - {formatDate(r.createdAt)}
                    </p>
                    {r.tests?.length ? (
                      <p className="mt-2 text-xs text-slate-400">
                        Includes {r.tests.length} test{r.tests.length === 1 ? "" : "s"}
                      </p>
                    ) : null}
                  </div>
                </div>

                <a
                  href={r.url || `/reports/${r.id}`}
                  download
                  className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-sky-600 to-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-blue-200 transition hover:-translate-y-0.5"
                >
                  Download
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
