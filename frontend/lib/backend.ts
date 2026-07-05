export function getBackendBase(): string {
  if (typeof window !== "undefined") {
    const explicit = (window as any).NEXT_PUBLIC_BACKEND_URL;
    if (typeof explicit === "string" && explicit.trim()) {
      return explicit.replace(/\/+$|\s+$/g, "");
    }

    const location = window.location;
    const host = location.hostname || "localhost";
    const protocol = location.protocol === "https:" ? "https:" : "http:";
    return `${protocol}//${host}:8000`;
  }

  return process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/g, "") || "http://localhost:8000";
}

export function getWsBase(): string {
  const backendBase = getBackendBase();
  if (backendBase.startsWith("https://")) {
    return backendBase.replace(/^https:/, "wss:");
  }
  return backendBase.replace(/^http:/, "ws:");
}
