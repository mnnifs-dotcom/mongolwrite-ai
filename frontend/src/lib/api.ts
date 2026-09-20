import type {
  AuthMeResponse,
  AuthUser,
  CheckResponse,
  ImproveResponse,
  SettingsResponse,
} from "./types";

export type { AuthMeResponse, AuthUser };

function apiUrl(path: string): string {
  if (typeof window !== "undefined") return path;
  return `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}${path}`;
}

export async function checkText(
  text: string,
  options?: { document_type?: string; style?: string; signal?: AbortSignal },
): Promise<CheckResponse> {
  return postCheck("/api/v1/check/deterministic", text, options);
}

export async function checkTextWithAI(
  text: string,
  options?: { document_type?: string; style?: string; signal?: AbortSignal },
): Promise<CheckResponse> {
  return postCheck("/api/v1/check/all", text, options);
}

export class CheckLimitError extends Error {
  limit: number;

  constructor(limit?: number) {
    super(
      limit
        ? `Текст хэт урт байна. Нэг дор ${limit.toLocaleString("mn-MN")} тэмдэгт хүртэл шалгана.`
        : "Текст хэт урт байна. Багцын хязгаар хэтэрсэн.",
    );
    this.name = "CheckLimitError";
    this.limit = limit ?? 0;
  }
}

async function postCheck(
  path: string,
  text: string,
  options?: { document_type?: string; style?: string; signal?: AbortSignal },
): Promise<CheckResponse> {
  const body = JSON.stringify({
    text,
    document_type: options?.document_type ?? "official_letter",
    style: options?.style ?? "government_official",
  });
  // Engine targets a few seconds up to ~300k; keep headroom for cold Fly starts.
  const timeoutMs = Math.min(
    90_000,
    Math.max(20_000, 12_000 + Math.floor(text.length * 0.25)),
  );
  let lastError: Error | null = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const timeout = AbortSignal.timeout(timeoutMs);
      const signal = options?.signal
        ? AbortSignal.any([options.signal, timeout])
        : timeout;
      const response = await fetch(apiUrl(path), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body,
        signal,
      });
      if (response.ok) {
        return response.json() as Promise<CheckResponse>;
      }
      if (response.status === 413 || response.status === 422) {
        lastError = new CheckLimitError();
      } else {
        lastError = new Error(
          response.status >= 500
            ? "Шалгалт түр саатав."
            : `Шалгалт амжилтгүй (${response.status})`,
        );
      }
      if (response.status < 500) break;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        if (options?.signal?.aborted) throw err;
        throw new Error(
          "Шалгалт хэт удаан байна. Бичвэрийг хэсэгчлэн (жишээ нь бүлгээр) шалгана уу.",
        );
      }
      if (err instanceof Error && err.name === "AbortError") {
        if (options?.signal?.aborted) throw err;
        throw new Error(
          "Шалгалт хэт удаан байна. Бичвэрийг хэсэгчлэн (жишээ нь бүлгээр) шалгана уу.",
        );
      }
      if (err instanceof Error && err.name === "TimeoutError") {
        throw new Error(
          "Шалгалт хэт удаан байна. Бичвэрийг хэсэгчлэн (жишээ нь бүлгээр) шалгана уу.",
        );
      }
      lastError = err instanceof Error ? err : new Error("Холбогдсонгүй");
    }
    if (options?.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw lastError ?? new Error("Шалгалт амжилтгүй");
}

export async function submitFeedback(input: {
  category: string;
  message: string;
  word?: string;
  email?: string;
  page?: string;
}): Promise<{ ok: boolean; id: string }> {
  const response = await fetch(apiUrl("/api/v1/feedback"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      category: input.category,
      message: input.message,
      word: input.word ?? "",
      email: input.email ?? "",
      page: input.page ?? "",
    }),
  });
  if (!response.ok) {
    throw new Error(
      response.status === 422
        ? "Тайлбар хэт богино байна."
        : "Мэдэгдэл илгээж чадсангүй.",
    );
  }
  return response.json() as Promise<{ ok: boolean; id: string }>;
}

export async function improveText(
  text: string,
  options?: { document_type?: string; style?: string },
): Promise<ImproveResponse> {
  const response = await fetch(apiUrl("/api/v1/check/improve"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      document_type: options?.document_type ?? "official_letter",
      style: options?.style ?? "government_official",
    }),
  });
  if (!response.ok) {
    if (response.status === 413 || response.status === 422) {
      throw new CheckLimitError();
    }
    throw new Error(`Сайжруулалт амжилтгүй (${response.status})`);
  }
  return response.json() as Promise<ImproveResponse>;
}

export async function importDocument(file: File): Promise<{ filename: string; text: string }> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(apiUrl("/api/v1/import/file"), {
    method: "POST",
    body,
  });
  if (!response.ok) {
    throw new Error("Файлыг уншиж чадсангүй");
  }
  return response.json() as Promise<{ filename: string; text: string }>;
}

/** Download Mongolian-script text as a Word (.docx) file. */
export async function downloadBichigDocx(
  text: string,
  filename = "mongol-bichig.docx",
): Promise<void> {
  const response = await fetch(apiUrl("/api/v1/export/docx"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, filename, script: "bichig" }),
  });
  if (!response.ok) {
    throw new Error("Word файл үүсгэж чадсангүй");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename.endsWith(".docx") ? filename : `${filename}.docx`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function learnFromText(text: string): Promise<{ added: string[]; added_count: number }> {
  const response = await fetch(apiUrl("/api/v1/dictionary/learn"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw new Error("Тольд нэмж чадсангүй");
  }
  return response.json() as Promise<{ added: string[]; added_count: number }>;
}

export async function getSettings(): Promise<SettingsResponse> {
  const response = await fetch(apiUrl("/api/v1/settings"), { credentials: "include" });
  if (!response.ok) {
    return { ai_enabled: false, check_max_chars: 500 };
  }
  return response.json() as Promise<SettingsResponse>;
}

export async function authMe(): Promise<AuthMeResponse> {
  const response = await fetch(apiUrl("/api/v1/auth/me"), { credentials: "include" });
  if (!response.ok) {
    return { authenticated: false, user: null, google_client_id: null, plans: [] };
  }
  return response.json() as Promise<AuthMeResponse>;
}

export async function loginWithGoogle(
  credential: string,
): Promise<{ ok: boolean; user: AuthUser }> {
  const response = await fetch(apiUrl("/api/v1/auth/google"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential }),
  });
  if (!response.ok) {
    throw new Error("Google-ээр нэвтэрч чадсангүй");
  }
  return response.json() as Promise<{ ok: boolean; user: AuthUser }>;
}

export async function loginWithGoogleAccessToken(
  accessToken: string,
): Promise<{ ok: boolean; user: AuthUser }> {
  const response = await fetch(apiUrl("/api/v1/auth/google"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: accessToken }),
  });
  if (!response.ok) {
    throw new Error("Google-ээр нэвтэрч чадсангүй");
  }
  return response.json() as Promise<{ ok: boolean; user: AuthUser }>;
}

export async function authLogout(): Promise<void> {
  await fetch(apiUrl("/api/v1/auth/logout"), {
    method: "POST",
    credentials: "include",
  });
}

export async function saveAiKey(key: string): Promise<SettingsResponse> {
  const response = await fetch(apiUrl("/api/v1/settings/ai-key"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key }),
  });
  if (!response.ok) {
    throw new Error("Түлхүүр хадгалж чадсангүй");
  }
  return response.json() as Promise<SettingsResponse>;
}

export async function addDictionaryWords(
  words: string[],
): Promise<{ added: string[]; added_count: number }> {
  const response = await fetch(apiUrl("/api/v1/dictionary/words"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words }),
  });
  if (!response.ok) {
    throw new Error("Үг нэмж чадсангүй");
  }
  return response.json() as Promise<{ added: string[]; added_count: number }>;
}

/** Skip a spelling mark without fixing — queues the word for admin review. */
export async function skipSpellingWord(word: string, ruleId = ""): Promise<void> {
  await fetch(apiUrl("/api/v1/dictionary/skip"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word, rule_id: ruleId }),
  });
}

export type PendingSkippedWord = {
  word: string;
  folded: string;
  rule_id: string;
  count: number;
  updated_at: string;
};

export type HunspellCandidate = {
  word: string;
  folded: string;
  tier: "reliable" | "doubt";
  reason: string;
  suggestion: string;
  count: number;
  seen_at: string;
  updated_at: string;
};

export type SiteHealth = {
  status: "ready" | "starting" | "busy";
  ready: boolean;
  advice: string;
  checks_24h: number;
  warm_p95_ms_24h: number;
  p50_ms_24h?: number;
  p95_ms_24h: number;
  slow_24h: number;
  outlier_24h: number;
  warmup_ms: number;
  uptime_seconds: number;
  check_concurrency?: number;
  cache?: {
    enabled: boolean;
    connected: boolean;
    hit_pct: number;
    lookups: number;
    l1_hits: number;
    redis_hits: number;
    misses: number;
    backend: string;
  };
};

export type SiteOverview = {
  lexicon: {
    seed: number;
    has_hunspell: boolean;
    hunspell_stems?: number;
    admin_added?: number;
  };
  candidates: {
    reliable: number;
    doubt: number;
    total: number;
    reliable_items?: HunspellCandidate[];
    doubt_items?: HunspellCandidate[];
  };
  added_words?: AdminAddedWord[];
  pending_skipped?: PendingSkippedWord[];
  pending_count?: number;
  health?: SiteHealth;
  admin_username: string;
  check_max_chars: number;
};

export type AdminAddedWord = {
  word: string;
  folded: string;
  added_at: string;
};

export type AdminUser = {
  id: string;
  email: string;
  name: string;
  picture: string;
  plan: string;
  plan_name: string;
  plan_expires_at: string | null;
  is_paid: boolean;
  status: string;
  created_at: string;
  last_login_at: string;
};

export type AdminUsersPage = {
  items: AdminUser[];
  total: number;
  offset: number;
  limit: number;
  counts: {
    total: number;
    free: number;
    paid: number;
    pro: number;
    pro_3m?: number;
    pro_year?: number;
  };
};

export async function adminLogin(username: string, password: string): Promise<void> {
  const response = await fetch(apiUrl("/api/v1/admin/login"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const detail =
      response.status === 503
        ? "Админ нууц үг тохируулаагүй"
        : "Нэвтрэх нэр эсвэл нууц үг буруу";
    throw new Error(detail);
  }
}

export async function adminLogout(): Promise<void> {
  await fetch(apiUrl("/api/v1/admin/logout"), { method: "POST", credentials: "include" });
}

export async function adminMe(): Promise<boolean> {
  const response = await fetch(apiUrl("/api/v1/admin/me"), { credentials: "include" });
  return response.ok;
}

export async function adminOverview(): Promise<SiteOverview> {
  const response = await fetch(apiUrl("/api/v1/admin/overview"), { credentials: "include" });
  if (!response.ok) throw new Error("Ерөнхий мэдээлэл уншигдсангүй");
  return response.json() as Promise<SiteOverview>;
}

export async function adminCandidates(
  tier?: "reliable" | "doubt",
): Promise<{ items: HunspellCandidate[]; count: number }> {
  const query = tier ? `?tier=${tier}` : "";
  const response = await fetch(apiUrl(`/api/v1/admin/candidates${query}`), {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Нэр дэвшигч үгс уншигдсангүй");
  return response.json() as Promise<{ items: HunspellCandidate[]; count: number }>;
}

export async function adminApproveCandidates(
  words: string[],
): Promise<{ added: string[]; added_count: number; recorded_count?: number }> {
  const response = await fetch(apiUrl("/api/v1/admin/candidates/approve"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words }),
  });
  if (!response.ok) throw new Error("Үгсийг санд нэмж чадсангүй");
  return response.json() as Promise<{
    added: string[];
    added_count: number;
    recorded_count?: number;
  }>;
}

export async function adminRejectCandidates(
  words: string[],
): Promise<{ removed: string[]; removed_count: number }> {
  const response = await fetch(apiUrl("/api/v1/admin/candidates/reject"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words }),
  });
  if (!response.ok) throw new Error("Үгсийг хасаж чадсангүй");
  return response.json() as Promise<{ removed: string[]; removed_count: number }>;
}

export type LegalImportPreview = {
  present: boolean;
  trusted_count: number;
  doubt_count: number;
  trusted_sample: string[];
  doubt_sample: string[];
  corpus?: {
    articles?: number;
    unique_tokens?: number;
    already_in_seed?: number;
  };
  meta?: {
    source?: string;
    rules?: Record<string, unknown>;
    trusted_count?: number;
    doubt_count?: number;
    corpus?: {
      articles?: number;
      unique_tokens?: number;
      already_in_seed?: number;
    };
  };
};

export async function adminLegalPreview(): Promise<LegalImportPreview> {
  const response = await fetch(apiUrl("/api/v1/admin/lexicon/legal-preview"), {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Legalinfo тойм уншигдсангүй");
  return response.json() as Promise<LegalImportPreview>;
}

export async function adminLegalImport(): Promise<{
  added_to_lexicon: number;
  queued_for_admin: number;
  trusted_file: number;
  doubt_file: number;
}> {
  const response = await fetch(apiUrl("/api/v1/admin/lexicon/legal-import"), {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) throw new Error("Legalinfo импорт амжилтгүй");
  return response.json() as Promise<{
    added_to_lexicon: number;
    queued_for_admin: number;
    trusted_file: number;
    doubt_file: number;
  }>;
}

export type LegalLawItem = {
  law_id: string;
  title: string;
  url: string;
  article_count?: number;
};

export type LegalLawsPage = {
  items: LegalLawItem[];
  total: number;
  offset: number;
  limit: number;
  source?: string | null;
  catalog_count: number;
  ingested_count?: number;
  failed_count?: number;
  remaining_count?: number;
};

export async function adminLegalLaws(params: {
  q?: string;
  offset?: number;
  limit?: number;
}): Promise<LegalLawsPage> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.offset != null) search.set("offset", String(params.offset));
  if (params.limit != null) search.set("limit", String(params.limit));
  const query = search.toString();
  const response = await fetch(apiUrl(`/api/v1/admin/legal/laws${query ? `?${query}` : ""}`), {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Хуулийн жагсаалт уншигдсангүй");
  return response.json() as Promise<LegalLawsPage>;
}

export type LegalLawIngestResult = {
  law_id: string;
  title: string;
  url: string;
  char_count: number;
  line_count: number;
  added_to_lexicon: number;
  added_words: string[];
  queued_candidates: number;
};

export async function adminLegalLawIngest(lawId: string): Promise<LegalLawIngestResult> {
  const response = await fetch(apiUrl(`/api/v1/admin/legal/laws/${encodeURIComponent(lawId)}/ingest`), {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    let message = "Хууль татаж чадсангүй";
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  return response.json() as Promise<LegalLawIngestResult>;
}

export type FailedLawItem = {
  law_id: string;
  title: string;
  url: string;
  error: string;
  reason: string;
  attempts: number;
  failed_at: string;
};

export async function adminLegalLawsFailed(limit = 100): Promise<{
  items: FailedLawItem[];
  count: number;
}> {
  const response = await fetch(apiUrl(`/api/v1/admin/legal/laws/failed?limit=${limit}`), {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Алдаатай хуулиуд уншигдсангүй");
  return response.json() as Promise<{ items: FailedLawItem[]; count: number }>;
}

export async function adminLegalLawSkip(lawId: string): Promise<{ skipped: FailedLawItem }> {
  const response = await fetch(apiUrl(`/api/v1/admin/legal/laws/${encodeURIComponent(lawId)}/skip`), {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) throw new Error("Хуулийг хасаж чадсангүй");
  return response.json() as Promise<{ skipped: FailedLawItem }>;
}

export async function adminLegalLawRetry(lawId: string): Promise<{ retried: string }> {
  const response = await fetch(apiUrl(`/api/v1/admin/legal/laws/${encodeURIComponent(lawId)}/retry`), {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) throw new Error("Дахин оруулж чадсангүй");
  return response.json() as Promise<{ retried: string }>;
}

export type LegalBotStatus = {
  enabled: boolean;
  running: boolean;
  last_started_at: string;
  last_finished_at: string;
  last_law_id: string;
  last_title: string;
  last_ok: boolean | null;
  last_error: string;
  last_added: number;
  last_queued: number;
  next_wait_seconds: number;
  cycles: number;
  min_interval_seconds: number;
  max_interval_seconds: number;
};

export async function adminLegalBotStatus(): Promise<LegalBotStatus> {
  const response = await fetch(apiUrl("/api/v1/admin/legal/bot"), { credentials: "include" });
  if (!response.ok) throw new Error("Бот төлөв уншигдсангүй");
  return response.json() as Promise<LegalBotStatus>;
}

export type ReviewWordItem = {
  word: string;
  folded: string;
  kinds: string[];
  sources: string[];
  when: string;
  refs?: string[];
  tier?: string;
  reason?: string;
  rule_id?: string;
};

export type ReviewBatch = {
  items: ReviewWordItem[];
  words: string[];
  count: number;
  since: string;
  until: string;
  text: string;
};

export async function adminReviewWords(opts?: {
  since?: string;
  until?: string;
  q?: string;
}): Promise<ReviewBatch> {
  const search = new URLSearchParams();
  if (opts?.since) search.set("since", opts.since);
  if (opts?.until) search.set("until", opts.until);
  if (opts?.q) search.set("q", opts.q);
  const query = search.toString();
  const response = await fetch(apiUrl(`/api/v1/admin/review${query ? `?${query}` : ""}`), {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Шалгах үгс татагдсангүй");
  return response.json() as Promise<ReviewBatch>;
}

export type ReviewPreview = {
  batch_count: number;
  approved_count: number;
  keep: string[];
  keep_extra: string[];
  keep_count: number;
  drop_count: number;
  remove_from_lexicon: string[];
  do_not_add: string[];
};

export async function adminReviewPreview(body: {
  batch_words: string[];
  approved_text: string;
}): Promise<ReviewPreview> {
  const response = await fetch(apiUrl("/api/v1/admin/review/preview"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Урьдчилсан харьцуулалт амжилтгүй");
  return response.json() as Promise<ReviewPreview>;
}

export async function adminReviewConfirm(body: {
  keep: string[];
  remove_from_lexicon: string[];
  do_not_add: string[];
}): Promise<{
  kept_count: number;
  added_count: number;
  removed_count: number;
  rejected_count: number;
}> {
  const response = await fetch(apiUrl("/api/v1/admin/review/confirm"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Баталгаажуулалт амжилтгүй");
  return response.json() as Promise<{
    kept_count: number;
    added_count: number;
    removed_count: number;
    rejected_count: number;
  }>;
}

export type LexiconLetter = {
  letter: string;
  folded: string;
  count: number;
};

export type LexiconPage = {
  words: string[];
  total: number;
  offset: number;
  limit: number;
  letters: LexiconLetter[];
  query: string;
  letter: string;
};

export async function adminLexiconWords(params: {
  q?: string;
  letter?: string;
  offset?: number;
  limit?: number;
}): Promise<LexiconPage> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.letter) search.set("letter", params.letter);
  if (params.offset != null) search.set("offset", String(params.offset));
  if (params.limit != null) search.set("limit", String(params.limit));
  const query = search.toString();
  const response = await fetch(apiUrl(`/api/v1/admin/lexicon/words${query ? `?${query}` : ""}`), {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Үгийн сан уншигдсангүй");
  return response.json() as Promise<LexiconPage>;
}

export async function adminLexiconExport(): Promise<{ words: string[]; count: number }> {
  const response = await fetch(apiUrl("/api/v1/admin/lexicon/export"), {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Үгийн санг татаж чадсангүй");
  return response.json() as Promise<{ words: string[]; count: number }>;
}

export async function adminLexiconRemove(
  words: string[],
  queueAsDoubt = true,
): Promise<{
  removed: string[];
  removed_count: number;
  queued_count: number;
  lexicon_total: number;
}> {
  const response = await fetch(apiUrl("/api/v1/admin/lexicon/remove"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words, queue_as_doubt: queueAsDoubt }),
  });
  if (!response.ok) throw new Error("Үгийг сангаас хасаж чадсангүй");
  return response.json() as Promise<{
    removed: string[];
    removed_count: number;
    queued_count: number;
    lexicon_total: number;
  }>;
}

export async function adminHarvest(
  text: string,
): Promise<{ queued: number; counts: { reliable: number; doubt: number; total: number } }> {
  const response = await fetch(apiUrl("/api/v1/admin/candidates/harvest"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) throw new Error("Цуглуулж чадсангүй");
  return response.json() as Promise<{
    queued: number;
    counts: { reliable: number; doubt: number; total: number };
  }>;
}

export async function adminAddedWords(opts?: {
  since?: string;
  until?: string;
  q?: string;
}): Promise<{ items: AdminAddedWord[]; count: number }> {
  const params = new URLSearchParams();
  if (opts?.since) params.set("since", opts.since);
  if (opts?.until) params.set("until", opts.until);
  if (opts?.q) params.set("q", opts.q);
  const query = params.toString();
  const response = await fetch(
    apiUrl(`/api/v1/admin/added-words${query ? `?${query}` : ""}`),
    { credentials: "include" },
  );
  if (!response.ok) throw new Error("Нэмсэн үгс уншигдсангүй");
  return response.json() as Promise<{ items: AdminAddedWord[]; count: number }>;
}

export async function adminApprovePending(
  word: string,
): Promise<{ added: string[]; added_count: number; word: string }> {
  const response = await fetch(apiUrl("/api/v1/admin/pending/approve"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word }),
  });
  if (!response.ok) throw new Error("Үг нэмж чадсангүй");
  return response.json() as Promise<{ added: string[]; added_count: number; word: string }>;
}

export async function adminApprovePendingMany(
  words: string[],
): Promise<{ added: string[]; added_count: number; removed_count: number; words: string[] }> {
  const response = await fetch(apiUrl("/api/v1/admin/pending/approve-many"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words }),
  });
  if (!response.ok) throw new Error("Үгс нэмж чадсангүй");
  return response.json() as Promise<{
    added: string[];
    added_count: number;
    removed_count: number;
    words: string[];
  }>;
}

export async function adminRejectPending(word: string): Promise<{ word: string }> {
  const response = await fetch(apiUrl("/api/v1/admin/pending/reject"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word }),
  });
  if (!response.ok) throw new Error("Үг хасаж чадсангүй");
  return response.json() as Promise<{ word: string }>;
}

export async function adminRejectPendingMany(
  words: string[],
): Promise<{ removed: string[]; removed_count: number }> {
  const response = await fetch(apiUrl("/api/v1/admin/pending/reject-many"), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words }),
  });
  if (!response.ok) throw new Error("Үгс хасаж чадсангүй");
  return response.json() as Promise<{ removed: string[]; removed_count: number }>;
}

export async function adminUsers(opts?: {
  q?: string;
  plan?: string;
  offset?: number;
  limit?: number;
}): Promise<AdminUsersPage> {
  const params = new URLSearchParams();
  if (opts?.q) params.set("q", opts.q);
  if (opts?.plan) params.set("plan", opts.plan);
  if (opts?.offset != null) params.set("offset", String(opts.offset));
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  const query = params.toString();
  const response = await fetch(apiUrl(`/api/v1/admin/users${query ? `?${query}` : ""}`), {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Хэрэглэгчид уншигдсангүй");
  return response.json() as Promise<AdminUsersPage>;
}

export async function adminSetUserPlan(
  userId: string,
  plan: "free" | "pro_3m" | "pro_year" | "pro",
  planExpiresAt?: string | null,
): Promise<{ ok: boolean; user: AdminUser }> {
  const response = await fetch(apiUrl(`/api/v1/admin/users/${encodeURIComponent(userId)}/plan`), {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan,
      plan_expires_at: planExpiresAt ?? null,
    }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Төлөвлөгөө шинэчлэгдсэнгүй");
  }
  return response.json() as Promise<{ ok: boolean; user: AdminUser }>;
}

export type BillingPlan = {
  id: string;
  name: string;
  price_mnt: number;
  duration_days?: number | null;
  interval?: string;
  features: string[];
  badge?: string;
  blurb?: string;
};

export type BillingStatus = {
  plans: BillingPlan[];
  all_plans: BillingPlan[];
  currency: string;
  provider: string;
  checkout_ready: boolean;
  message: string;
};

export type BillingOrder = {
  id: string;
  sender_invoice_no: string;
  plan_id: string;
  plan_name: string;
  amount_mnt: number;
  currency: string;
  status: string;
  qpay_qr_text?: string | null;
  qpay_urls?: unknown[];
  created_at?: string;
  expires_at?: string;
  note?: string;
};

export async function fetchBillingPlans(): Promise<BillingStatus> {
  const response = await fetch(apiUrl("/api/v1/billing/plans"));
  if (!response.ok) throw new Error("Багц уншигдсангүй");
  return response.json() as Promise<BillingStatus>;
}

export async function createBillingCheckout(
  planId: "pro_3m" | "pro_year",
): Promise<{ ok: boolean; order: BillingOrder; checkout_ready: boolean; provider: string }> {
  const response = await fetch(apiUrl("/api/v1/billing/checkout"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ plan_id: planId }),
  });
  if (!response.ok) {
    const detail =
      response.status === 401 || response.status === 403
        ? "Төлбөр хийхийн тулд нэвтэрнэ үү."
        : "Захиалга үүсгэж чадсангүй.";
    throw new Error(detail);
  }
  return response.json() as Promise<{
    ok: boolean;
    order: BillingOrder;
    checkout_ready: boolean;
    provider: string;
  }>;
}
