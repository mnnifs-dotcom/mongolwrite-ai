import { convert } from "@gege-mn/gege-converter";

const MVS = "\u180E";
const NNBSP = "\u202F";
const FVS1 = "\u180B";

const MN_DIGITS = "᠐᠑᠒᠓᠔᠕᠖᠗᠘᠙";

/**
 * High-trust Bolorsoft/KIMO readings for words gege mis-ranks or mis-shapes.
 * Uses Ali Gali ᢈ/ᢉ where KIMO does — correct with Dashitseden/MongolianScript.
 */
const WORD_OVERRIDES: Record<string, string> = {
  монгол: "ᠮᠣᠩᠭᠣᠯ",
  улсын: `ᠤᠯᠤᠰ${NNBSP}ᠤ${FVS1}ᠨ`,
  улс: "ᠤᠯᠤᠰ",
  ерөнхийлөгч: "ᠶᠡᠷᠦᠩᢈᠡᠶᠢᠯᠡᢉᠴᠢ",
  зэвсэгт: "ᠵᠡᠪᠰᠡᢉᠲᠦ",
  хүчний: `ᢈᠦᠴᠦᠨ${NNBSP}ᠦ${FVS1}`,
  хүчин: "ᢈᠦᠴᠦᠨ",
  ерөнхий: "ᠶᠡᠷᠦᠩᢈᠡᠢ",
  командлагч: "ᠻᠣᠮᠮᠠᠨ᠋ᠳ᠋ᠯᠠᠭᠴᠢ",
  ухнаагийн: `ᠤᠬᠤᠨ${MVS}ᠠ${NNBSP}ᠶ${FVS1}ᠢᠨ`,
  ухнаа: `ᠤᠬᠤᠨ${MVS}ᠠ`,
  хүрэлсүх: `ᢈᠦᠷᠡᠯᠰᠦ${FVS1}ᢈᠡ`,
  онд: `ᠣᠨ${NNBSP}ᠳ${FVS1}ᠤ`,
  оны: `ᠣᠨ${NNBSP}ᠤ${FVS1}`,
  он: "ᠣᠨ",
  сайн: "ᠰᠠᠶᠢᠨ",
  байна: `ᠪᠠᠶᠢᠨ${MVS}ᠠ`,
  байх: "ᠪᠠᠶᠢᠬᠤ",
  хотод: `ᠬᠣᠲᠠ${NNBSP}ᠳ${FVS1}ᠤ`,
  хот: "ᠬᠣᠲᠠ",
  эрхэм: "ᠡᠷᢈᠢᠮ",
  хүндэт: "ᢈᠦᠨᠳᠦᠲᠦ",
  хүсэлт: "ᢈᠦᠰᠡᠯᠲᠡ",
  хүсэлтийг: `ᢈᠦᠰᠡᠯᠲᠡ${NNBSP}ᠶ${FVS1}ᠢ`,
  байгууллага: `ᠪᠠᠶᠢᠭᠤᠯᠤᠯᠭ${MVS}ᠠ`,
  байгууллагаас: `ᠪᠠᠶᠢᠭᠤᠯᠤᠯᠭ${MVS}ᠠ${NNBSP}ᠠᠴᠠ`,
  төрийн: `ᠲᠥᠷᠦ${NNBSP}ᠶ${FVS1}ᠢᠨ`,
  төр: "ᠲᠥᠷᠦ",
  гэрээ: `ᠭᠡᠷ${MVS}ᠡ`,
  хууль: "ᠬᠠᠤᠯᠢ",
  шүүх: "ᠰᠢᢉᠦᢈᠦ",
  иргэн: "ᠢᠷᢉᠡᠨ",
  засаг: "ᠵᠠᠰᠠᠭ",
  өдөр: "ᠡᠳᠦᠷ",
  өдрийн: `ᠡᠳᠦᠷ${NNBSP}ᠦ${FVS1}ᠨ`,
  сарын: `ᠰᠠᠷ${MVS}ᠠ${NNBSP}ᠶ${FVS1}ᠢᠨ`,
  сар: `ᠰᠠᠷ${MVS}ᠠ`,
  манай: "ᠮᠠᠨᠠᠢ",
  танай: "ᠲᠠᠨᠠᠢ",
  хүлээн: "ᢈᠦᠯᠢᠶᠡᠨ",
  авч: "ᠠᠪᠴᠤ",
  уу: "ᠤᠤ",
  үү: "ᠦᠦ",
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

  // Gege sometimes doubles yi before genitive: …ᠶᠢ᠎ᠶᠢᠨ (ухнаагийн)
  out = out.replace(/ᠶᠢ(?:\u180E|\u202F)?ᠶᠢᠨ/g, `${NNBSP}ᠶ${FVS1}ᠢᠨ`);

  // ай/ой/уй… diphthongs: vowel + ᠢ → vowel + ᠶᠢ (сайн, байна)
  out = out.replace(/([ᠠᠡᠣᠤᠥᠦ])ᠢ/g, "$1ᠶᠢ");

  const suffixForms: Array<[string, string]> = [
    ["ᠤᠨ", `ᠤ${FVS1}ᠨ`],
    ["ᠦᠨ", `ᠦ${FVS1}ᠨ`],
    ["ᠳᠤ", `ᠳ${FVS1}ᠤ`],
    ["ᠳᠦ", `ᠳ${FVS1}ᠦ`],
    ["ᠲᠤ", `ᠲ${FVS1}ᠤ`],
    ["ᠲᠦ", `ᠲ${FVS1}ᠦ`],
    ["ᠶᠢᠨ", `ᠶ${FVS1}ᠢᠨ`],
    ["ᠠᠴᠠ", "ᠠᠴᠠ"],
    ["ᠡᠴᠡ", "ᠡᠴᠡ"],
  ];
  for (const [from, to] of suffixForms) {
    out = out.replaceAll(`${MVS}${from}`, `${NNBSP}${to}`);
  }
  return out;
}

/**
 * Bolorsoft/KIMO convention: front-vowel words use Ali Gali ᢈ/ᢉ for х/г.
 * Dashitseden shapes these correctly; Noto often does not.
 */
function toAliGaliFront(script: string): string {
  return script.replace(/\S+/gu, (token) => {
    const hasFront = /[ᠡᠥᠦ]/.test(token);
    const hasBack = /[ᠠᠣᠤ]/.test(token);
    if (hasFront && !hasBack) {
      return token.replaceAll("ᠬ", "ᢈ").replaceAll("ᠭ", "ᢉ");
    }
    return token;
  });
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
    return toAliGaliFront(
      toPracticalBichig(convert(word, { digits: "mongolian", punctuation: "mongolian" })),
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
      return toAliGaliFront(
        toPracticalBichig(convert(token, { digits: "mongolian", punctuation: "mongolian" })),
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
