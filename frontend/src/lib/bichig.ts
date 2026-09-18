import { convert } from "@gege-mn/gege-converter";

/** Cyrillic → traditional Mongolian script (Монгол бичиг). */
export function cyrillicToBichig(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "";
  try {
    return convert(text);
  } catch {
    return text;
  }
}

export type ScriptMode = "cyrillic" | "dual" | "bichig";
