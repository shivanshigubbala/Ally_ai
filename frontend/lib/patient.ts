// No auth service exists in the backend — the WebSocket opens directly on
// /ws/{user_id}. This helper stores the patient's profile + health intake
// client-side and derives a stable user_id from their name.

export interface PatientProfile {
  name: string;
  age: string;
  phone: string;
  conditions: string;
  medications: string;
  allergies: string;
}

const STORAGE_KEY = "ally_patient_profile";

export function slugifyUserId(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return slug || "guest";
}

export function saveProfile(profile: PatientProfile): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
}

export function getProfile(): PatientProfile | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PatientProfile;
  } catch {
    return null;
  }
}

export function clearProfile(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(STORAGE_KEY);
}

export function getUserId(): string | null {
  const profile = getProfile();
  return profile ? slugifyUserId(profile.name) : null;
}

export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}