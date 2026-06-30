"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  saveProfile,
  type HealthAssessment,
  type PatientProfile,
} from "@/lib/patient";

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

type ToggleQuestionKey = keyof HealthAssessment;

const ASSESSMENT_QUESTIONS: Array<{
  key: ToggleQuestionKey;
  label: string;
  description: string;
}> = [
  {
    key: "diabetes",
    label: "Have you been diagnosed with Diabetes?",
    description: "Useful for medication and care planning.",
  },
  {
    key: "hypertension",
    label: "Have you been diagnosed with High Blood Pressure (Hypertension)?",
    description: "Helps the care team watch your blood pressure history.",
  },
  {
    key: "tobaccoUse",
    label: "Do you smoke or use tobacco products?",
    description: "Important for heart and respiratory risk assessment.",
  },
  {
    key: "alcoholUse",
    label: "Do you consume alcohol regularly?",
    description: "Supports safer advice around medications and recovery.",
  },
  {
    key: "currentMedications",
    label: "Are you currently taking any medications?",
    description: "So the doctor can review possible interactions.",
  },
  {
    key: "heartDisease",
    label: "Have you ever been diagnosed with Heart Disease?",
    description: "Useful for cardiology triage and prioritisation.",
  },
  {
    key: "heartProcedureHistory",
    label: "Have you ever had Heart Surgery, Angioplasty, or a Stent?",
    description: "Helps the team understand prior cardiac interventions.",
  },
];

function FieldShell({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {hint ? <span className="mt-2 block text-xs text-slate-400">{hint}</span> : null}
    </label>
  );
}

function TextInput({
  label,
  value,
  onChange,
  placeholder,
  required,
  type = "text",
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  required?: boolean;
  type?: string;
  hint?: string;
}) {
  return (
    <FieldShell label={label} hint={hint}>
      <input
        type={type}
        value={value}
        required={required}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-sky-300 focus:bg-white focus:ring-4 focus:ring-sky-100"
      />
    </FieldShell>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder: string;
  required?: boolean;
}) {
  return (
    <FieldShell label={label}>
      <select
        value={value}
        required={required}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-4 focus:ring-sky-100"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
  rows = 4,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  rows?: number;
  hint?: string;
}) {
  return (
    <FieldShell label={label} hint={hint}>
      <textarea
        value={value}
        rows={rows}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-sky-300 focus:bg-white focus:ring-4 focus:ring-sky-100"
      />
    </FieldShell>
  );
}

function ToggleQuestion({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description: string;
  value: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="mb-4">
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => onChange(false)}
          className={`rounded-2xl border px-4 py-2.5 text-sm font-semibold transition ${
            value
              ? "border-slate-200 bg-slate-50 text-slate-500"
              : "border-sky-200 bg-sky-50 text-sky-700 shadow-sm"
          }`}
        >
          No
        </button>
        <button
          type="button"
          onClick={() => onChange(true)}
          className={`rounded-2xl border px-4 py-2.5 text-sm font-semibold transition ${
            value
              ? "border-sky-200 bg-gradient-to-r from-sky-600 to-blue-600 text-white shadow-lg shadow-blue-200"
              : "border-slate-200 bg-slate-50 text-slate-600"
          }`}
        >
          Yes
        </button>
      </div>
    </div>
  );
}

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState<PatientProfile>(EMPTY_PROFILE);
  const [assessment, setAssessment] = useState<HealthAssessment>(EMPTY_ASSESSMENT);
  const [error, setError] = useState("");

  const set = (key: keyof PatientProfile) => (v: string) =>
    setForm((prev) => ({ ...prev, [key]: v }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.gender.trim()) {
      setError("Please fill in your full name, email, and gender to continue.");
      return;
    }

    setError("");
    saveProfile({
      ...form,
      healthAssessment: assessment,
    });
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
                <p className="text-sm text-white/80">Cardiology intake and care coordination</p>
              </div>
            </div>

            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Create your health profile in one calm, guided flow.
            </h1>
            <p className="mt-5 max-w-lg text-base leading-8 text-white/85 sm:text-lg">
              Share the key clinical details your care team needs so your consultation, appointments, and follow-up are ready from the start.
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {[
                "Modern healthcare intake",
                "Secure local session storage",
                "Assessment and medical history",
                "Seamless chat handoff",
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

        <form
          onSubmit={handleSubmit}
          className="flex min-h-0 flex-col overflow-y-auto px-5 py-6 sm:px-8 lg:px-10"
        >
          <div className="mx-auto w-full max-w-3xl">
            <div className="mb-8">
              <div className="mb-3 flex items-center gap-2">
                <span className="inline-flex rounded-full bg-sky-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">
                  Health details
                </span>
                <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                  Step 1 of 1
                </span>
              </div>
              <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                Tell us about your health profile
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500 sm:text-base">
                The information below helps Ally AI personalize your care recommendations while keeping your current workflow intact.
              </p>
            </div>

            <div className="space-y-8">
              <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5">
                  <h3 className="text-base font-semibold text-slate-900">Account details</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    We still use your email to sign you back in later.
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <TextInput
                    label="Full name"
                    placeholder="Rohan Kapoor"
                    value={form.name}
                    onChange={set("name")}
                    required
                  />
                  <TextInput
                    label="Email"
                    placeholder="rohan@example.com"
                    value={form.email}
                    onChange={set("email")}
                    required
                    type="email"
                  />
                </div>
              </section>

              <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5">
                  <h3 className="text-base font-semibold text-slate-900">Additional information</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Core demographic and contact details for your care team.
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <TextInput
                    label="Age"
                    placeholder="34"
                    value={form.age}
                    onChange={set("age")}
                  />
                  <SelectField
                    label="Gender"
                    placeholder="Select gender"
                    value={form.gender}
                    onChange={set("gender")}
                    options={["Male", "Female", "Other"]}
                    required
                  />
                  <TextInput
                    label="Phone number"
                    placeholder="+91 98765 43210"
                    value={form.phone}
                    onChange={set("phone")}
                  />
                  <SelectField
                    label="Blood group"
                    placeholder="Select blood group"
                    value={form.bloodGroup || ""}
                    onChange={set("bloodGroup")}
                    options={["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]}
                  />
                </div>
              </section>

              <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5">
                  <h3 className="text-base font-semibold text-slate-900">Health assessment</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Quick yes/no answers that help the cardiology team prepare.
                  </p>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  {ASSESSMENT_QUESTIONS.map((question) => (
                    <ToggleQuestion
                      key={question.key}
                      label={question.label}
                      description={question.description}
                      value={assessment[question.key]}
                      onChange={(next) =>
                        setAssessment((prev) => ({ ...prev, [question.key]: next }))
                      }
                    />
                  ))}
                </div>
              </section>

              <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5">
                  <h3 className="text-base font-semibold text-slate-900">Medical history</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Add the details that are most helpful for your care plan.
                  </p>
                </div>

                <div className="grid gap-4">
                  <TextAreaField
                    label="Known allergies"
                    placeholder="e.g. penicillin, pollen, peanuts"
                    value={form.allergies}
                    onChange={set("allergies")}
                    hint="List anything your care team should avoid."
                  />
                  <TextAreaField
                    label="Current medications"
                    placeholder="e.g. metformin 500mg, aspirin, vitamin D"
                    value={form.medications}
                    onChange={set("medications")}
                    hint="Include dosage if you know it."
                  />
                  <TextAreaField
                    label="Past medical conditions"
                    placeholder="e.g. hypertension, diabetes, asthma, prior surgeries"
                    value={form.conditions}
                    onChange={set("conditions")}
                    hint="This helps the team understand your background."
                  />
                </div>
              </section>
            </div>

            {error ? (
              <p className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </p>
            ) : null}

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                type="submit"
                className="inline-flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-200 transition hover:-translate-y-0.5 sm:w-auto"
              >
                Save profile and continue
              </button>
              <p className="text-xs leading-5 text-slate-400 sm:max-w-lg">
                Your health information is used only to personalize your consultation and is stored locally in this demo flow.
              </p>
            </div>

            <p className="mt-6 text-center text-sm text-slate-500">
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => router.push("/login")}
                className="font-semibold text-sky-700 hover:underline"
              >
                Log in
              </button>
            </p>
          </div>
        </form>
      </div>
    </main>
  );
}
