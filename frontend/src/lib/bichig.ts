import { convert } from "@gege-mn/gege-converter";

/** Cyrillic → traditional Mongolian script. */
export function cyrillicToBichig(text: string): string {
  if (!text.trim()) return "";
  try {
    return convert(text);
  } catch {
    return text;
  }
}
