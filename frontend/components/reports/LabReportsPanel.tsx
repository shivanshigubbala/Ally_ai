"use client";

import { useState } from "react";
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

export default function LabReportsPanel({
  reports,
}: LabReportsPanelProps) {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleDownload = async (url: string, reportId: string) => {
    setDownloadingId(reportId);
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error("Network response was not ok");
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      const cleanId = reportId.replace(/[^A-Za-z0-9_\-]+/g, "_");
      link.download = `lab_report_${cleanId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      // CORS or fetch fallback: open in new tab
      window.open(url, "_blank");
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 sm:px-6 py-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Lab reports</h1>
          <p className="mt-1 text-sm text-slate-500">
            View completed tests and download available results.
          </p>
        </div>
      </div>

      {reports.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-200 bg-white/90 p-8 text-sm text-slate-500 shadow-sm">
          No reports yet. Once your doctor orders tests and they&apos;re processed, they&apos;ll appear here.
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((r) => {
            const isGenerating = r.status === "generating";
            return (
              <div
                key={r.id}
                className={`rounded-3xl border p-4 shadow-sm transition ${
                  isGenerating
                    ? "border-amber-200 bg-amber-50/40 animate-pulse"
                    : "border-slate-200 bg-white hover:-translate-y-0.5 hover:shadow-md"
                }`}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-4">
                    <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${
                      isGenerating ? "bg-amber-100 text-amber-700" : "bg-sky-100 text-sky-700"
                    }`}>
                      {isGenerating ? (
                        <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
                          <path d="M7 3h7l5 5v13H7z" />
                          <path d="M14 3v5h5" />
                          <path d="M9 13h6M9 17h6" strokeLinecap="round" />
                        </svg>
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {isGenerating ? "Analyzing & Generating Report..." : `Lab report - ${r.id}`}
                      </p>
                      <p className="mt-1 text-sm text-slate-500">
                        {r.doctorName} - {isGenerating ? "Processing" : formatDate(r.createdAt)}
                      </p>
                      {isGenerating ? (
                        <p className="mt-2 text-xs text-amber-600 font-medium">
                          Simulating medical lab diagnostic tests...
                        </p>
                      ) : r.tests?.length ? (
                        <p className="mt-2 text-xs text-slate-400">
                          Includes {r.tests.length} test{r.tests.length === 1 ? "" : "s"}
                        </p>
                      ) : null}
                    </div>
                  </div>

                  {!isGenerating ? (
                    <button
                      onClick={() => handleDownload(r.url || `/reports/${r.id}`, r.id)}
                      disabled={downloadingId === r.id}
                      className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-sky-600 to-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-blue-200 transition hover:-translate-y-0.5 disabled:opacity-50 disabled:pointer-events-none"
                    >
                      {downloadingId === r.id ? "Downloading..." : "Download"}
                    </button>
                  ) : (
                    <div className="inline-flex items-center gap-1.5 rounded-2xl bg-amber-100/50 px-3.5 py-2 text-xs font-semibold text-amber-700">
                      Pending Results
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
