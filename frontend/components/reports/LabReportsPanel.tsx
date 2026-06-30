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

export default function LabReportsPanel({ reports, onAddSampleReport }: LabReportsPanelProps) {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h1 className="text-base font-semibold text-gray-900 mb-4">
        Lab reports
      </h1>

      {typeof (onAddSampleReport) !== "undefined" && (
        <div className="mb-4">
          <button
            onClick={onAddSampleReport}
            className="text-xs font-medium px-3 py-1 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
          >
            Add sample report
          </button>
        </div>
      )}

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
              <a
                href={r.url || `/reports/${r.id}`}
                download
                className="text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700"
              >
                Download
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
