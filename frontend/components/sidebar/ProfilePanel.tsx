"use client";

import type { ReactNode } from "react";
import type { PatientProfile } from "@/lib/patient";

interface Report {
  id?: string;
  testName?: string;
  name?: string;
  status?: string;
}

interface ProfilePanelProps {
  profile: PatientProfile | null;
  reports?: Report[];
  onLogout?: () => void;
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-900">{value || "-"}</span>
    </div>
  );
}

function Pill({ children, active }: { children: ReactNode; active: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
        active
          ? "bg-emerald-100 text-emerald-700"
          : "bg-slate-100 text-slate-500"
      }`}
    >
      {children}
    </span>
  );
}

export default function ProfilePanel({
  profile,
  reports = [],
  onLogout,
}: ProfilePanelProps) {
  if (!profile) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <p className="text-sm text-slate-500">No profile found.</p>
      </div>
    );
  }

  const assessment = profile.healthAssessment;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
      <div className="mb-5">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">Profile</h1>
        <p className="mt-1 text-sm text-slate-500">
          Your saved health intake details and consultation history.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 via-blue-600 to-indigo-600 text-sm font-semibold text-white">
                {profile.name
                  .split(" ")
                  .filter(Boolean)
                  .slice(0, 2)
                  .map((part) => part[0])
                  .join("") || "P"}
              </div>
              <div>
                <p className="text-base font-semibold text-slate-900">{profile.name}</p>
                <p className="text-sm text-slate-500">{profile.email}</p>
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              <Row label="Gender" value={profile.gender} />
              <Row label="Age" value={profile.age} />
              <Row label="Phone" value={profile.phone} />
              <Row label="Blood group" value={profile.bloodGroup || ""} />
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-slate-900">Medical history</h2>
              <p className="mt-1 text-sm text-slate-500">
                The health information you shared during signup.
              </p>
            </div>

            <div className="space-y-2">
              <Row label="Past medical conditions" value={profile.conditions} />
              <Row label="Current medications" value={profile.medications} />
              <Row label="Known allergies" value={profile.allergies} />
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-slate-900">Consultation history</h2>
              <p className="mt-1 text-sm text-slate-500">
                Previous consultations will appear here as they become available.
              </p>
            </div>

            {reports.length === 0 ? (
              <p className="text-sm text-slate-500">No reports available yet.</p>
            ) : (
              <div className="space-y-3">
                {reports.map((report, index) => (
                  <div
                    key={report.id ?? index}
                    className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
                  >
                    <div className="font-medium text-slate-900">
                      {report.testName ?? report.name ?? `Report ${index + 1}`}
                    </div>
                    <div className="mt-1 text-sm text-slate-500">
                      {report.status ?? "Completed"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="space-y-4">
          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-slate-900">Health assessment</h2>
              <p className="mt-1 text-sm text-slate-500">
                Quick yes/no answers from your intake form.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Pill active={Boolean(assessment?.diabetes)}>Diabetes</Pill>
              <Pill active={Boolean(assessment?.hypertension)}>Hypertension</Pill>
              <Pill active={Boolean(assessment?.tobaccoUse)}>Tobacco use</Pill>
              <Pill active={Boolean(assessment?.alcoholUse)}>Alcohol use</Pill>
              <Pill active={Boolean(assessment?.currentMedications)}>Medications</Pill>
              <Pill active={Boolean(assessment?.heartDisease)}>Heart disease</Pill>
              <Pill active={Boolean(assessment?.heartProcedureHistory)}>
                Heart procedure
              </Pill>
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900">Current details</h2>
            <div className="mt-3 space-y-1">
              <Row label="Blood group" value={profile.bloodGroup || ""} />
              <Row label="Email" value={profile.email} />
              <Row label="Phone" value={profile.phone} />
            </div>
          </section>

          <button
            onClick={onLogout}
            className="inline-flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-rose-600 to-red-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-rose-200 transition hover:-translate-y-0.5"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  );
}
