"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import AuthShell from "@/components/auth/AuthShell";
import { findProfileByEmail, saveProfile } from "@/lib/patient";

export default function LoginPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const prefill = searchParams.get("email");
    if (prefill) setEmail(prefill);
  }, [searchParams]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("Please enter the email you used to register.");
      return;
    }

    try {
      const { loginProfile } = await import("@/lib/patient");
      const res = await loginProfile(email);

      if (!res.ok) {
        setError(res.error || "Login failed");
        return;
      }

      router.push("/chat");
    } catch (err: any) {
      setError(String(err));
    }
  };

  return (
    <AuthShell
      title="Welcome to Ally AI."
      description="Sign in to continue your AI-powered healthcare journey, manage appointments, and stay connected with your trusted virtual healthcare assistant"
      panelTitle="Welcome back"
      panelDescription="Use the email you registered with to continue where you left off."
      panelChildren={
        <form onSubmit={handleSubmit} className="space-y-5">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Email</span>
            <input
              type="email"
              value={email}
              required
              placeholder="rohan@example.com"
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-cyan-300 focus:bg-white focus:ring-4 focus:ring-cyan-100"
            />
          </label>

          {error && (
            <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="inline-flex w-full items-center justify-center rounded-2xl bg-[#1ea7c6] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_35px_rgba(30,167,198,0.28)] transition hover:-translate-y-0.5"
          >
            Continue to Ally AI
          </button>
        </form>
      }
      footer={
        <p className="text-center text-sm text-slate-500">
          New here?{" "}
          <button
            type="button"
            onClick={() => router.push("/signup")}
            className="font-semibold text-cyan-700 hover:underline"
          >
            Register
          </button>
        </p>
      }
    />
  );
}
