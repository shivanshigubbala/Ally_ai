"use client";

interface ChatHeaderProps {
  connected: boolean;
  doctorName: string | null;
}

export default function ChatHeader({ connected, doctorName }: ChatHeaderProps) {
  return (
    <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200">
      <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-sm font-semibold">
        {doctorName ? "MD" : "A"}
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-900">
          {doctorName || "Ally · Hospital receptionist"}
        </p>
        <p className="text-xs flex items-center gap-1.5 text-gray-500">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected ? "bg-green-500" : "bg-gray-300"
            }`}
          />
          {connected ? "Online" : "Connecting..."}
        </p>
      </div>
    </div>
  );
}