import { cyrillicToBichig } from "@/lib/bichig";

const FVS1 = "\u180B";
const NNBSP = "\u202F";

export type BichigAuditHit = {
  word: string;
  suggested: string;
  rule_id: string;
  explanation: string;
};

/** True when FVS1 appears outside NNBSP-suffix shaping (visible mid-word junk). */
function hasOrphanFvs(script: string): boolean {
  for (let i = 0; i < script.length; i++) {
    if (script[i] !== FVS1) continue;
    if (!(i >= 2 && script[i - 2] === NNBSP)) return true;
  }
  return false;
}

/**
 * Flag curated lemmas that break Mongol-bichig conversion (mid-word "!",
 * leftover Cyrillic/Latin, multi-word dictionary rows).
 */
export function auditWordForBichig(word: string): BichigAuditHit | null {
  const trimmed = word.trim();
  if (!trimmed) return null;

  if (/\s/.test(trimmed)) {
    const parts = trimmed.split(/\s+/).filter(Boolean);
    return {
      word: trimmed,
      suggested: parts.join(" · "),
      rule_id: "bichig_multiword",
      explanation: "Сангийн нэг мөрөнд олон үг — бичигт буруу хөрвөнө. Тус тусад нь үлдээнэ.",
    };
  }

  let script = "";
  try {
    script = cyrillicToBichig(trimmed);
  } catch {
    return {
      word: trimmed,
      suggested: "",
      rule_id: "bichig_error",
      explanation: "Монгол бичигт хөрвүүлэхэд алдаа гарлаа.",
    };
  }

  if (!script.trim()) {
    return {
      word: trimmed,
      suggested: "",
      rule_id: "bichig_empty",
      explanation: "Монгол бичигт хоосон гарав.",
    };
  }

  if (script.includes("!") || script.includes("！")) {
    return {
      word: trimmed,
      suggested: "",
      rule_id: "bichig_bang",
      explanation: "Хөрвүүлэлтэд анхаарлын тэмдэг (!) үлдлээ.",
    };
  }

  if (/[а-яёөүА-ЯЁӨҮ]/u.test(script)) {
    return {
      word: trimmed,
      suggested: "",
      rule_id: "bichig_cyrillic",
      explanation: "Хөрвүүлэлтэд кирилл үсэг үлдлээ.",
    };
  }

  if (/[A-Za-z]/.test(script)) {
    return {
      word: trimmed,
      suggested: "",
      rule_id: "bichig_latin",
      explanation: "Хөрвүүлэлтэд латин үсэг үлдлээ.",
    };
  }

  if (hasOrphanFvs(script)) {
    return {
      word: trimmed,
      suggested: "",
      rule_id: "bichig_mark",
      explanation: "Үгийн дунд харагдах тэмдэг (FVS) үлдлээ — бичигт ! шиг харагдана.",
    };
  }

  return null;
}

export function auditWordsForBichig(words: string[]): BichigAuditHit[] {
  const hits: BichigAuditHit[] = [];
  for (const word of words) {
    const hit = auditWordForBichig(word);
    if (hit) hits.push(hit);
  }
  return hits;
}
