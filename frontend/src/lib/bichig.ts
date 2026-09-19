import { analyze, convert } from "@gege-mn/gege-converter";
import type { Candidate } from "@gege-mn/gege-converter";

const MVS = "\u180E";
const NNBSP = "\u202F";
const FVS1 = "\u180B";

const MN_DIGITS = "᠐᠑᠒᠓᠔᠕᠖᠗᠘᠙";

const CONVERT_OPTS = { digits: "mongolian" as const, punctuation: "mongolian" as const };

/**
 * High-trust Bolorsoft/KIMO readings for words gege mis-ranks or mis-shapes.
 * Uses Ali Gali ᢈ/ᢉ where KIMO does — correct with Dashitseden/MongolianScript.
 *
 * Also locks forms where multi-suffix parses are genuinely correct (хамтдаа)
 * but the general stem-final scorer would prefer a worse whole-word guess.
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
  // Classical teγülder (gege guess tögüldür is tofu-free but less classical)
  төгөлдөр: "ᠲᠡᢉᠦᠯᠳᠡᠷ",
  // Genuine multi-suffix forms the stem-final scorer would otherwise flatten
  хамтдаа: `ᠬᠠᠮᠲᠤ${NNBSP}ᠳ${FVS1}ᠤ${NNBSP}ᠪᠠᠨ`,
  олондтоо: `ᠣᠯᠠᠨ${NNBSP}ᠳ${FVS1}ᠤ${NNBSP}ᠲ${FVS1}ᠤ${NNBSP}ᠪᠠᠨ`,
  өөртөө: `ᠥᠪᠡᠷ${NNBSP}ᠲ${FVS1}ᠦ${NNBSP}ᠪᠡᠨ`,
};

/** Cyrillic case/particle endings → traditional suffixes (front / back). Longer first. */
const DECLENSIONS: Array<{
  re: RegExp;
  front: string;
  back: string;
}> = [
  { re: /ийн$/u, front: `${NNBSP}ᠦ${FVS1}ᠨ`, back: `${NNBSP}ᠤ${FVS1}ᠨ` },
  { re: /ын$/u, front: `${NNBSP}ᠦ${FVS1}ᠨ`, back: `${NNBSP}ᠤ${FVS1}ᠨ` },
  { re: /ийг$/u, front: `${NNBSP}ᠶ${FVS1}ᠢ`, back: `${NNBSP}ᠶ${FVS1}ᠢ` },
  { re: /ыг$/u, front: `${NNBSP}ᠶ${FVS1}ᠢ`, back: `${NNBSP}ᠶ${FVS1}ᠢ` },
  { re: /ээс$/u, front: `${NNBSP}ᠡᠴᠡ`, back: `${NNBSP}ᠠᠴᠠ` },
  { re: /аас$/u, front: `${NNBSP}ᠡᠴᠡ`, back: `${NNBSP}ᠠᠴᠠ` },
  { re: /өөс$/u, front: `${NNBSP}ᠡᠴᠡ`, back: `${NNBSP}ᠠᠴᠠ` },
  { re: /оос$/u, front: `${NNBSP}ᠡᠴᠡ`, back: `${NNBSP}ᠠᠴᠠ` },
  { re: /ээр$/u, front: `${NNBSP}ᠢᠶᠡᠷ`, back: `${NNBSP}ᠢᠶᠠᠷ` },
  { re: /аар$/u, front: `${NNBSP}ᠢᠶᠡᠷ`, back: `${NNBSP}ᠢᠶᠠᠷ` },
  { re: /өөр$/u, front: `${NNBSP}ᠢᠶᠡᠷ`, back: `${NNBSP}ᠢᠶᠠᠷ` },
  { re: /оор$/u, front: `${NNBSP}ᠢᠶᠡᠷ`, back: `${NNBSP}ᠢᠶᠠᠷ` },
  { re: /тэй$/u, front: `${NNBSP}ᠲᠡᠶᠢ`, back: `${NNBSP}ᠲᠠᠶᠢ` },
  { re: /тай$/u, front: `${NNBSP}ᠲᠡᠶᠢ`, back: `${NNBSP}ᠲᠠᠶᠢ` },
  { re: /той$/u, front: `${NNBSP}ᠲᠡᠶᠢ`, back: `${NNBSP}ᠲᠣᠶᠢ` },
  { re: /д$/u, front: `${NNBSP}ᠳ${FVS1}ᠦ`, back: `${NNBSP}ᠳ${FVS1}ᠤ` },
  { re: /т$/u, front: `${NNBSP}ᠲ${FVS1}ᠦ`, back: `${NNBSP}ᠲ${FVS1}ᠤ` },
];

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

function isFrontStem(script: string): boolean {
  const hasFront = /[ᠡᠥᠦᢈᢉ]/.test(script);
  const hasBack = /[ᠠᠣᠤ]/.test(script);
  return hasFront && !hasBack;
}

/**
 * Gege emits Unicode-16 MVS connectors. Practical Word/KIMO shaping uses NNBSP
 * + FVS1 on case suffixes, monggol with ᠣ, and ᠶᠢ diphthongs.
 *
 * Leftover MVS that is not a true vowel separator (before ᠠ/ᠡ) must be removed:
 * MongolianScript maps U+180E to an empty base glyph, so browsers show tofu.
 */
function toPracticalBichig(script: string): string {
  let out = script.replaceAll("ᠮᠣᠩᠭᠤᠯ", "ᠮᠣᠩᠭᠣᠯ");

  // Gege sometimes doubles yi before genitive: …ᠶᠢ᠎ᠶᠢᠨ (ухнаагийн)
  out = out.replace(/ᠶᠢ(?:\u180E|\u202F)?ᠶᠢᠨ/g, `${NNBSP}ᠶ${FVS1}ᠢᠨ`);

  // ай/ой/уй… diphthongs: vowel + ᠢ → vowel + ᠶᠢ (сайн, байна)
  out = out.replace(/([ᠠᠡᠣᠤᠥᠦ])ᠢ/g, "$1ᠶᠢ");

  // Longer matches first (ᠤᠨ before bare ᠤ).
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
    ["ᠪᠡᠷ", "ᠪᠡᠷ"],
    ["ᠪᠠᠷ", "ᠪᠠᠷ"],
    ["ᠢᠶᠡᠷ", "ᠢᠶᠡᠷ"],
    ["ᠢᠶᠠᠷ", "ᠢᠶᠠᠷ"],
    ["ᠪᠠᠨ", "ᠪᠠᠨ"],
    ["ᠪᠡᠨ", "ᠪᠡᠨ"],
    // Short genitive/possessive: хүчний, ажилтны
    ["ᠤ", `ᠤ${FVS1}`],
    ["ᠦ", `ᠦ${FVS1}`],
  ];
  for (const [from, to] of suffixForms) {
    out = out.replaceAll(`${MVS}${from}`, `${NNBSP}${to}`);
  }

  // Drop leftover MVS that is not a vowel separator (before final a/e).
  out = out.replace(/\u180E(?![ᠠᠡ])/g, "");
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

/**
 * Re-rank gege candidates. Gege often treats stem-final letters of names/stems
 * as case endings:
 *   баярмаа → bayarm-iyan   (аа as reflexive)
 *   гандболд → γandbul-du   (д as dative)
 *   оюунчимэг → oyunčime-yi (г as accusative)
 *   төгөлдөр → töγel-dü-ber (д+өр over-segmentation)
 *
 * Legitimate case forms (номын, онд, дундаа) keep their score.
 */
function scoreCandidate(c: Candidate): number {
  let s = c.confidence ?? 0;
  const suffixes = c.segmentation?.suffixes ?? [];
  const sep = suffixes.filter((x) => x.separate);
  const prov = c.provenance;

  if (suffixes.length === 1) {
    const suf = suffixes[0];
    if (prov === "guess") {
      if (suf.cyrillic === "г" && suf.category === "accusative") s -= 0.4;
      if (suf.cyrillic === "д" && suf.category === "dative-locative") s -= 0.4;
      if (suf.cyrillic === "т" && suf.category === "dative-locative") s -= 0.3;
      if (/^[аэоө]{2}$/u.test(suf.cyrillic) && suf.category === "reflexive") s -= 0.35;
    }
    // Lexicon "гэр-ийн" style reflexive on long-vowel words — prefer γer-e
    if (
      (prov === "lexicon" || prov === "harvested") &&
      suf.category === "reflexive" &&
      /iyan$|iyen$/u.test(c.classical)
    ) {
      s -= 0.2;
    }
  }

  if (sep.length >= 2) {
    const firstShort = (sep[0].cyrillic?.length ?? 0) <= 1;
    const secondShort = (sep[1].cyrillic?.length ?? 0) <= 2;
    // төгөлдөр-style: single-letter piece + short second piece
    if (firstShort && secondShort) s -= 0.5;
    else if (firstShort) s -= 0.35;
  }

  return s;
}

function pickCandidateScript(cands: readonly Candidate[]): string | null {
  if (!cands.length) return null;
  let best = cands[0];
  let bestScore = scoreCandidate(best);
  for (let i = 1; i < cands.length; i++) {
    const score = scoreCandidate(cands[i]);
    if (score > bestScore) {
      best = cands[i];
      bestScore = score;
    }
  }
  return best.script;
}

function topSeparateCount(word: string): number {
  try {
    const tokens = analyze(word, CONVERT_OPTS);
    const wt = tokens.find((t) => t.token.kind === "word");
    return wt?.candidates?.[0]?.segmentation?.suffixes?.filter((s) => s.separate).length ?? 0;
  } catch {
    return 0;
  }
}

/**
 * Analyze the full token so clitic splits (монголруу → монгол + руу) stay intact,
 * then apply stem-final-aware ranking per fragment.
 */
function pickGegeScript(word: string): string {
  try {
    const tokens = analyze(word, CONVERT_OPTS);
    if (!tokens.length) return convert(word, CONVERT_OPTS);

    let out = "";
    let sawWord = false;
    for (const t of tokens) {
      if (t.token.kind === "word") {
        sawWord = true;
        const picked = pickCandidateScript(t.candidates ?? []);
        out += picked ?? convert(t.token.text, CONVERT_OPTS);
      } else if (t.token.kind === "space") {
        out += t.token.text;
      } else {
        out += convert(t.token.text, CONVERT_OPTS);
      }
    }
    return sawWord ? out : convert(word, CONVERT_OPTS);
  } catch {
    return convert(word, CONVERT_OPTS);
  }
}

function finalizeScript(script: string): string {
  return toAliGaliFront(toPracticalBichig(script));
}

function convertWord(word: string): string {
  const key = word.toLocaleLowerCase("mn");
  const override = WORD_OVERRIDES[key];
  if (override) return override;

  // Declined forms: strip case ending, convert stem, re-attach practical suffix.
  // Critical when the full form over-segments (төгөлдөрийн → töγel-dü-ber-ün).
  for (const decl of DECLENSIONS) {
    const m = key.match(decl.re);
    if (!m) continue;
    const stem = key.slice(0, -m[0].length);
    if (!stem || stem.length < 2) continue;

    if (WORD_OVERRIDES[stem]) {
      const stemScript = WORD_OVERRIDES[stem];
      const suffix = isFrontStem(stemScript) ? decl.front : decl.back;
      return stemScript + suffix;
    }

    // Only rebuild from stem when the full word looks over-segmented
    if (topSeparateCount(key) >= 2) {
      const stemScript = finalizeScript(pickGegeScript(stem));
      if (stemScript && !/[а-яёөүА-ЯЁӨҮ]/u.test(stemScript)) {
        const suffix = isFrontStem(stemScript) ? decl.front : decl.back;
        return stemScript + suffix;
      }
    }
  }

  try {
    return finalizeScript(pickGegeScript(word));
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
      return finalizeScript(pickGegeScript(token));
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
