"use client";

import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_32%),radial-gradient(circle_at_top_right,_rgba(59,130,246,0.15),_transparent_30%),linear-gradient(180deg,_#f8fbff_0%,_#eef5fb_100%)] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-6xl items-center justify-center">
        <div className="grid w-full overflow-hidden rounded-[32px] border border-white/70 bg-white/90 shadow-[0_30px_100px_rgba(15,23,42,0.12)] backdrop-blur lg:grid-cols-[1.1fr_0.9fr]">
          <section className="relative overflow-hidden bg-gradient-to-br from-sky-600 via-blue-600 to-indigo-700 px-6 py-10 text-white sm:px-8 lg:px-10">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.18),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(255,255,255,0.12),transparent_24%)]" />
            <div className="relative z-10 flex h-full flex-col justify-between">
              <div>
                <div className="mb-8 flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 text-lg font-semibold shadow-lg shadow-black/10">
                    A
                  </div>
                  <div>
                    <p className="text-lg font-semibold tracking-tight">Ally AI</p>
                    <p className="text-sm text-white/80">Healthcare concierge</p>
                  </div>
                </div>

                <h1 className="max-w-xl text-4xl font-semibold tracking-tight sm:text-5xl">
                  A calmer way to manage care, appointments, and follow-up.
                </h1>
                <p className="mt-5 max-w-xl text-base leading-8 text-white/85 sm:text-lg">
                  Ally AI keeps the intake flow, chat experience, and report management in one polished healthcare workspace.
                </p>
              </div>

              <div className="mt-10 grid gap-3 sm:grid-cols-2">
                {[
                  "Cardiology-first patient intake",
                  "Guided chat with live appointment flow",
                  "Inbox, reports, and profile in one place",
                  "Built for fast re-entry after login",
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

          <section className="flex items-center px-5 py-6 sm:px-8 lg:px-10">
            <div className="mx-auto w-full max-w-md">
              <div className="mb-3 inline-flex rounded-full bg-sky-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">
                Welcome
              </div>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
                Start your healthcare journey
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-500 sm:text-base">
                Choose whether you want to sign in to an existing profile or create a new patient intake profile.
              </p>

              <div className="mt-8 space-y-4">
                <button
                  onClick={() => router.push("/login")}
                  className="inline-flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-200 transition hover:-translate-y-0.5"
                >
                  Login
                </button>

                <button
                  onClick={() => router.push("/signup")}
                  className="inline-flex w-full items-center justify-center rounded-2xl border border-slate-200 bg-white px-5 py-3.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-200 hover:text-sky-700"
                >
                  Sign up
                </button>
              </div>

              <div className="mt-8 rounded-3xl border border-slate-200 bg-slate-50 p-5">
                <p className="text-sm font-semibold text-slate-900">What you can do here</p>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                  <li>Book or continue appointments with cardiology support.</li>
                  <li>Review lab notifications and reports as they arrive.</li>
                  <li>Keep your patient details in one local profile.</li>
                </ul>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
