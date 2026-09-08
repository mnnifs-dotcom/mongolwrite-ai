import type { CheckResponse, ImproveResponse, SettingsResponse } from "./types";

function apiUrl(path: string): string {
  if (typeof window !== "undefined") return path;
  return `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}${path}`;
}

export async function checkText(
  text: string,
  options?: { document_type?: string; style?: string; signal?: AbortSignal },
): Promise<CheckResponse> {
  return postCheck("/api/v1/check/deterministic", text, options);
}

export async function checkTextWithAI(
  text: string,
  options?: { document_type?: string; style?: string; signal?: AbortSignal },
): Promise<CheckResponse> {
  return postCheck("/api/v1/check/all", text, options);
}

async function postCheck(
  path: string,
  text: string,
  options?: { document_type?: string; style?: string; signal?: AbortSignal },
): Promise<CheckResponse> {
  const body = JSON.stringify({
    text,
    document_type: options?.document_type ?? "official_letter",
    style: options?.style ?? "government_official",
  });
  let lastError: Error | null = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetch(apiUrl(path), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        signal: options?.signal,
      });
      if (response.ok) {
        return response.json() as Promise<CheckResponse>;
      }
      lastError = new Error(
        response.status === 422
          ? "Текст хэт урт байна. Нэг дор 100 мянган тэмдэгт хүртэл шалгана."
          : response.status >= 500
            ? "Шалгалт түр саатав."
            : `Шалгалт амжилтгүй (${response.status})`,
      );
      if (response.status < 500) break;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") throw err;
      if (err instanceof Error && err.name === "AbortError") throw err;
      lastError = err instanceof Error ? err : new Error("Холбогдсонгүй");
    }
    if (options?.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw lastError ?? new Error("Шалгалт амжилтгүй");
}

export async function improveText(
  text: string,
  options?: { document_type?: string; style?: string },
): Promise<ImproveResponse> {
  const response = await fetch(apiUrl("/api/v1/check/improve"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      document_type: options?.document_type ?? "official_letter",
      style: options?.style ?? "government_official",
    }),
  });
  if (!response.ok) {
    throw new Error(`Сайжруулалт амжилтгүй (${response.status})`);
  }
  return response.json() as Promise<ImproveResponse>;
}

export async function importDocument(file: File): Promise<{ filename: string; text: string }> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(apiUrl("/api/v1/import/file"), {
    method: "POST",
    body,
  });
  if (!response.ok) {
    throw new Error("Файлыг уншиж чадсангүй");
  }
  return response.json() as Promise<{ filename: string; text: string }>;
}

export async function learnFromText(text: string): Promise<{ added: string[]; added_count: number }> {
  const response = await fetch(apiUrl("/api/v1/dictionary/learn"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw new Error("Тольд нэмж чадсангүй");
  }
  return response.json() as Promise<{ added: string[]; added_count: number }>;
}

export async function getSettings(): Promise<SettingsResponse> {
  const response = await fetch(apiUrl("/api/v1/settings"));
  if (!response.ok) {
    return { ai_enabled: false };
  }
  return response.json() as Promise<SettingsResponse>;
}

export async function saveAiKey(key: string): Promise<SettingsResponse> {
  const response = await fetch(apiUrl("/api/v1/settings/ai-key"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key }),
  });
  if (!response.ok) {
    throw new Error("Түлхүүр хадгалж чадсангүй");
  }
  return response.json() as Promise<SettingsResponse>;
}

export async function addDictionaryWords(
  words: string[],
): Promise<{ added: string[]; added_count: number }> {
  const response = await fetch(apiUrl("/api/v1/dictionary/words"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words }),
  });
  if (!response.ok) {
    throw new Error("Үг нэмж чадсангүй");
  }
  return response.json() as Promise<{ added: string[]; added_count: number }>;
}
