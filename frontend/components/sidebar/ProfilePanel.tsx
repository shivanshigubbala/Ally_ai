"use client";

import type { PatientProfile } from "@/lib/patient";

interface ProfilePanelProps {
  profile: PatientProfile | null;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-100 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-sm text-gray-900">{value || "—"}</span>
    </div>
  );
}

export default function ProfilePanel({ profile }: ProfilePanelProps) {
  if (!profile) {
    return (
      <div className="flex-1 overflow-y-auto p-6">
        <p className="text-sm text-gray-500">No profile found.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h1 className="text-base font-semibold text-gray-900 mb-4">Profile</h1>
      <div className="max-w-lg border border-gray-200 rounded-xl p-5">
        <Row label="Full name" value={profile.name} />
        <Row label="Age" value={profile.age} />
        <Row label="Phone number" value={profile.phone} />
        <Row label="Known conditions" value={profile.conditions} />
        <Row label="Current medications" value={profile.medications} />
        <Row label="Allergies" value={profile.allergies} />
      </div>
      <p className="text-xs text-gray-400 mt-3 max-w-lg">
        Stored locally in this browser session — the backend doesn&apos;t yet
        have a profile endpoint to persist this.
      </p>
    </div>
  );
}