"use client";

import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-100 via-white to-cyan-100 flex items-center justify-center px-6">
      <div className="max-w-4xl w-full bg-white rounded-3xl shadow-2xl overflow-hidden grid md:grid-cols-2">
        <div className="bg-blue-700 text-white p-10 flex flex-col justify-center">
          <h1 className="text-5xl font-bold mb-6">Ally AI</h1>
          <p className="text-lg leading-8">
            Your intelligent hospital assistant for appointments,
            consultations, reports and healthcare guidance.
          </p>
        </div>

        <div className="p-10 flex flex-col justify-center">
          <h2 className="text-3xl font-bold text-gray-800">Welcome 👋</h2>
          <p className="text-gray-500 mt-3 mb-10">Continue to Ally AI</p>

          <button
            onClick={() => router.push("/login")}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl py-4 text-lg font-semibold"
          >
            Login
          </button>

          <button
            onClick={() => router.push("/signup")}
            className="mt-5 border-2 border-blue-600 text-blue-700 rounded-xl py-4 text-lg font-semibold hover:bg-blue-50"
          >
            Sign Up
          </button>
        </div>
      </div>
    </main>
  );
}