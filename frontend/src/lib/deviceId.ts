/** Stable per-browser device id for the 2-device account limit. */

const STORAGE_KEY = "mw_device_id";

function randomId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID().replace(/-/g, "");
  }
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i += 1) bytes[i] = Math.floor(Math.random() * 256);
  }
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function getDeviceId(): string {
  if (typeof window === "undefined") return "ssr-placeholder-device";
  try {
    const existing = window.localStorage.getItem(STORAGE_KEY);
    if (existing && /^[A-Za-z0-9_-]{8,128}$/.test(existing)) return existing;
    const created = randomId();
    window.localStorage.setItem(STORAGE_KEY, created);
    return created;
  } catch {
    return randomId();
  }
}

export const DEVICE_HEADER = "X-MW-Device-Id";

export function deviceHeaders(): Record<string, string> {
  return { [DEVICE_HEADER]: getDeviceId() };
}
