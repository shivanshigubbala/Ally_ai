"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { saveProfile, findProfileByEmail } from "@/lib/patient";

function CardShell({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      {children}
    </div>
  );
}

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
      setError("No account found for this email. Redirecting you to sign up...");
      setTimeout(() => router.push("/signup"), 1200);
      return;
    }

    saveProfile(existing);
    router.push("/chat");
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_32%),radial-gradient(circle_at_top_right,_rgba(59,130,246,0.15),_transparent_30%),linear-gradient(180deg,_#f8fbff_0%,_#eef5fb_100%)] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-7xl overflow-hidden rounded-[32px] border border-white/70 bg-white/90 shadow-[0_30px_100px_rgba(15,23,42,0.12)] backdrop-blur lg:grid-cols-[0.92fr_1.08fr]">
        <section className="relative flex items-center overflow-hidden bg-gradient-to-br from-sky-600 via-blue-600 to-indigo-700 px-6 py-10 text-white sm:px-8 lg:px-10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.18),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(255,255,255,0.12),transparent_24%)]" />
          <div className="relative z-10 max-w-xl">
            <div className="mb-8 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 text-lg font-semibold shadow-lg shadow-black/10">
                A
              </div>
              <div>
                <p className="text-lg font-semibold tracking-tight">Ally AI</p>
                <p className="text-sm text-white/80">Secure patient access</p>
              </div>
            </div>

            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Welcome back to your care workspace.
            </h1>
            <p className="mt-5 max-w-lg text-base leading-8 text-white/85 sm:text-lg">
              Sign in with your email to continue the exact same healthcare flow, chat history, and appointment journey.
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {[
                "Reopen your patient profile",
                "Return to ongoing consultations",
                "View inbox and lab updates",
                "Keep the same local session",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm font-medium text-white/90 shadow-sm"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        </section>

        <div className="flex min-h-0 flex-col justify-center px-5 py-6 sm:px-8 lg:px-10">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-8">
              <div className="mb-3 flex items-center gap-2">
                <span className="inline-flex rounded-full bg-sky-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">
                  Sign in
                </span>
              </div>
              <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                Continue with your email
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500 sm:text-base">
                We&apos;ll look up the profile you created during signup and bring you right back in.
              </p>
            </div>

            <CardShell>
              <form onSubmit={handleSubmit} className="space-y-5">
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-700">Email</span>
                  <input
                    type="email"
                    value={email}
                    required
                    placeholder="rohan@example.com"
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-sky-300 focus:bg-white focus:ring-4 focus:ring-sky-100"
                  />
                </label>

                {error && (
                  <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  className="inline-flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-200 transition hover:-translate-y-0.5"
                >
                  Continue to Ally AI
                </button>
              </form>
            </CardShell>

            <p className="mt-6 text-center text-sm text-slate-500">
              Don&apos;t have an account?{" "}
              <button
                type="button"
                onClick={() => router.push("/signup")}
                className="font-semibold text-sky-700 hover:underline"
              >
                Sign up
              </button>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
