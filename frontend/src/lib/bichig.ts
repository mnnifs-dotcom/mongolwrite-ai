import { convert } from "@gege-mn/gege-converter";

const MVS = "\u180E";
const NNBSP = "\u202F";
const FVS1 = "\u180B";

/**
 * Gege emits Unicode-16-correct MVS connectors. Mongolian Word users (and
 * Bolorsoft/KIMO) expect the older practical encoding: NNBSP between stem and
 * case suffix, plus FVS1 on the suffix's first letter, and monggol with ᠣ.
 * Without this, text looks "wrong" next to KIMO / official Word output.
 */
function toPracticalBichig(script: string): string {
  let out = script.replaceAll("ᠮᠣᠩᠭᠤᠯ", "ᠮᠣᠩᠭᠣᠯ");

  // ай/ой/уй… diphthongs: vowel + ᠢ → vowel + ᠶᠢ (сайн, байна, байгууллага)
  out = out.replace(/([ᠠᠡᠣᠤᠥᠦ])ᠢ/g, "$1ᠶᠢ");

  const suffixForms: Array<[string, string]> = [
    ["ᠤᠨ", `ᠤ${FVS1}ᠨ`],
    ["ᠦᠨ", `ᠦ${FVS1}ᠨ`],
    ["ᠳᠤ", `ᠳ${FVS1}ᠤ`],
    ["ᠳᠦ", `ᠳ${FVS1}ᠦ`],
    ["ᠲᠤ", `ᠲ${FVS1}ᠤ`],
    ["ᠲᠦ", `ᠲ${FVS1}ᠦ`],
    ["ᠶᠢᠨ", `ᠶ${FVS1}ᠢᠨ`],
  ];
  for (const [from, to] of suffixForms) {
    out = out.replaceAll(`${MVS}${from}`, `${NNBSP}${to}`);
  }

  return out;
}

/** Cyrillic → traditional Mongolian script (Word/KIMO-compatible shaping). */
export function cyrillicToBichig(text: string): string {
  if (!text.trim()) return "";
  try {
    return toPracticalBichig(convert(text));
  } catch {
    return text;
  }
}
