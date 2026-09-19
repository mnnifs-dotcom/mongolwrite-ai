import { convert } from "@gege-mn/gege-converter";

const MVS = "\u180E";
const NNBSP = "\u202F";
const FVS1 = "\u180B";

const MN_DIGITS = "᠐᠑᠒᠓᠔᠕᠖᠗᠘᠙";

/** High-trust KIMO/Bolorsoft readings for words gege mis-ranks or mis-shapes. */
const WORD_OVERRIDES: Record<string, string> = {
  монгол: "ᠮᠣᠩᠭᠣᠯ",
  улсын: `ᠤᠯᠤᠰ${NNBSP}ᠤ${FVS1}ᠨ`,
  ерөнхийлөгч: "ᠶᠡᠷᠦᠩᢈᠡᠶᠢᠯᠡᢉᠴᠢ",
  зэвсэгт: "ᠵᠡᠪᠰᠡᢉᠲᠦ",
  хүчний: "ᢈᠦᠴᠦᠨ ᠦ᠋",
  ерөнхий: "ᠶᠡᠷᠦᠩᢈᠡᠢ",
  командлагч: "ᠻᠣᠮᠮᠠᠨ᠋ᠳ᠋ᠯᠠᠭᠴᠢ",
  ухнаагийн: `ᠤᠬᠤᠨ${MVS}ᠠ${NNBSP}ᠶ${FVS1}ᠢᠨ`,
  хүрэлсүх: `ᢈᠦᠷᠡᠯᠰᠦ${FVS1}ᢈᠡ`,
  онд: `ᠣᠨ${NNBSP}ᠳ${FVS1}ᠤ`,
  сайн: "ᠰᠠᠶᠢᠨ",
  байна: `ᠪᠠᠶᠢᠨ${MVS}ᠠ`,
  хотод: `ᠬᠣᠲᠠ${NNBSP}ᠳ${FVS1}ᠤ`,
  эрхэм: "ᠡᠷᢈᠢᠮ",
  хүндэт: "ᢈᠦᠨᠳᠦᠲᠦ",
  хүсэлт: "ᢈᠦᠰᠡᠯᠲᠡ",
  байгууллага: `ᠪᠠᠶᠢᠭᠤᠯᠤᠯᠭ${MVS}ᠠ`,
  төрийн: `ᠲᠥᠷᠦ${NNBSP}ᠶ${FVS1}ᠢᠨ`,
};

const PUNCT_MAP: Record<string, string> = {
  ".": "᠃",
  ",": "᠂",
  ":": "᠄",
  ";": "᠄",
  "!": "᠄",
  "?": "᠅",
  "«": "《",
  "»": "》",
};

/**
 * Gege emits Unicode-16 MVS connectors. Practical Word/KIMO shaping uses NNBSP
 * + FVS1 on case suffixes, monggol with ᠣ, and ᠶᠢ diphthongs.
 */
function toPracticalBichig(script: string): string {
  let out = script.replaceAll("ᠮᠣᠩᠭᠤᠯ", "ᠮᠣᠩᠭᠣᠯ");
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

function convertDigits(token: string): string {
  return [...token]
    .map((ch) => {
      const n = ch.charCodeAt(0) - 48;
      return n >= 0 && n <= 9 ? MN_DIGITS[n] : ch;
    })
    .join("");
}

function convertWord(word: string): string {
  const key = word.toLocaleLowerCase("mn");
  const override = WORD_OVERRIDES[key];
  if (override) return override;
  try {
    return toPracticalBichig(
      convert(word, { digits: "mongolian", punctuation: "mongolian" }),
    );
  } catch {
    return word;
  }
}

function convertToken(token: string): string {
  if (/^\d+$/.test(token)) return convertDigits(token);
  if (token.length === 1 && PUNCT_MAP[token]) return PUNCT_MAP[token];

  // Split leading/trailing punctuation so «хууль.» → override + ᠃
  const match = token.match(/^(\P{L}*)(\p{L}[\p{L}\p{M}\-']*)(\P{L}*)$/u);
  if (!match) {
    try {
      return toPracticalBichig(
        convert(token, { digits: "mongolian", punctuation: "mongolian" }),
      );
    } catch {
      return token;
    }
  }
  const [, lead, core, trail] = match;
  const leadOut = [...lead].map((ch) => PUNCT_MAP[ch] ?? ch).join("");
  const trailOut = [...trail].map((ch) => PUNCT_MAP[ch] ?? ch).join("");
  if (!core) return leadOut + trailOut;
  return leadOut + convertWord(core) + trailOut;
}

/**
 * Cyrillic → traditional Mongolian script.
 * Runs over the finished text (command-based), not character-by-character while typing.
 */
export function cyrillicToBichig(text: string): string {
  if (!text.trim()) return "";
  // Keep whitespace; convert words/numbers/punct as whole tokens.
  return text.replace(/(\s+)|(\d+)|(\S+)/gu, (part, space: string | undefined) => {
    if (space) return space;
    return convertToken(part);
  });
}
