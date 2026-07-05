// No auth service exists in the backend — the WebSocket opens directly on
// /ws/{user_id}. This helper stores the patient's profile + health intake
// client-side and derives a stable user_id from their name.
//
// Two localStorage keys are used:
//  - STORAGE_KEY: the "current" profile, i.e. who is logged in right now.
//  - REGISTRY_KEY: every profile ever saved, keyed by email, so /login can
//    look someone up after a signup without needing a backend.

export interface PatientProfile {
  name: string;
  email: string;
  gender: string;
  age: string;
  phone: string;
  bloodGroup?: string;
  conditions?: string;
  medications?: string;
  allergies?: string;
  healthAssessment?: HealthAssessment;
  pastMedicalConditions?: string;
  patientId?: string;
}

export interface HealthAssessment {
  diabetes: boolean;
  hypertension: boolean;
  tobaccoUse: boolean;
  alcoholUse: boolean;
  currentMedications: boolean;
  heartDisease: boolean;
  heartProcedureHistory: boolean;
}

const STORAGE_KEY = "ally_patient_profile";
const REGISTRY_KEY = "ally_patient_registry";
const SESSION_KEY = "ally_session_id";
const SESSION_PATIENT_KEY = "ally_session_patient_id";

export function slugifyUserId(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return slug || "guest";
}

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

function readRegistry(): Record<string, PatientProfile> {
  if (typeof window === "undefined") return {};
  const raw = window.localStorage.getItem(REGISTRY_KEY);
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, PatientProfile>;
  } catch {
    return {};
  }
}

function writeRegistry(registry: Record<string, PatientProfile>): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(REGISTRY_KEY, JSON.stringify(registry));
}

/**
 * Saves the given profile as both the "current" session and, if it has an
 * email, into the registry so it can be looked up again later via login.
 */
export function saveProfile(profile: PatientProfile): void {
  if (typeof window === "undefined") return;

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));

  const email = normalizeEmail(profile.email || "");
  if (email) {
    const registry = readRegistry();
    registry[email] = profile;
    writeRegistry(registry);
  }
}

export function getProfile(): PatientProfile | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PatientProfile;
  } catch {
    return null;
  }
}

/**
 * Looks up a previously-signed-up profile by email. Used by /login.
 * Returns null if no profile with that email has ever been saved.
 */
export function findProfileByEmail(email: string): PatientProfile | null {
  const registry = readRegistry();
  return registry[normalizeEmail(email)] ?? null;
}

/**
 * Clears only the "current" session — the registry (and therefore the
 * ability to log back in later) is left untouched.
 */
export function clearProfile(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
  try {
    window.sessionStorage.removeItem(SESSION_KEY);
    window.sessionStorage.removeItem(SESSION_PATIENT_KEY);
  } catch {}
}

export function getUserId(): string | null {
  if (typeof window !== "undefined") {
    const patientId = window.sessionStorage.getItem(SESSION_PATIENT_KEY);
    if (patientId) return patientId;
  }
  const profile = getProfile();
  if (!profile) return null;
  if (profile.patientId) return profile.patientId;
  return slugifyUserId(profile.name);
}


export async function registerProfile(profile: PatientProfile): Promise<{ ok: boolean; patient_id?: string; session_id?: string; error?: string }> {
  if (typeof window === "undefined") return { ok: false, error: "client-only" };

  const client_user_id = getUserId();

  try {
    // Prefer direct backend URL when available (useful in Docker Compose),
    // otherwise fall back to the Next API proxy at `/api/auth/register`.
    const backendBase = (typeof window !== "undefined" && (window as any).NEXT_PUBLIC_BACKEND_URL) || process.env.NEXT_PUBLIC_BACKEND_URL || "";
    const target = backendBase ? `${backendBase.replace(/\/+$/,'')}/register` : "/api/auth/register";

    const resp = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: profile.name,
        age: Number(profile.age) || null,
        gender: profile.gender,
        phone: profile.phone,
        email: profile.email || null,
        city: undefined,
        emergency_contact: undefined,
        consent: true,
        client_user_id,
      }),
    });

    let data;
    const text = await resp.text();
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      return {
        ok: false,
        error: text || `Auth response was not valid JSON (status ${resp.status})`,
      };
    }

    if (!data || !data.ok) return { ok: false, error: data?.detail || "register failed" };
    // persist profile (without patientId) and store session identifiers transiently
    const next = { ...profile, patientId: data.patient_id || profile.patientId };
    saveProfile(next);
    try {
      window.sessionStorage.setItem(SESSION_KEY, data.session_id || "");
      window.sessionStorage.setItem(SESSION_PATIENT_KEY, data.patient_id || "");
    } catch {}
    return { ok: true, patient_id: data.patient_id, session_id: data.session_id };
  } catch (err: any) {
    return { ok: false, error: String(err) };
  }
}

export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}
