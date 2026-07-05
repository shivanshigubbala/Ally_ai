"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { saveProfile, type HealthAssessment, type PatientProfile } from "@/lib/patient";

type AssessmentKey = keyof HealthAssessment;

const ASSESSMENT_QUESTIONS: Array<{ key: AssessmentKey; label: string }> = [
  { key: "diabetes", label: "Have you been diagnosed with Diabetes?" },
  {
    key: "hypertension",
    label: "Have you been diagnosed with High Blood Pressure (Hypertension)?",
  },
  { key: "tobaccoUse", label: "Do you smoke or use tobacco products?" },
  { key: "alcoholUse", label: "Do you consume alcohol regularly?" },
  { key: "currentMedications", label: "Are you currently taking any medications?" },
  { key: "heartDisease", label: "Have you ever been diagnosed with Heart Disease?" },
  {
    key: "heartProcedureHistory",
    label: "Have you ever had Heart Surgery, Angioplasty, or a Stent?",
  },
];

const EMPTY_PROFILE: PatientProfile = {
  name: "",
  email: "",
  gender: "",
  age: "",
  phone: "",
  bloodGroup: "",
  conditions: "",
  medications: "",
  allergies: "",
};

const EMPTY_ASSESSMENT: HealthAssessment = {
  diabetes: false,
  hypertension: false,
  tobaccoUse: false,
  alcoholUse: false,
  currentMedications: false,
  heartDisease: false,
  heartProcedureHistory: false,
};

function SectionTitle({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-4">
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h2>
      {subtitle ? <p className="mt-2 text-sm leading-6 text-slate-500">{subtitle}</p> : null}
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-cyan-300 focus:ring-4 focus:ring-cyan-100"
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  placeholder: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-cyan-300 focus:ring-4 focus:ring-cyan-100"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">{label}</span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={3}
        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-cyan-300 focus:ring-4 focus:ring-cyan-100"
      />
    </label>
  );
}

function YesNoRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <p className="text-sm font-medium leading-6 text-slate-900">{label}</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => onChange(false)}
          className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold transition ${
            !value
              ? "border-slate-300 bg-slate-100 text-slate-900"
              : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          <span className={`h-4 w-4 rounded border ${!value ? "border-slate-900 bg-slate-900" : "border-slate-300 bg-white"}`} />
          No
        </button>
        <button
          type="button"
          onClick={() => onChange(true)}
          className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold transition ${
            value
              ? "border-cyan-200 bg-cyan-50 text-cyan-700"
              : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          <span className={`h-4 w-4 rounded border ${value ? "border-cyan-600 bg-cyan-600" : "border-slate-300 bg-white"}`} />
          Yes
        </button>
      </div>
    </div>
  );
}

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState<PatientProfile>(EMPTY_PROFILE);
  const [error, setError] = useState("");
  const [consent, setConsent] = useState(false);

  const set = (key: keyof PatientProfile) => (value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!form.name.trim() || !form.phone.trim() || !form.gender.trim()) {
      setError("Please fill in your full name, phone, and gender to continue.");
      return;
    }

    if (!consent) {
      setError("Consent for AI consultation is required to register.");
      return;
    }

    setError("");
    // lazy import to avoid server-side issues
    try {
      const { registerProfile } = await import("@/lib/patient");
      const payload = { ...form };
      const res = await registerProfile(payload as any);
      if (!res.ok) {
        setError(res.error || "Registration failed");
        return;
      }
      // After registration, initialize session and open Ally directly (no login)
      router.push(`/chat`);
    } catch (err: any) {
      setError(String(err));
    }
  };

  return (
    <main className="min-h-screen bg-[#c9edf2] px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 shadow-[0_28px_90px_rgba(14,116,144,0.16)] backdrop-blur">
          <div className="border-b border-white/80 bg-[linear-gradient(180deg,#eefbfe_0%,#d9f2f7_100%)] px-5 py-5 sm:px-8 sm:py-6">
            <div className="inline-flex rounded-full bg-cyan-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-800">
              Ally AI
            </div>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Register with Ally AI.
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600 sm:text-base">
              Fill in the required details below, answer the health questions, then log in with the new email to continue.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6 p-5 sm:p-8">
            <section>
              <SectionTitle
                title="Register"
                subtitle="Provide basic identity details to start a consultation with Ally. No login or password required."
              />
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <TextField label="Full Name" value={form.name} onChange={set("name")} placeholder="Rohan Kapoor" />
                <TextField label="Age" value={form.age} onChange={set("age")} placeholder="34" />
                <SelectField
                  label="Gender"
                  value={form.gender}
                  onChange={set("gender")}
                  placeholder="Select gender"
                  options={["Male", "Female", "Other"]}
                />
                <TextField label="Phone Number" value={form.phone} onChange={set("phone")} placeholder="+91 98765 43210" />
                <TextField
                  label="City"
                  value={form.bloodGroup || ""}
                  onChange={set("bloodGroup")}
                  placeholder="City"
                />
                <TextField
                  label="Email (optional)"
                  value={form.email}
                  onChange={set("email")}
                  placeholder="rohan@example.com"
                  type="email"
                />
              </div>
            </section>

            <section>
              <SectionTitle title="Consent" subtitle="Required to proceed with AI-powered consultation." />
              <div className="flex items-start gap-3">
                <input id="consent" type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
                <label htmlFor="consent" className="text-sm text-slate-700">
                  I consent to using Ally AI for conversational triage and understand this is a prototype.
                </label>
              </div>
            </section>

            {error ? (
              <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </p>
            ) : null}

            <div className="flex flex-col gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <button
                type="submit"
                className="inline-flex w-full items-center justify-center rounded-2xl bg-[#1ea7c6] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_35px_rgba(30,167,198,0.28)] transition hover:-translate-y-0.5 sm:w-auto"
              >
                Save profile and go to login
              </button>

              <button
                type="button"
                onClick={() => router.push("/login")}
                className="text-sm font-semibold text-cyan-700 hover:underline"
              >
                Already have an account? Log in
              </button>
            </div>
          </form>
        </div>
      </div>
    </main>
  );
}
