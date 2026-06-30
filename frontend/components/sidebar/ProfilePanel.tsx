"use client";

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

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-3 border-b border-gray-100">
      <span className="text-gray-500 text-sm">{label}</span>
      <span className="font-medium text-gray-900">{value || "—"}</span>
    </div>
  );
}

export default function ProfilePanel({
  profile,
  reports = [],
  onLogout,
}: ProfilePanelProps) {
  if (!profile) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p>No profile found.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
      <h1 className="text-base font-semibold text-gray-900 mb-4">Profile</h1>

      <div className="max-w-lg border border-gray-200 rounded-xl p-5 bg-white">
        <Row label="Full name" value={profile.name} />
        <Row label="Gender" value={profile.gender} />
        <Row label="Age" value={profile.age} />
        <Row label="Phone" value={profile.phone} />
        <Row label="Known Conditions" value={profile.conditions} />
        <Row label="Medications" value={profile.medications} />
        <Row label="Allergies" value={profile.allergies} />
      </div>

      <div className="bg-white rounded-xl shadow p-6 mt-6">
        <h2 className="text-xl font-semibold mb-4">Medical Reports</h2>

        {reports.length === 0 ? (
          <p className="text-gray-500">No reports available.</p>
        ) : (
          <div className="space-y-3">
            {reports.map((report, index) => (
              <div key={report.id ?? index} className="border rounded-lg p-3">
                <div className="font-medium">
                  {report.testName ?? report.name ?? `Report ${index + 1}`}
                </div>
                <div className="text-sm text-gray-500">{report.status ?? "Completed"}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow p-6 mt-6">
        <h2 className="text-xl font-semibold mb-4">Previous Consultations</h2>
        <p className="text-gray-500">Consultation history will appear here.</p>
      </div>

      <button
        onClick={onLogout}
        className="mt-8 w-full bg-red-600 hover:bg-red-700 text-white py-3 rounded-xl font-semibold transition"
      >
        Logout
      </button>
    </div>
  );
}