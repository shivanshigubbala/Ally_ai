"use client";

import type { LabReport } from "@/types/chat";

interface LabReportsPanelProps {
  reports: LabReport[];
}

function formatDate(ts: number): string {
  return new Date(ts).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function LabReportsPanel({ reports }: LabReportsPanelProps) {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h1 className="text-base font-semibold text-gray-900 mb-4">
        Lab reports
      </h1>

      {reports.length === 0 ? (
        <p className="text-sm text-gray-500">
          No reports yet. Once your doctor orders tests and they&apos;re
          processed, they&apos;ll appear here.
        </p>
      ) : (
        <div className="space-y-3 max-w-lg">
          {reports.map((r) => (
            <div
              key={r.id}
              className="border border-gray-200 rounded-xl p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-700">
                  📄
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    Lab report - {r.id}
                  </p>
                  <p className="text-xs text-gray-500">
                    {r.doctorName} · {formatDate(r.createdAt)}
                  </p>
                </div>
              </div>
              <button
                disabled
                title="Backend doesn't expose a report download endpoint yet"
                className="text-xs font-medium px-3 py-1.5 rounded-lg bg-gray-100 text-gray-400 cursor-not-allowed"
              >
                Download
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
