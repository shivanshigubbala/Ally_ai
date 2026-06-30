"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { saveProfile, type PatientProfile } from "@/lib/patient";

const EMPTY: PatientProfile = {
  name: "",
  email: "",
  age: "",
  phone: "",
  conditions: "",
  medications: "",
  allergies: "",
};

function Field({
  label,
  placeholder,
  value,
  onChange,
  required,
  type = "text",
}: {
  label: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  type?: string;
}) {
  return (
    <div className="mb-3.5">
      <label className="block text-xs text-gray-500 mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        required={required}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
      />
    </div>
  );
}

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState<PatientProfile>(EMPTY);

  const set = (key: keyof PatientProfile) => (v: string) =>
    setForm((prev) => ({ ...prev, [key]: v }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim()) return;
    saveProfile(form);
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
          Create your account to continue to your hospital assistant
        </p>

        <Field
          label="Full name"
          placeholder="Rohan Kapoor"
          value={form.name}
          onChange={set("name")}
          required
        />
        <Field
          label="Email"
          placeholder="rohan@example.com"
          value={form.email}
          onChange={set("email")}
          required
          type="email"
        />
        <Field
          label="Age"
          placeholder="34"
          value={form.age}
          onChange={set("age")}
        />
        <Field
          label="Phone number"
          placeholder="+91 98765 43210"
          value={form.phone}
          onChange={set("phone")}
        />

        <div className="h-px bg-gray-100 my-5" />

        <p className="text-sm font-medium text-gray-900 mb-3">
          Health details
        </p>
        <Field
          label="Known conditions"
          placeholder="e.g. hypertension, diabetes"
          value={form.conditions}
          onChange={set("conditions")}
        />
        <Field
          label="Current medications"
          placeholder="e.g. metformin 500mg"
          value={form.medications}
          onChange={set("medications")}
        />
        <Field
          label="Allergies"
          placeholder="e.g. penicillin"
          value={form.allergies}
          onChange={set("allergies")}
        />

        <button
          type="submit"
          className="w-full mt-2 bg-blue-600 text-white text-sm font-medium rounded-lg py-2.5 hover:bg-blue-700 transition"
        >
          Continue to Ally AI
        </button>

        <p className="text-xs text-gray-400 text-center mt-4">
          Your health information is used only to personalize your
          consultation.
        </p>

        <p className="text-sm text-gray-500 text-center mt-5">
          Already have an account?{" "}
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="text-blue-600 font-medium hover:underline"
          >
            Log in
          </button>
        </p>
      </form>
    </main>
  );
}