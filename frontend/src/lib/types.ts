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

/** Editor only shows spelling marks. */
export const CATEGORY_LABELS: Record<string, string> = {
  SPELLING: "Зөв бичиг",
};

export const FILTERS = ["ALL", "SPELLING"] as const;
