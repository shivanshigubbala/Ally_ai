"use client";

interface AppointmentsPanelProps {
  doctorName: string | null;
  booked: boolean;
}

export default function AppointmentsPanel({
  doctorName,
  booked,
}: AppointmentsPanelProps) {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h1 className="text-base font-semibold text-gray-900 mb-4">
        Appointments
      </h1>

      {!booked ? (
        <p className="text-sm text-gray-500">
          No appointments yet. Chat with Ally to get booked in.
        </p>
      ) : (
        <div className="max-w-lg border border-gray-200 rounded-xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center text-green-700">
            ✓
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">
              {doctorName || "Doctor"}
            </p>
            <p className="text-xs text-gray-500">Status: confirmed</p>
          </div>
        </div>
      )}
    </div>
  );
}