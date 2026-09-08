export type Correction = {
  id: string;
  category: string;
  original_text: string;
  suggested_text: string;
  explanation: string;
  confidence: number;
  start: number;
  end: number;
  source: string;
  rule_id: string;
  severity: "error" | "warning" | "suggestion";
  suggestions?: string[];
};

export type CheckResponse = {
  corrections: Correction[];
  word_count: number;
  character_count: number;
  ai_enabled?: boolean;
};

export type ImproveResponse = CheckResponse & {
  text: string;
  applied_count: number;
};

export type SettingsResponse = {
  ai_enabled: boolean;
};

export const CATEGORY_LABELS: Record<string, string> = {
  SPELLING: "Үсэг",
  GRAMMAR: "Дүрэм",
  PUNCTUATION: "Цэг таслал",
  WORD_CHOICE: "Үгийн сонголт",
  STYLE: "Найруулга",
  FORMALITY: "Албан хэл",
  CLARITY: "Ойлгомжтой байдал",
  REDUNDANCY: "Давхардал",
  TERMINOLOGY: "Нэр томьёо",
  AI_REWRITE: "AI",
};

export const FILTERS = [
  "ALL",
  "SPELLING",
  "GRAMMAR",
  "WORD_CHOICE",
  "STYLE",
  "CLARITY",
  "PUNCTUATION",
  "REDUNDANCY",
  "FORMALITY",
] as const;
