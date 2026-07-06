"use client";

import { useState } from "react";
import { getBackendBase } from "@/lib/backend";

export default function SettingsPanel() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleFlush = async () => {
    if (!confirm("Are you sure you want to flush all databases and reset the application to its original state? This deletes all chats, appointments, and generated lab reports!")) {
      return;
    }
    setLoading(true);
    setMessage("");
    setError("");

    try {
      const backendBase = getBackendBase();
      const target = backendBase ? `${backendBase.replace(/\/+$/, "")}/reset-db` : "/api/reset-db";

      const resp = await fetch(target, {
        method: "POST",
      });

      const text = await resp.text();
      let data;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        // fallback
      }

      if (resp.ok) {
        setMessage("Database tables successfully flushed and re-seeded! All time slots are now available.");
        // Clear local storage state too to match
        localStorage.clear();
        sessionStorage.clear();
        setTimeout(() => {
          window.location.href = "/signup";
        }, 3000);
      } else {
        const errorMsg = data?.detail
          ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))
          : (text || "Failed to reset database");
        setError(errorMsg);
      }
    } catch (err: any) {
      setError(err?.message || "Connection error failed to reset database");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900 font-sans">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage system configurations and developer controls.
        </p>
      </div>

      <div className="max-w-2xl space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Developer Actions</h2>
          <p className="mt-1 text-sm text-slate-500">
            Reset the system state to start a clean session.
          </p>

          <div className="mt-5 border-t border-slate-100 pt-5">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">Flush Application Databases</p>
                <p className="mt-1 text-xs text-slate-500 max-w-md">
                  Deletes all appointments, chat messages, uploaded files, timeline entries, and generated PDFs. Re-seeds doctors and makes all slots open.
                </p>
              </div>
              <button
                onClick={handleFlush}
                disabled={loading}
                className={`inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-rose-600 to-red-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-rose-100 transition hover:-translate-y-0.5 disabled:opacity-50 disabled:pointer-events-none`}
              >
                {loading ? "Flushing..." : "Flush & Reset DB"}
              </button>
            </div>
          </div>

          {message && (
            <div className="mt-4 rounded-2xl bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-800 animate-fade-in">
              <p className="font-semibold">Success</p>
              <p className="mt-1 text-xs">{message}</p>
              <p className="mt-2 text-xs font-medium text-emerald-700">Redirecting to signup in 3 seconds...</p>
            </div>
          )}

          {error && (
            <div className="mt-4 rounded-2xl bg-rose-50 border border-rose-200 p-4 text-sm text-rose-800">
              <p className="font-semibold">Error</p>
              <p className="mt-1 text-xs">{error}</p>
            </div>
          )}
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white/60 p-6 shadow-sm backdrop-blur">
          <h2 className="text-base font-semibold text-slate-900">Department Autonomy Status</h2>
          <p className="mt-1 text-sm text-slate-500">
            Specialty departments are decoupled and configured independently.
          </p>

          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white/80 p-3 text-xs">
              <span className="font-semibold text-slate-700">General Medicine (Dr. Shankar Dada)</span>
              <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-emerald-700 font-medium">Independent</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white/80 p-3 text-xs">
              <span className="font-semibold text-slate-700">Cardiology (Dr. Arjun Reddy)</span>
              <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-emerald-700 font-medium">Independent</span>
            </div>
            <div className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white/80 p-3 text-xs">
              <span className="font-semibold text-slate-700">Neurology (Dr. Octopus)</span>
              <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-emerald-700 font-medium">Independent</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
