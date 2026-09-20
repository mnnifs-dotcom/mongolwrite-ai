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
  check_max_chars?: number;
  google_client_id?: string | null;
};

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  picture: string;
  plan: string;
  plan_name: string;
  plan_expires_at?: string | null;
  is_paid?: boolean;
  entitlements: {
    check_max_chars: number;
    checks_per_day: number | null;
    features: string[];
  };
};

export type AuthMeResponse = {
  authenticated: boolean;
  user: AuthUser | null;
  google_client_id: string | null;
  plans: Array<{
    id: string;
    name: string;
    price_mnt: number;
    check_max_chars: number;
    checks_per_day: number | null;
    features: string[];
  }>;
};

/** Editor only shows spelling marks. */
export const CATEGORY_LABELS: Record<string, string> = {
  SPELLING: "Зөв бичиг",
};

export const FILTERS = ["ALL", "SPELLING"] as const;
