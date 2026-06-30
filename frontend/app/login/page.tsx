"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { saveProfile, findProfileByEmail } from "@/lib/patient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) return;

    const existing = findProfileByEmail(email);

    if (!existing) {
      setError("No account found for this email — redirecting you to sign up…");
      setTimeout(() => router.push("/signup"), 1200);
      return;
    }

    saveProfile(existing);
    router.push("/chat");
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 px-6 py-10">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md bg-white border border-gray-200 rounded-2xl p-8"
      >
        <div className="flex items-center justify-center gap-2 mb-1.5">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white text-sm font-semibold">
            A
          </div>
          <p className="text-lg font-semibold text-gray-900">Ally AI</p>
        </div>
        <p className="text-sm text-gray-500 text-center mb-6">
          Log in to continue to your hospital assistant
        </p>

        <div className="mb-3.5">
          <label className="block text-xs text-gray-500 mb-1.5">Email</label>
          <input
            type="email"
            value={email}
            required
            placeholder="rohan@example.com"
            onChange={(e) => setEmail(e.target.value)}
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>

        {error && (
          <p className="text-xs text-red-600 mb-3.5">{error}</p>
        )}

        <button
          type="submit"
          className="w-full mt-2 bg-blue-600 text-white text-sm font-medium rounded-lg py-2.5 hover:bg-blue-700 transition"
        >
          Continue to Ally AI
        </button>

        <p className="text-sm text-gray-500 text-center mt-5">
          Don&apos;t have an account?{" "}
          <button
            type="button"
            onClick={() => router.push("/signup")}
            className="text-blue-600 font-medium hover:underline"
          >
            Sign up
          </button>
        </p>
      </form>
    </main>
  );
}