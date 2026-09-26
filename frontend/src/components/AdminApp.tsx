"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import {
  adminAddedWords,
  adminApproveCandidates,
  adminApprovePending,
  adminApprovePendingMany,
  adminHarvest,
  adminLegalBotStatus,
  adminLegalImport,
  adminLegalLawIngest,
  adminLegalLawRetry,
  adminLegalLaws,
  adminLegalLawsFailed,
  adminLegalLawSkip,
  adminLegalPreview,
  adminLexiconRemove,
  adminLexiconExport,
  adminLexiconWords,
  adminLogin,
  adminLogout,
  adminMe,
  adminOverview,
  adminRejectCandidates,
  adminRejectPending,
  adminRejectPendingMany,
  adminSetUserPlan,
  adminClearUserDevices,
  adminUsers,
  adminFeedbackList,
  adminFeedbackDelete,
  adminFeedbackPurgeTests,
  type AdminAddedWord,
  type AdminFeedbackItem,
  type AdminUser,
  type AdminUsersPage,
  type FailedLawItem,
  type HunspellCandidate,
  type LegalBotStatus,
  type LegalFailedSummary,
  type LegalImportPreview,
  type LegalLawItem,
  type LexiconLetter,
  type PendingSkippedWord,
  type SiteOverview,
} from "@/lib/api";
import { BrandLogo } from "@/components/BrandLogo";
import { AdminReviewPanel } from "@/components/AdminReviewPanel";

type AdminSection =
  | "overview"
  | "lexicon"
  | "hunspell"
  | "pending"
  | "added"
  | "feedback"
  | "review"
  | "users"
  | "legal"
  | "health";

const PAGE_SIZE = 400;
const USERS_PAGE = 50;
const LAWS_PAGE = 40;

const FEEDBACK_LABELS: Record<string, string> = {
  spelling: "Зөв бичиг",
  bichig: "Монгол бичиг",
  site: "Сайт",
  other: "Бусад",
};

function formatWhen(value: string): string {
  if (!value) return "—";
  const stamp = Date.parse(value);
  if (Number.isNaN(stamp)) return value;
  return new Date(stamp).toLocaleString("mn-MN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days} өдөр ${hours % 24} цаг`;
  if (hours > 0) return `${hours} цаг`;
  return `${Math.floor(seconds / 60)} мин`;
}

function healthLabel(status: string): string {
  if (status === "ready") return "Хэвийн";
  if (status === "busy") return "Завгүй";
  return "Асаж байна";
}

export function AdminApp() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [overview, setOverview] = useState<SiteOverview | null>(null);
  const [reliable, setReliable] = useState<HunspellCandidate[]>([]);
  const [doubt, setDoubt] = useState<HunspellCandidate[]>([]);
  const [addedWords, setAddedWords] = useState<AdminAddedWord[]>([]);
  const [addedFiltered, setAddedFiltered] = useState<AdminAddedWord[]>([]);
  const [addedSince, setAddedSince] = useState("");
  const [addedUntil, setAddedUntil] = useState("");
  const [addedQuery, setAddedQuery] = useState("");
  const [addedSelected, setAddedSelected] = useState<Set<string>>(new Set());
  const [addedLoading, setAddedLoading] = useState(false);
  const [addedCopied, setAddedCopied] = useState(false);
  const [feedbackItems, setFeedbackItems] = useState<AdminFeedbackItem[]>([]);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [pendingSkipped, setPendingSkipped] = useState<PendingSkippedWord[]>([]);
  const [pendingSelected, setPendingSelected] = useState<Set<string>>(new Set());
  const [pendingCopied, setPendingCopied] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [harvestText, setHarvestText] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [acting, setActing] = useState<string | null>(null);
  const [legalPreview, setLegalPreview] = useState<LegalImportPreview | null>(null);
  const [laws, setLaws] = useState<LegalLawItem[]>([]);
  const [lawsTotal, setLawsTotal] = useState(0);
  const [lawsOffset, setLawsOffset] = useState(0);
  const [lawsCatalogCount, setLawsCatalogCount] = useState(0);
  const [lawsIngestedCount, setLawsIngestedCount] = useState(0);
  const [lawsRemainingCount, setLawsRemainingCount] = useState(0);
  const [lawsFailedCount, setLawsFailedCount] = useState(0);
  const [lawsFailedSummary, setLawsFailedSummary] = useState<LegalFailedSummary | null>(null);
  const [lawsTitledRemaining, setLawsTitledRemaining] = useState(0);
  const [lawsUntitledRemaining, setLawsUntitledRemaining] = useState(0);
  const [lawsTitledOnly, setLawsTitledOnly] = useState(true);
  const [failedLaws, setFailedLaws] = useState<FailedLawItem[]>([]);
  const [legalBot, setLegalBot] = useState<LegalBotStatus | null>(null);
  const [lawsQuery, setLawsQuery] = useState("");
  const [lawsLoading, setLawsLoading] = useState(false);
  const [ingestingLawId, setIngestingLawId] = useState<string | null>(null);
  const [section, setSection] = useState<AdminSection>("lexicon");
  const [lexQuery, setLexQuery] = useState("");
  const [lexLetter, setLexLetter] = useState("");
  const [lexOffset, setLexOffset] = useState(0);
  const [lexWords, setLexWords] = useState<string[]>([]);
  const [lexTotal, setLexTotal] = useState(0);
  const [lexLetters, setLexLetters] = useState<LexiconLetter[]>([]);
  const [lexSelected, setLexSelected] = useState<Set<string>>(new Set());
  const [lexLoading, setLexLoading] = useState(false);
  const [lexCopied, setLexCopied] = useState(false);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersOffset, setUsersOffset] = useState(0);
  const [usersCounts, setUsersCounts] = useState<AdminUsersPage["counts"]>({
    total: 0,
    free: 0,
    paid: 0,
    pro: 0,
    pro_3m: 0,
    pro_year: 0,
  });
  const [usersQuery, setUsersQuery] = useState("");
  const [usersPlan, setUsersPlan] = useState("");
  const [usersLoading, setUsersLoading] = useState(false);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [editPlan, setEditPlan] = useState<"free" | "pro_3m" | "pro_year">("free");
  const [editExpiry, setEditExpiry] = useState("");

  const applyOverview = useCallback((next: SiteOverview) => {
    setOverview(next);
    setReliable(next.candidates.reliable_items ?? []);
    setDoubt(next.candidates.doubt_items ?? []);
    const added = next.added_words ?? [];
    setAddedWords(added);
    setPendingSkipped(next.pending_skipped ?? []);
    setPendingSelected(new Set());
  }, []);

  const loadAddedWords = useCallback(
    async (opts?: { since?: string; until?: string; q?: string }) => {
      const since = opts?.since ?? addedSince;
      const until = opts?.until ?? addedUntil;
      const q = opts?.q ?? addedQuery;
      setAddedLoading(true);
      setError(null);
      try {
        const page = await adminAddedWords({
          since: since || undefined,
          until: until || undefined,
          q: q.trim() || undefined,
        });
        setAddedFiltered(page.items);
        setAddedSelected(new Set());
        // Keep nav badge in sync when filters clear — otherwise leave overview total.
        if (!since && !until && !q.trim()) {
          setAddedWords(page.items);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Нэмсэн үгс уншигдсангүй");
      } finally {
        setAddedLoading(false);
      }
    },
    [addedSince, addedUntil, addedQuery],
  );

  const loadFeedback = useCallback(async () => {
    setFeedbackLoading(true);
    setError(null);
    try {
      const page = await adminFeedbackList(300);
      setFeedbackItems(page.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Алдааны мэдэгдэл уншигдсангүй");
    } finally {
      setFeedbackLoading(false);
    }
  }, []);

  const loadLexicon = useCallback(async (opts?: { q?: string; letter?: string; offset?: number }) => {
    const q = opts?.q ?? lexQuery;
    const letter = opts?.letter ?? lexLetter;
    const offset = opts?.offset ?? lexOffset;
    setLexLoading(true);
    try {
      const page = await adminLexiconWords({
        q: q.trim() || undefined,
        letter: letter || undefined,
        offset,
        limit: PAGE_SIZE,
      });
      setLexWords(page.words);
      setLexTotal(page.total);
      setLexLetters(page.letters);
      setLexOffset(page.offset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Үгийн сан уншигдсангүй");
    } finally {
      setLexLoading(false);
    }
  }, [lexQuery, lexLetter, lexOffset]);

  const loadUsers = useCallback(async (opts?: { q?: string; plan?: string; offset?: number }) => {
    const q = opts?.q ?? usersQuery;
    const plan = opts?.plan ?? usersPlan;
    const offset = opts?.offset ?? usersOffset;
    setUsersLoading(true);
    try {
      const page = await adminUsers({
        q: q.trim() || undefined,
        plan: plan || undefined,
        offset,
        limit: USERS_PAGE,
      });
      setUsers(page.items);
      setUsersTotal(page.total);
      setUsersOffset(page.offset);
      setUsersCounts(page.counts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Хэрэглэгчид уншигдсангүй");
    } finally {
      setUsersLoading(false);
    }
  }, [usersQuery, usersPlan, usersOffset]);

  const loadLaws = useCallback(async (opts?: { q?: string; offset?: number; titledOnly?: boolean }) => {
    const q = opts?.q ?? lawsQuery;
    const offset = opts?.offset ?? lawsOffset;
    const titledOnly = opts?.titledOnly ?? lawsTitledOnly;
    setLawsLoading(true);
    try {
      const [page, failed, bot] = await Promise.all([
        adminLegalLaws({
          q: q.trim() || undefined,
          offset,
          limit: LAWS_PAGE,
          titled_only: titledOnly,
        }),
        adminLegalLawsFailed(80).catch(() => ({
          items: [] as FailedLawItem[],
          count: 0,
          summary: undefined as LegalFailedSummary | undefined,
        })),
        adminLegalBotStatus().catch(() => null),
      ]);
      setLaws(page.items);
      setLawsTotal(page.total);
      setLawsOffset(page.offset);
      setLawsCatalogCount(page.catalog_count);
      setLawsIngestedCount(page.ingested_count ?? 0);
      setLawsRemainingCount(page.remaining_count ?? page.total);
      setLawsTitledRemaining(page.titled_remaining ?? 0);
      setLawsUntitledRemaining(page.untitled_remaining ?? 0);
      setLawsFailedCount(page.failed_count ?? failed.count);
      setLawsFailedSummary(page.failed_summary ?? failed.summary ?? null);
      setFailedLaws(failed.items);
      setLegalBot(bot);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Хуулийн жагсаалт уншигдсангүй");
    } finally {
      setLawsLoading(false);
    }
  }, [lawsQuery, lawsOffset, lawsTitledOnly]);

  const loadLists = useCallback(async () => {
    const nextOverview = await adminOverview();
    applyOverview(nextOverview);
    try {
      setLegalPreview(await adminLegalPreview());
    } catch {
      setLegalPreview(null);
    }
  }, [applyOverview]);

  useEffect(() => {
    void (async () => {
      try {
        const ok = await adminMe();
        setAuthed(ok);
        if (ok) {
          await loadLists();
          await loadLexicon({ offset: 0 });
          await loadUsers({ offset: 0 });
          await loadLaws({ offset: 0 });
          await loadFeedback();
        }
      } catch {
        setAuthed(false);
      } finally {
        setReady(true);
      }
    })();
    // Initial load only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!authed || section !== "added") return;
    void loadAddedWords();
    // Reload when opening the section; filter fields apply via form submit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, section]);

  useEffect(() => {
    if (!authed || section !== "feedback") return;
    void (async () => {
      // Drop leftover deploy/smoke-test rows so they don't clog the real queue.
      try {
        await adminFeedbackPurgeTests();
      } catch {
        /* ignore — still load whatever is there */
      }
      await loadFeedback();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, section]);

  useEffect(() => {
    if (!authed || section !== "legal") return;
    void loadLaws();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, section]);

  async function onLogin(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await adminLogin(username, password);
      setAuthed(true);
      setPassword("");
      await loadLists();
      await loadLexicon({ offset: 0 });
      await loadUsers({ offset: 0 });
      setSection("lexicon");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Нэвтэрч чадсангүй");
    } finally {
      setBusy(false);
    }
  }

  async function onLogout() {
    await adminLogout();
    setAuthed(false);
    setOverview(null);
    setReliable([]);
    setDoubt([]);
    setAddedWords([]);
    setPendingSkipped([]);
    setUsers([]);
    setUsersTotal(0);
    setSelected(new Set());
    setStatus("");
    setError(null);
  }

  async function onSaveUserPlan() {
    if (!editingUser || acting) return;
    setActing(`user-${editingUser.id}`);
    setError(null);
    try {
      const result = await adminSetUserPlan(
        editingUser.id,
        editPlan,
        editPlan === "free" ? null : editExpiry || null,
      );
      setStatus(
        `«${result.user.email || result.user.name || result.user.id}» · ${result.user.status}`,
      );
      setEditingUser(null);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Төлөвлөгөө шинэчлэгдсэнгүй");
    } finally {
      setActing(null);
    }
  }

  async function onClearUserDevices() {
    if (!editingUser || acting) return;
    setActing(`user-dev-${editingUser.id}`);
    setError(null);
    try {
      const result = await adminClearUserDevices(editingUser.id);
      setStatus(
        `«${result.user.email || result.user.name || result.user.id}» · төхөөрөмж цэвэрлэгдлээ`,
      );
      setEditingUser({ ...editingUser, device_count: 0 });
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Төхөөрөмж цэвэрлэж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function onPendingApprove(word: string) {
    if (acting) return;
    setActing(`p-ok-${word.toLocaleLowerCase("mn")}`);
    setError(null);
    try {
      const result = await adminApprovePending(word);
      setStatus(
        result.added_count ? `«${result.word}» санд орлоо` : `«${result.word}» аль хэдийн санд байсан`,
      );
      setPendingSelected((current) => {
        const next = new Set(current);
        next.delete(word.toLocaleLowerCase("mn"));
        return next;
      });
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Нэмж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function onPendingReject(word: string) {
    if (acting) return;
    setActing(`p-no-${word.toLocaleLowerCase("mn")}`);
    setError(null);
    try {
      const result = await adminRejectPending(word);
      setStatus(`«${result.word}» татгалзлаа`);
      setPendingSelected((current) => {
        const next = new Set(current);
        next.delete(word.toLocaleLowerCase("mn"));
        return next;
      });
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Татгалзаж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  function togglePendingWord(folded: string, enabled: boolean) {
    setPendingSelected((current) => {
      const next = new Set(current);
      if (enabled) next.add(folded);
      else next.delete(folded);
      return next;
    });
  }

  function pendingSelectedText(): string {
    return pendingSkipped
      .filter((item) => pendingSelected.has(item.folded))
      .map((item) => item.word)
      .join("\n");
  }

  function applyPendingSelectedText(text: string) {
    const tokens = text
      .split(/[\s,;]+/)
      .map((part) => part.trim())
      .filter(Boolean);
    if (!tokens.length) {
      setPendingSelected(new Set());
      return;
    }
    const byFold = new Map(pendingSkipped.map((item) => [item.folded, item] as const));
    const byWord = new Map(
      pendingSkipped.map((item) => [item.word.toLocaleLowerCase("mn"), item] as const),
    );
    const next = new Set<string>();
    for (const token of tokens) {
      const folded = token.toLocaleLowerCase("mn");
      const match = byFold.get(folded) ?? byWord.get(folded);
      if (match) next.add(match.folded);
    }
    setPendingSelected(next);
  }

  async function copyPendingSelected() {
    const text = pendingSelectedText();
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    setPendingCopied(true);
    window.setTimeout(() => setPendingCopied(false), 2000);
    setStatus(`${pendingSelected.size} үг хууллаа`);
  }

  async function onPendingApproveMany() {
    const words = pendingSkipped
      .filter((item) => pendingSelected.has(item.folded))
      .map((item) => item.word);
    if (!words.length || acting) return;
    setActing("pending-approve");
    setError(null);
    try {
      const result = await adminApprovePendingMany(words);
      setStatus(
        result.added_count
          ? `${result.added_count} үг санд орлоо`
          : `${result.removed_count} үг жагсаалтаас хасагдлаа`,
      );
      setPendingSelected(new Set());
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Нэмж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function onPendingRejectMany() {
    const words = pendingSkipped
      .filter((item) => pendingSelected.has(item.folded))
      .map((item) => item.word);
    if (!words.length || acting) return;
    setActing("pending-reject");
    setError(null);
    try {
      const result = await adminRejectPendingMany(words);
      setStatus(`${result.removed_count} үг татгалзлаа`);
      setPendingSelected(new Set());
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Татгалзаж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  function toggleWord(folded: string, enabled: boolean) {
    setSelected((current) => {
      const next = new Set(current);
      if (enabled) next.add(folded);
      else next.delete(folded);
      return next;
    });
  }

  function selectAllHunspell() {
    setSelected(new Set([...reliable, ...doubt].map((item) => item.folded)));
  }

  function clearHunspellSelection() {
    setSelected(new Set());
  }

  function selectedWordsText(items: HunspellCandidate[]): string {
    return items.map((item) => item.word).join(" ");
  }

  function applySelectedText(text: string) {
    const tokens = text
      .split(/[\s,;]+/)
      .map((part) => part.trim())
      .filter(Boolean);
    if (!tokens.length) {
      setSelected(new Set());
      return;
    }
    const byFold = new Map(
      [...reliable, ...doubt].map((item) => [item.folded, item] as const),
    );
    const byWord = new Map(
      [...reliable, ...doubt].map((item) => [item.word.toLocaleLowerCase("mn"), item] as const),
    );
    const next = new Set<string>();
    for (const token of tokens) {
      const folded = token.toLocaleLowerCase("mn");
      const match = byFold.get(folded) ?? byWord.get(folded);
      if (match) next.add(match.folded);
    }
    setSelected(next);
  }

  async function approveMany(words: string[]) {
    if (!words.length || acting) return;
    setActing("approve");
    setError(null);
    try {
      const result = await adminApproveCandidates(words);
      setStatus(
        result.added_count
          ? `${result.added_count} үг санд орлоо`
          : result.recorded_count
            ? `${result.recorded_count} үг санд баталгаажууллаа`
            : "Сонгосон үгс аль хэдийн санд байсан.",
      );
      setSelected(new Set());
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Нэмж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function rejectMany(words: string[]) {
    if (!words.length || acting) return;
    setActing("reject");
    setError(null);
    try {
      const result = await adminRejectCandidates(words);
      setStatus(
        result.removed_count
          ? `${result.removed_count} үг жагсаалтаас хасагдлаа`
          : "Сонгосон үгс хасагдлаа",
      );
      setSelected(new Set());
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Хасаж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function onHarvest(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await adminHarvest(harvestText);
      setStatus(
        result.queued
          ? `${result.queued} үг цугларлаа`
          : "Шинэ үг олдсонгүй",
      );
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Цуглуулж чадсангүй");
    } finally {
      setBusy(false);
    }
  }

  async function onLegalImport() {
    if (acting) return;
    setActing("legal");
    setError(null);
    try {
      const result = await adminLegalImport();
      setStatus(
        `Legalinfo файл: шалгах багц / Hunspell руу ${result.queued_for_admin.toLocaleString("mn-MN")} үг · шууд санд оруулаагүй`,
      );
      await loadLists();
      await loadLexicon({ offset: 0 });
      setSection("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Импорт амжилтгүй");
    } finally {
      setActing(null);
    }
  }

  async function onLawsSearch(event: FormEvent) {
    event.preventDefault();
    setLawsOffset(0);
    await loadLaws({ offset: 0, q: lawsQuery });
  }

  async function onLawIngest(lawId: string) {
    if (ingestingLawId || acting) return;
    setIngestingLawId(lawId);
    setError(null);
    try {
      const result = await adminLegalLawIngest(lawId);
      const queued = result.queued_for_review ?? result.queued_candidates ?? 0;
      const already = result.already_in_lexicon ?? 0;
      const alreadyHint =
        already > 0
          ? ` · аль хэдийн санд ${already.toLocaleString("mn-MN")}`
          : "";
      setStatus(
        `«${result.title}» (#${result.law_id}): шалгах багц руу ${queued.toLocaleString("mn-MN")} үг${alreadyHint} · ${(result.char_count || 0).toLocaleString("mn-MN")} тэмдэгт · шууд санд оруулаагүй`,
      );
      await loadLists();
      await loadLexicon({ offset: 0 });
      const nextOffset = laws.length <= 1 ? Math.max(0, lawsOffset - LAWS_PAGE) : lawsOffset;
      setLawsOffset(nextOffset);
      await loadLaws({ offset: nextOffset, q: lawsQuery });
    } catch (err) {
      // Failed ingest now auto-skips the law from the queue — refresh so it disappears.
      setError(
        err instanceof Error
          ? err.message.toLocaleLowerCase("mn").includes("олдсонгүй") ||
            err.message.toLocaleLowerCase("mn").includes("хоосон")
            ? `${err.message} · жагсаалтаас хаслаа (акт байхгүй)`
            : `${err.message} · энэ хуулийг хассан жагсаалт руу шилжүүллээ`
          : "Хууль татаж чадсангүй",
      );
      const nextOffset = laws.length <= 1 ? Math.max(0, lawsOffset - LAWS_PAGE) : lawsOffset;
      setLawsOffset(nextOffset);
      await loadLaws({ offset: nextOffset, q: lawsQuery });
    } finally {
      setIngestingLawId(null);
    }
  }

  async function onLawSkip(lawId: string) {
    if (acting) return;
    setActing(`skip-${lawId}`);
    setError(null);
    try {
      await adminLegalLawSkip(lawId);
      setStatus(`Хууль #${lawId}-ийг жагсаалтаас хаслаа`);
      await loadLaws({ offset: lawsOffset, q: lawsQuery });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Хасаж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function onLawRetry(lawId: string) {
    if (acting) return;
    setActing(`retry-${lawId}`);
    setError(null);
    try {
      await adminLegalLawRetry(lawId);
      setStatus(`Хууль #${lawId}-ийг дахин орууллаа`);
      await loadLaws({ offset: 0, q: lawsQuery });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Дахин оруулж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  function toggleLexWord(word: string, enabled: boolean) {
    setLexSelected((current) => {
      const next = new Set(current);
      if (enabled) next.add(word);
      else next.delete(word);
      return next;
    });
  }

  async function onLexSearch(event: FormEvent) {
    event.preventDefault();
    setLexOffset(0);
    setLexSelected(new Set());
    await loadLexicon({ q: lexQuery, letter: lexLetter, offset: 0 });
  }

  async function onPickLetter(folded: string) {
    const next = lexLetter === folded ? "" : folded;
    setLexLetter(next);
    setLexOffset(0);
    setLexSelected(new Set());
    await loadLexicon({ letter: next, q: lexQuery, offset: 0 });
  }

  async function onLexPage(nextOffset: number) {
    setLexOffset(nextOffset);
    setLexSelected(new Set());
    await loadLexicon({ offset: nextOffset });
  }

  async function onRemoveFromLexicon(queueAsDoubt: boolean) {
    const words = [...lexSelected];
    if (!words.length || acting) return;
    setActing("lex-remove");
    setError(null);
    try {
      const result = await adminLexiconRemove(words, queueAsDoubt);
      if (!result.removed_count) {
        setError(`Сонгосон үг хасагдсангүй: ${words.join(", ")}`);
        setStatus("");
      } else {
        setStatus(
          queueAsDoubt
            ? `${result.removed_count} үг сангаас хасаж, алдаатай жагсаалтад орууллаа`
            : `${result.removed_count} үг сангаас хаслаа`,
        );
        setLexSelected(new Set());
        await loadLists();
        await loadLexicon({ offset: lexOffset });
        if (section === "added") await loadAddedWords();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Хасаж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  function toggleAddedWord(folded: string, enabled: boolean) {
    setAddedSelected((current) => {
      const next = new Set(current);
      if (enabled) next.add(folded);
      else next.delete(folded);
      return next;
    });
  }

  function addedSelectedText(): string {
    return addedFiltered
      .filter((item) => addedSelected.has(item.folded))
      .map((item) => item.word)
      .join("\n");
  }

  function applyAddedSelectedText(text: string) {
    const tokens = text
      .split(/[\s,;]+/)
      .map((part) => part.trim())
      .filter(Boolean);
    if (!tokens.length) {
      setAddedSelected(new Set());
      return;
    }
    const byFold = new Map(addedFiltered.map((item) => [item.folded, item] as const));
    const byWord = new Map(
      addedFiltered.map((item) => [item.word.toLocaleLowerCase("mn"), item] as const),
    );
    const next = new Set<string>();
    for (const token of tokens) {
      const folded = token.toLocaleLowerCase("mn");
      const match = byFold.get(folded) ?? byWord.get(folded);
      if (match) next.add(match.folded);
    }
    setAddedSelected(next);
  }

  async function copyAddedSelected() {
    const text = addedSelectedText();
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    setAddedCopied(true);
    window.setTimeout(() => setAddedCopied(false), 2000);
    setStatus(`${addedSelected.size} үг хууллаа`);
  }

  async function onDeleteFeedback(id: string) {
    if (!id || acting) return;
    setActing(`fb-del-${id}`);
    setError(null);
    try {
      await adminFeedbackDelete(id);
      setFeedbackItems((current) => current.filter((row) => row.id !== id));
      setStatus("Мэдэгдэл устгалаа");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Устгаж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function onPurgeTestFeedback() {
    if (acting) return;
    setActing("fb-purge");
    setError(null);
    try {
      const result = await adminFeedbackPurgeTests();
      await loadFeedback();
      setStatus(
        result.deleted_count
          ? `Тест мэдэгдэл ${result.deleted_count} устгалаа`
          : "Тест мэдэгдэл олдсонгүй",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Цэвэрлэж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function copyAllLexiconWords() {
    if (acting === "lex-copy") return;
    setActing("lex-copy");
    setError(null);
    try {
      const payload = await adminLexiconExport();
      const text = payload.words.join("\n");
      if (!text.trim()) {
        setStatus("Үгийн сан хоосон");
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.left = "-9999px";
        document.body.appendChild(area);
        area.select();
        document.execCommand("copy");
        area.remove();
      }
      setLexCopied(true);
      window.setTimeout(() => setLexCopied(false), 2500);
      setStatus(`${payload.count.toLocaleString("mn-MN")} үг хууллаа`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Үгийн санг хуулж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  async function onRemoveAddedFromLexicon() {
    const words = addedFiltered
      .filter((item) => addedSelected.has(item.folded))
      .map((item) => item.word);
    if (!words.length || acting) return;
    setActing("added-remove");
    setError(null);
    try {
      const result = await adminLexiconRemove(words, false);
      if (!result.removed_count) {
        setError(`Сонгосон үг хасагдсангүй: ${words.join(", ")}`);
        setStatus("");
      } else {
        setStatus(`${result.removed_count} үг үгийн сангаас хаслаа`);
        setAddedSelected(new Set());
        await loadLists();
        await loadAddedWords();
        await loadLexicon({ offset: lexOffset });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Хасаж чадсангүй");
    } finally {
      setActing(null);
    }
  }

  if (!ready) {
    return (
      <div className="mw-admin-page">
        <div className="mw-admin mw-admin-centered">
          <BrandLogo size="lg" className="mw-brand-splash" />
          <p className="mw-muted">Уншиж байна…</p>
        </div>
      </div>
    );
  }

  if (!authed) {
    return (
      <div className="mw-admin-page">
        <div className="mw-admin mw-admin-centered">
          <form className="mw-admin-card mw-admin-login" onSubmit={(event) => void onLogin(event)}>
            <BrandLogo size="lg" className="mw-brand-splash" wordmark="MongolWrite · Админ" />
            <h1>Админ нэвтрэх</h1>
            <label>
              Нэвтрэх нэр
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                required
              />
            </label>
            <label>
              Нууц үг
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
            {error ? <p className="mw-banner">{error}</p> : null}
            <button type="submit" className="mw-btn-primary" disabled={busy}>
              {busy ? "Нэвтэрч байна…" : "Нэвтрэх"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  const hunspellWords = [...reliable, ...doubt];
  const selectedHunspell = hunspellWords.filter((item) => selected.has(item.folded));
  const navItems: { id: AdminSection; label: string; count?: number; hide?: boolean }[] = [
    { id: "lexicon", label: "Үгийн сан", count: overview?.lexicon.seed },
    { id: "hunspell", label: "Hunspell үгс", count: hunspellWords.length },
    { id: "pending", label: "Алгассан", count: pendingSkipped.length },
    { id: "added", label: "Нэмсэн", count: addedWords.length },
    { id: "feedback", label: "Алдаа мэдэгдэл", count: feedbackItems.length },
    { id: "review", label: "Шалгах багц" },
    { id: "users", label: "Хэрэглэгчид", count: usersCounts.total },
    {
      id: "legal",
      label: "legalinfo.mn",
      count: lawsRemainingCount || lawsCatalogCount || legalPreview?.trusted_count,
    },
    { id: "overview", label: "Тойм" },
    { id: "health", label: "Сайтын төлөв" },
  ];

  return (
    <div className="mw-admin-page">
      <header className="mw-admin-bar">
        <BrandLogo size="sm" wordmark="MongolWrite · Админ" />
        <Link className="mw-btn" href="/">
          Засварлагч
        </Link>
        <button
          type="button"
          className="mw-btn"
          onClick={() => {
            void loadLists();
            void loadLexicon();
            void loadUsers();
            if (section === "added") void loadAddedWords();
            if (section === "feedback") void loadFeedback();
          }}
        >
          Шинэчлэх
        </button>
        <button type="button" className="mw-btn" onClick={() => void onLogout()}>
          Гарах
        </button>
      </header>
      <div className="mw-admin-shell">
        <aside className="mw-admin-nav" aria-label="Админ цэс">
          {navItems
            .filter((item) => !item.hide)
            .map((item) => (
              <button
                key={item.id}
                type="button"
                className={section === item.id ? "mw-admin-nav-item is-active" : "mw-admin-nav-item"}
                onClick={() => setSection(item.id)}
              >
                <span>{item.label}</span>
                {item.count != null ? (
                  <em>{item.count.toLocaleString("mn-MN")}</em>
                ) : null}
              </button>
            ))}
        </aside>
        <div className="mw-admin mw-admin-pane">
          {error ? <p className="mw-banner">{error}</p> : null}
          {status ? <p className="mw-admin-status">{status}</p> : null}

          {section === "health" && overview?.health ? (
            <section className="mw-admin-card">
              <div className="mw-health-head">
                <h2>Сайтын төлөв</h2>
                <span className={`mw-health-pill is-${overview.health.status}`}>
                  {healthLabel(overview.health.status)}
                </span>
              </div>
              <p className="mw-muted">
                {overview.health.checks_24h} шалгалт · p50{" "}
                {overview.health.p50_ms_24h ??
                  overview.health.warm_p95_ms_24h ??
                  overview.health.p95_ms_24h}
                мс · p95 {overview.health.warm_p95_ms_24h || overview.health.p95_ms_24h}мс ·{" "}
                {formatUptime(overview.health.uptime_seconds)}
              </p>
              <div className="mw-overview-grid" style={{ marginTop: "1rem" }}>
                <div className="mw-overview-tile">
                  <span>Зэрэг шалгалт</span>
                  <strong>{overview.health.check_concurrency ?? 3}</strong>
                  <em>CHECK_CONCURRENCY</em>
                </div>
                <div className="mw-overview-tile">
                  <span>Cache hit</span>
                  <strong>
                    {(overview.health.cache?.hit_pct ?? 0).toLocaleString("mn-MN")}%
                  </strong>
                  <em>
                    {overview.health.cache?.connected
                      ? "Redis + memory"
                      : overview.health.cache?.enabled
                        ? "Redis тохируулсан, холбогдоогүй"
                        : "Зөвхөн memory (Redis байхгүй)"}
                  </em>
                </div>
                <div className="mw-overview-tile">
                  <span>Lookups</span>
                  <strong>
                    {(overview.health.cache?.lookups ?? 0).toLocaleString("mn-MN")}
                  </strong>
                  <em>
                    L1 {overview.health.cache?.l1_hits ?? 0} · Redis{" "}
                    {overview.health.cache?.redis_hits ?? 0} · miss{" "}
                    {overview.health.cache?.misses ?? 0}
                  </em>
                </div>
              </div>
            </section>
          ) : null}

          {section === "overview" && overview ? (
            <section className="mw-admin-card">
              <h2>Тойм</h2>
              <div className="mw-overview-grid">
                <div className="mw-overview-tile">
                  <span>Үгийн сан</span>
                  <strong>{overview.lexicon.seed.toLocaleString("mn-MN")}</strong>
                  <em>
                    {overview.lexicon.hunspell_stems
                      ? `Шалгалт: Hunspell ${(overview.lexicon.hunspell_stems / 1000).toFixed(0)} мянга (бүгдийг санд хийдэггүй)`
                      : overview.lexicon.has_hunspell
                        ? "Hunspell идэвхтэй"
                        : "—"}
                  </em>
                </div>
                <div className="mw-overview-tile">
                  <span>Алгассан</span>
                  <strong>{pendingSkipped.length.toLocaleString("mn-MN")}</strong>
                </div>
                <div className="mw-overview-tile">
                  <span>Hunspell</span>
                  <strong>{hunspellWords.length}</strong>
                  <em>
                    {reliable.length} / {doubt.length}
                  </em>
                </div>
                <div className="mw-overview-tile">
                  <span>Нэмсэн</span>
                  <strong>{addedWords.length.toLocaleString("mn-MN")}</strong>
                </div>
              </div>
            </section>
          ) : null}

          {section === "lexicon" ? (
            <section className="mw-admin-card" id="lexicon-browser">
              <h2>Үгийн сан · {lexTotal.toLocaleString("mn-MN")}</h2>
              <p className="mw-muted">
                Энэ жагсаалт нь curated үгийн сан (санал/админ). Шалгалтын хүлээн авалт Hunspell
                (~{Math.floor((overview?.lexicon.hunspell_stems ?? 0) / 1000)} мянган үндэс)-ээр
                явдаг — тэр бүх үгийг энд шууд оруулдаггүй.
              </p>
              <form className="mw-lex-search" onSubmit={(event) => void onLexSearch(event)}>
                <input
                  value={lexQuery}
                  onChange={(event) => setLexQuery(event.target.value)}
                  placeholder="Үг хайх…"
                  aria-label="Үг хайх"
                />
                <button type="submit" className="mw-btn-primary" disabled={lexLoading}>
                  {lexLoading ? "…" : "Хайх"}
                </button>
                <button
                  type="button"
                  className="mw-btn"
                  onClick={() => {
                    setLexQuery("");
                    setLexLetter("");
                    setLexOffset(0);
                    void loadLexicon({ q: "", letter: "", offset: 0 });
                  }}
                >
                  Цэвэрлэх
                </button>
              </form>
              <div className="mw-lex-letters" role="tablist" aria-label="Үсгээр шүүх">
                {lexLetters.map((item) => (
                  <button
                    key={item.folded}
                    type="button"
                    role="tab"
                    aria-selected={lexLetter === item.folded}
                    className={
                      lexLetter === item.folded ? "mw-lex-letter is-active" : "mw-lex-letter"
                    }
                    onClick={() => void onPickLetter(item.folded)}
                    title={`${item.count} үг`}
                  >
                    {item.letter}
                    <em>{item.count}</em>
                  </button>
                ))}
              </div>
              <div className="mw-admin-row mw-lex-actions">
                <button
                  type="button"
                  className="mw-btn"
                  disabled={lexTotal <= 0 || acting === "lex-copy"}
                  onClick={() => void copyAllLexiconWords()}
                  title="Бүх үгийг нэг мөрөнд нэг үгээр clipboard-д хуулна"
                >
                  {acting === "lex-copy"
                    ? "Хуулж байна…"
                    : lexCopied
                      ? "Хуулсан ✓"
                      : `Бүх үгийг хуулах · ${lexTotal.toLocaleString("mn-MN")}`}
                </button>
                <button
                  type="button"
                  className="mw-btn"
                  disabled={!lexWords.length}
                  onClick={() => setLexSelected(new Set(lexWords))}
                >
                  Хуудсыг сонгох
                </button>
                <button
                  type="button"
                  className="mw-btn"
                  disabled={!lexSelected.size}
                  onClick={() => setLexSelected(new Set())}
                >
                  Сонголт арилгах
                </button>
                <button
                  type="button"
                  className="mw-btn"
                  disabled={!lexSelected.size || acting === "lex-remove"}
                  onClick={() => void onRemoveFromLexicon(true)}
                >
                  {acting === "lex-remove"
                    ? "Хасаж байна…"
                    : lexSelected.size
                      ? `Сангаас хасаад алдаатай руу · ${lexSelected.size}`
                      : "Сангаас хасаад алдаатай руу"}
                </button>
                <button
                  type="button"
                  className="mw-btn"
                  disabled={!lexSelected.size || acting === "lex-remove"}
                  onClick={() => void onRemoveFromLexicon(false)}
                >
                  Зөвхөн хасах
                </button>
              </div>
              {lexWords.length === 0 ? (
                <p className="mw-muted">{lexLoading ? "Уншиж байна…" : "Олдсонгүй"}</p>
              ) : (
                <div className="mw-admin-scroll mw-lex-scroll">
                  <ul className="mw-admin-list mw-lex-list">
                    {lexWords.map((word) => (
                      <li key={word}>
                        <label className="mw-candidate-main">
                          <input
                            type="checkbox"
                            checked={lexSelected.has(word)}
                            onChange={(event) => toggleLexWord(word, event.target.checked)}
                          />
                          <strong>{word}</strong>
                        </label>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="mw-admin-row mw-lex-pager">
                <button
                  type="button"
                  className="mw-btn"
                  disabled={lexOffset <= 0 || lexLoading}
                  onClick={() => void onLexPage(Math.max(0, lexOffset - PAGE_SIZE))}
                >
                  Өмнөх
                </button>
                <span className="mw-muted">
                  {lexTotal
                    ? `${lexOffset + 1}–${Math.min(lexOffset + lexWords.length, lexTotal)} / ${lexTotal.toLocaleString("mn-MN")}`
                    : "0"}
                </span>
                <button
                  type="button"
                  className="mw-btn"
                  disabled={lexOffset + PAGE_SIZE >= lexTotal || lexLoading}
                  onClick={() => void onLexPage(lexOffset + PAGE_SIZE)}
                >
                  Дараах
                </button>
              </div>
            </section>
          ) : null}

          {section === "legal" ? (
            <section className="mw-admin-card" id="legalinfo-laws">
              <h2>legalinfo.mn хуулиуд</h2>
              <p className="mw-muted">
                Үлдсэн {(lawsRemainingCount || lawsTotal).toLocaleString("mn-MN")}
                {lawsTitledRemaining
                  ? ` · нэртэй ${lawsTitledRemaining.toLocaleString("mn-MN")}`
                  : ""}
                {lawsUntitledRemaining
                  ? ` · гарчиггүй ${lawsUntitledRemaining.toLocaleString("mn-MN")}`
                  : ""}
                {lawsIngestedCount
                  ? ` · татсан ${lawsIngestedCount.toLocaleString("mn-MN")}`
                  : ""}
                {lawsFailedCount
                  ? ` · хассан ${lawsFailedCount.toLocaleString("mn-MN")}`
                  : ""}
                {lawsCatalogCount
                  ? ` / ${lawsCatalogCount.toLocaleString("mn-MN")}`
                  : ""}
              </p>
              <p className="mw-muted mw-legal-hint">
                Хуулиас олдсон шинэ үгс шууд санд орохгүй — эхлээд «Шалгах багц»-д орно. Тэнд
                үлдээсний дараа л үгийн санд нэмэгдэнэ. Гарчиггүй линкүүд ихэвчлэн хоосон/устгагдсан
                акт байж болно.
              </p>

              {legalBot ? (
                <div className="mw-legal-bulk" style={{ marginBottom: 14 }}>
                  <h3>Автомат бот</h3>
                  <p className="mw-muted mw-legal-hint">
                    {legalBot.enabled
                      ? `Идэвхтэй · ${Math.round(legalBot.min_interval_seconds / 60)}–${Math.round(legalBot.max_interval_seconds / 60)} мин тутамд 1 хууль (эхлээд нэртэй)`
                      : "Идэвхгүй"}
                    {legalBot.last_law_id
                      ? ` · сүүлд #${legalBot.last_law_id}${legalBot.last_ok === false ? " (алдаа)" : ""}`
                      : ""}
                    {legalBot.last_ok && legalBot.last_law_id
                      ? ` · шалгах багц +${legalBot.last_queued}`
                      : ""}
                    {legalBot.last_error ? ` · ${legalBot.last_error}` : ""}
                    {legalBot.cycles ? ` · ${legalBot.cycles} удаа ажилласан` : ""}
                  </p>
                </div>
              ) : null}

              <form className="mw-admin-row" onSubmit={(event) => void onLawsSearch(event)}>
                <input
                  type="search"
                  value={lawsQuery}
                  onChange={(event) => setLawsQuery(event.target.value)}
                  placeholder="Гарчиг эсвэл lawId (жишээ: 12701)"
                  aria-label="Хууль хайх"
                />
                <button type="submit" className="mw-btn" disabled={lawsLoading}>
                  Хайх
                </button>
                <label className="mw-muted" style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={lawsTitledOnly}
                    onChange={(event) => {
                      const next = event.target.checked;
                      setLawsTitledOnly(next);
                      setLawsOffset(0);
                      void loadLaws({ offset: 0, titledOnly: next });
                    }}
                  />
                  Зөвхөн нэртэй
                </label>
              </form>
              {lawsLoading && laws.length === 0 ? (
                <p className="mw-muted">Уншиж байна…</p>
              ) : laws.length === 0 ? (
                <p className="mw-muted">
                  {lawsTitledOnly
                    ? "Нэртэй хууль үлдсэнгүй — «Зөвхөн нэртэй»-г унтрааж гарчиггүйг харна уу"
                    : "Олдсонгүй"}
                </p>
              ) : (
                <div className="mw-admin-scroll mw-legal-laws-scroll">
                  <ul className="mw-admin-list mw-legal-laws-list">
                    {laws.map((law) => (
                      <li key={law.law_id}>
                        <div className="mw-candidate-main">
                          <strong>{law.title}</strong>
                          <span className="mw-muted">
                            #{law.law_id}
                            {law.untitled ? " · гарчиг индексэд алга" : ""} ·{" "}
                            <a href={law.url} target="_blank" rel="noreferrer">
                              legalinfo.mn
                            </a>
                          </span>
                        </div>
                        <div className="mw-admin-row">
                          <button
                            type="button"
                            className="mw-btn-primary"
                            disabled={ingestingLawId !== null}
                            onClick={() => void onLawIngest(law.law_id)}
                          >
                            {ingestingLawId === law.law_id
                              ? "Татаж шалгаж байна…"
                              : "Татаад санд нэмэх"}
                          </button>
                          <button
                            type="button"
                            className="mw-btn"
                            disabled={Boolean(acting)}
                            onClick={() => void onLawSkip(law.law_id)}
                            title="Алдаатай/хэрэггүй бол жагсаалтаас хасна"
                          >
                            Хасах
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="mw-admin-row">
                <button
                  type="button"
                  className="mw-btn"
                  disabled={lawsLoading || lawsOffset <= 0}
                  onClick={() => {
                    const next = Math.max(0, lawsOffset - LAWS_PAGE);
                    setLawsOffset(next);
                    void loadLaws({ offset: next });
                  }}
                >
                  Өмнөх
                </button>
                <span className="mw-muted">
                  {lawsTotal
                    ? `${lawsOffset + 1}–${Math.min(lawsOffset + laws.length, lawsTotal)} / ${lawsTotal.toLocaleString("mn-MN")}`
                    : "—"}
                </span>
                <button
                  type="button"
                  className="mw-btn"
                  disabled={lawsLoading || lawsOffset + laws.length >= lawsTotal}
                  onClick={() => {
                    const next = lawsOffset + LAWS_PAGE;
                    setLawsOffset(next);
                    void loadLaws({ offset: next });
                  }}
                >
                  Дараах
                </button>
              </div>

              {failedLaws.length ? (
                <div className="mw-legal-bulk" style={{ marginTop: 18 }}>
                  <h3>Хассан / олдсонгүй хуулиуд · {lawsFailedCount || failedLaws.length}</h3>
                  <p className="mw-muted mw-legal-hint">
                    {lawsFailedSummary
                      ? `Акт олдсонгүй ${lawsFailedSummary.missing.toLocaleString("mn-MN")} · техникийн алдаа ${lawsFailedSummary.error.toLocaleString("mn-MN")} · гараар хассан ${lawsFailedSummary.skipped.toLocaleString("mn-MN")}. `
                      : null}
                    Эдгээр нь алдаатай гэж харагдах боловч ихэнхдээ legalinfo дээр устгагдсан/хоосон линк.
                    Дахин оролдох эсвэл үлдээнэ.
                  </p>
                  <ul className="mw-admin-list">
                    {failedLaws.map((law) => (
                      <li key={`failed-${law.law_id}`}>
                        <div className="mw-candidate-main">
                          <strong>{law.title || `Хууль #${law.law_id}`}</strong>
                          <span className="mw-muted">
                            #{law.law_id} ·{" "}
                            {law.reason === "skipped"
                              ? "хассан"
                              : law.reason === "missing"
                                ? "акт олдсонгүй"
                                : "алдаа"}{" "}
                            · {law.error || "—"}
                          </span>
                        </div>
                        <div className="mw-admin-row">
                          <button
                            type="button"
                            className="mw-btn"
                            disabled={Boolean(acting)}
                            onClick={() => void onLawRetry(law.law_id)}
                          >
                            Дахин оруулах
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {legalPreview?.present ? (
                <div className="mw-legal-bulk">
                  <h3>Бөөн импорт (файл)</h3>
                  <p className="mw-muted mw-legal-hint">
                    Шинэ найдвартай {legalPreview.trusted_count.toLocaleString("mn-MN")} · эргэлзээтэй{" "}
                    {legalPreview.doubt_count.toLocaleString("mn-MN")} — бүгд шалгах багц / Hunspell
                    дараалалд орно, шууд санд биш.
                  </p>
                  <button
                    type="button"
                    className="mw-btn"
                    disabled={acting === "legal"}
                    onClick={() => void onLegalImport()}
                  >
                    {acting === "legal" ? "Импортлож байна…" : "Файлын импорт"}
                  </button>
                </div>
              ) : null}
            </section>
          ) : null}

          {section === "review" ? (
            <AdminReviewPanel
              onDone={() => {
                void loadLists();
                void loadLexicon({ offset: 0 });
              }}
            />
          ) : null}

          {section === "pending" ? (
            <section className="mw-admin-card" id="pending-skipped">
              <h2>Алгассан үгс{pendingSkipped.length ? ` · ${pendingSkipped.length}` : ""}</h2>
              <p className="mw-muted">
                Чекбоксоор сонгосон үгс дээрх хүснэгтэд орно — хуулж аваад өөр газар шалгана.
              </p>
              {pendingSkipped.length === 0 ? (
                <p className="mw-muted">Хоосон</p>
              ) : (
                <>
                  <div className="mw-select-box">
                    <label className="mw-select-box-label" htmlFor="mw-pending-selected-words">
                      Сонгосон үгс
                      {pendingSelected.size ? ` · ${pendingSelected.size}` : ""}
                    </label>
                    <textarea
                      id="mw-pending-selected-words"
                      className="mw-selected-words"
                      value={pendingSelectedText()}
                      onChange={(event) => applyPendingSelectedText(event.target.value)}
                      rows={Math.min(12, Math.max(4, pendingSelected.size || 4))}
                      spellCheck={false}
                      placeholder="Сонгосон үгс энд гарна — хуулж аваад өөр газар шалгана"
                    />
                    <div className="mw-admin-row mw-lex-actions">
                      <button
                        type="button"
                        className="mw-btn"
                        onClick={() =>
                          setPendingSelected(new Set(pendingSkipped.map((item) => item.folded)))
                        }
                      >
                        Бүгдийг сонгох
                      </button>
                      <button
                        type="button"
                        className="mw-btn"
                        disabled={!pendingSelected.size}
                        onClick={() => setPendingSelected(new Set())}
                      >
                        Сонголт арилгах
                      </button>
                      <button
                        type="button"
                        className="mw-btn"
                        disabled={!pendingSelected.size}
                        onClick={() => void copyPendingSelected()}
                      >
                        {pendingCopied ? "Хуулсан" : "Хуулах"}
                      </button>
                      <button
                        type="button"
                        className="mw-btn-primary"
                        disabled={!pendingSelected.size || acting === "pending-approve"}
                        onClick={() => void onPendingApproveMany()}
                      >
                        {acting === "pending-approve"
                          ? "Нэмж байна…"
                          : pendingSelected.size
                            ? `Санд нэмэх · ${pendingSelected.size}`
                            : "Санд нэмэх"}
                      </button>
                      <button
                        type="button"
                        className="mw-btn"
                        disabled={!pendingSelected.size || acting === "pending-reject"}
                        onClick={() => void onPendingRejectMany()}
                      >
                        {acting === "pending-reject"
                          ? "Татгалзаж байна…"
                          : pendingSelected.size
                            ? `Татгалзах · ${pendingSelected.size}`
                            : "Татгалзах"}
                      </button>
                    </div>
                  </div>
                  <div className="mw-admin-scroll">
                    <ul className="mw-admin-list">
                      {pendingSkipped.map((item) => (
                        <li key={item.folded}>
                          <label className="mw-candidate-main">
                            <input
                              type="checkbox"
                              checked={pendingSelected.has(item.folded)}
                              onChange={(event) =>
                                togglePendingWord(item.folded, event.target.checked)
                              }
                            />
                            <strong>{item.word}</strong>
                            <span className="mw-muted">
                              {item.count}× · {formatWhen(item.updated_at)}
                            </span>
                          </label>
                          <div className="mw-admin-row">
                            <button
                              type="button"
                              className="mw-btn-primary"
                              disabled={acting === `p-ok-${item.folded}`}
                              onClick={() => void onPendingApprove(item.word)}
                            >
                              Санд нэмэх
                            </button>
                            <button
                              type="button"
                              className="mw-btn"
                              disabled={acting === `p-no-${item.folded}`}
                              onClick={() => void onPendingReject(item.word)}
                            >
                              Татгалзах
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </section>
          ) : null}

          {section === "added" ? (
            <section className="mw-admin-card" id="admin-added">
              <h2>
                Нэмсэн үгс
                {addedFiltered.length || addedWords.length
                  ? ` · ${addedFiltered.length.toLocaleString("mn-MN")}`
                  : ""}
              </h2>
              <form
                className="mw-lex-search mw-added-toolbar"
                onSubmit={(event) => {
                  event.preventDefault();
                  void loadAddedWords({
                    since: addedSince,
                    until: addedUntil,
                    q: addedQuery,
                  });
                }}
              >
                <label className="mw-added-date">
                  Эхлэх
                  <input
                    type="date"
                    value={addedSince}
                    onChange={(event) => setAddedSince(event.target.value)}
                  />
                </label>
                <label className="mw-added-date">
                  Дуусах
                  <input
                    type="date"
                    value={addedUntil}
                    onChange={(event) => setAddedUntil(event.target.value)}
                  />
                </label>
                <input
                  type="search"
                  value={addedQuery}
                  onChange={(event) => setAddedQuery(event.target.value)}
                  placeholder="Үгээр хайх…"
                />
                <button type="submit" className="mw-btn" disabled={addedLoading}>
                  {addedLoading ? "…" : "Шүүх"}
                </button>
                <button
                  type="button"
                  className="mw-btn"
                  disabled={addedLoading || (!addedSince && !addedUntil && !addedQuery)}
                  onClick={() => {
                    setAddedSince("");
                    setAddedUntil("");
                    setAddedQuery("");
                    void loadAddedWords({ since: "", until: "", q: "" });
                  }}
                >
                  Цэвэрлэх
                </button>
              </form>

              {addedFiltered.length === 0 ? (
                <p className="mw-muted">{addedLoading ? "Уншиж байна…" : "Олдсонгүй"}</p>
              ) : (
                <>
                  <div className="mw-added-toolbar-actions mw-admin-row">
                    <button
                      type="button"
                      className="mw-btn"
                      disabled={!addedFiltered.length}
                      onClick={() =>
                        setAddedSelected(new Set(addedFiltered.map((item) => item.folded)))
                      }
                    >
                      Бүгдийг сонгох
                    </button>
                    <button
                      type="button"
                      className="mw-btn"
                      disabled={!addedSelected.size}
                      onClick={() => setAddedSelected(new Set())}
                    >
                      Сонголт арилгах
                    </button>
                    <button
                      type="button"
                      className="mw-btn"
                      disabled={!addedSelected.size}
                      onClick={() => void copyAddedSelected()}
                    >
                      {addedCopied ? "Хуулсан" : "Хуулах"}
                      {addedSelected.size ? ` · ${addedSelected.size}` : ""}
                    </button>
                    <button
                      type="button"
                      className="mw-btn"
                      disabled={!addedSelected.size || acting === "added-remove"}
                      onClick={() => void onRemoveAddedFromLexicon()}
                    >
                      {acting === "added-remove"
                        ? "Хасаж байна…"
                        : addedSelected.size
                          ? `Сангаас устгах · ${addedSelected.size}`
                          : "Сангаас устгах"}
                    </button>
                  </div>
                  <div className="mw-admin-scroll mw-added-scroll">
                    <ul className="mw-admin-list mw-added-list">
                      {addedFiltered.map((item) => (
                        <li key={`${item.folded}-${item.added_at || "file"}`}>
                          <label className="mw-candidate-main">
                            <input
                              type="checkbox"
                              checked={addedSelected.has(item.folded)}
                              onChange={(event) =>
                                toggleAddedWord(item.folded, event.target.checked)
                              }
                            />
                            <span className="mw-added-word-block">
                              <strong>{item.word}</strong>
                              <time
                                className="mw-added-when"
                                dateTime={item.added_at || undefined}
                              >
                                {formatWhen(item.added_at)}
                              </time>
                            </span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  </div>
                  {addedSelected.size > 0 ? (
                    <div className="mw-select-box mw-added-select-box">
                      <label className="mw-select-box-label" htmlFor="mw-added-selected-words">
                        Сонгосон · {addedSelected.size}
                      </label>
                      <textarea
                        id="mw-added-selected-words"
                        className="mw-selected-words mw-added-selected-words"
                        value={addedSelectedText()}
                        onChange={(event) => applyAddedSelectedText(event.target.value)}
                        rows={3}
                        spellCheck={false}
                        placeholder="Сонгосон үгс — хуулж аваад өөр газар шалгана"
                      />
                    </div>
                  ) : null}
                </>
              )}
            </section>
          ) : null}

          {section === "feedback" ? (
            <section className="mw-admin-card" id="admin-feedback">
              <div className="mw-feedback-head">
                <div>
                  <h2>
                    Алдааны мэдэгдэл
                    {feedbackItems.length
                      ? ` · ${feedbackItems.length.toLocaleString("mn-MN")}`
                      : ""}
                  </h2>
                  <p className="mw-muted">
                    Хэрэглэгчдийн «Алдаа мэдэгдэх» хуудаснаас илгээсэн мэдээлэл. Шийдсэний
                    дараа устгана.
                  </p>
                </div>
                <div className="mw-admin-row">
                  <button
                    type="button"
                    className="mw-btn"
                    disabled={feedbackLoading || acting === "fb-purge"}
                    onClick={() => void loadFeedback()}
                  >
                    {feedbackLoading ? "…" : "Шинэчлэх"}
                  </button>
                  <button
                    type="button"
                    className="mw-btn"
                    disabled={feedbackLoading || acting === "fb-purge" || !feedbackItems.length}
                    onClick={() => void onPurgeTestFeedback()}
                    title="Smoke / deploy тест мэдэгдлийг автоматаар хасна"
                  >
                    {acting === "fb-purge" ? "Цэвэрлэж байна…" : "Тест цэвэрлэх"}
                  </button>
                </div>
              </div>
              {feedbackLoading && !feedbackItems.length ? (
                <p className="mw-muted">Уншиж байна…</p>
              ) : feedbackItems.length === 0 ? (
                <p className="mw-muted">Шийдэгдээгүй мэдэгдэл алга — цэвэр.</p>
              ) : (
                <div className="mw-admin-scroll mw-feedback-scroll">
                  <ul className="mw-admin-list mw-feedback-list">
                    {feedbackItems.map((item) => {
                      const isTest = /smoke\s*test|production smoke|тест мэдэгдэл/i.test(
                        `${item.message} ${item.word}`,
                      );
                      return (
                        <li key={item.id}>
                          <div className="mw-feedback-item">
                            <div className="mw-feedback-meta">
                              <span className="mw-feedback-cat">
                                {FEEDBACK_LABELS[item.category] ?? item.category}
                                {isTest ? (
                                  <span className="mw-feedback-test-tag"> тест</span>
                                ) : null}
                              </span>
                              <time dateTime={item.created_at || undefined}>
                                {formatWhen(item.created_at)}
                              </time>
                            </div>
                            {item.word ? (
                              <strong className="mw-feedback-word">{item.word}</strong>
                            ) : null}
                            <p className="mw-feedback-message">{item.message}</p>
                            <div className="mw-feedback-foot">
                              <div className="mw-feedback-extra mw-muted">
                                {item.email ? <span>{item.email}</span> : null}
                                {item.page ? <span>{item.page}</span> : null}
                              </div>
                              <button
                                type="button"
                                className="mw-btn"
                                disabled={acting === `fb-del-${item.id}`}
                                onClick={() => void onDeleteFeedback(item.id)}
                              >
                                {acting === `fb-del-${item.id}` ? "…" : "Устгах"}
                              </button>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </section>
          ) : null}

          {section === "users" ? (
            <section className="mw-admin-card" id="admin-users">
              <h2>Хэрэглэгчид{usersCounts.total ? ` · ${usersCounts.total}` : ""}</h2>
              <p className="mw-muted">
                Үнэгүй {usersCounts.free.toLocaleString("mn-MN")} · 3 сар{" "}
                {(usersCounts.pro_3m ?? 0).toLocaleString("mn-MN")} · 1 жил{" "}
                {(usersCounts.pro_year ?? 0).toLocaleString("mn-MN")} · Төлбөртэй{" "}
                {usersCounts.paid.toLocaleString("mn-MN")}
              </p>
              <form
                className="mw-lex-search mw-users-toolbar"
                onSubmit={(event) => {
                  event.preventDefault();
                  setUsersOffset(0);
                  void loadUsers({ q: usersQuery, plan: usersPlan, offset: 0 });
                }}
              >
                <input
                  type="search"
                  value={usersQuery}
                  onChange={(event) => setUsersQuery(event.target.value)}
                  placeholder="И-мэйл / нэр хайх…"
                />
                <select
                  value={usersPlan}
                  onChange={(event) => {
                    const next = event.target.value;
                    setUsersPlan(next);
                    setUsersOffset(0);
                    void loadUsers({ plan: next, offset: 0 });
                  }}
                  aria-label="Төлөвлөгөө шүүх"
                >
                  <option value="">Бүгд</option>
                  <option value="free">Үнэгүй</option>
                  <option value="paid">Төлбөртэй</option>
                  <option value="pro_3m">3 сар</option>
                  <option value="pro_year">1 жил</option>
                </select>
                <button type="submit" className="mw-btn" disabled={usersLoading}>
                  Хайх
                </button>
              </form>

              {usersLoading && !users.length ? (
                <p className="mw-muted">Уншиж байна…</p>
              ) : users.length === 0 ? (
                <p className="mw-muted">Хэрэглэгч олдсонгүй</p>
              ) : (
                <>
                  <div className="mw-admin-scroll mw-users-scroll">
                    <table className="mw-users-table">
                      <thead>
                        <tr>
                          <th>Хэрэглэгч</th>
                          <th>Төлөв</th>
                          <th>Дуусах</th>
                          <th>Сүүлд нэвтэрсэн</th>
                          <th>Сүүлд шалгасан</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {users.map((user) => (
                          <tr key={user.id}>
                            <td>
                              <div className="mw-user-cell">
                                {user.picture ? (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img src={user.picture} alt="" className="mw-user-avatar" />
                                ) : (
                                  <span className="mw-user-avatar is-empty" aria-hidden />
                                )}
                                <div>
                                  <strong>{user.name || "—"}</strong>
                                  <span className="mw-muted">{user.email || user.id}</span>
                                </div>
                              </div>
                            </td>
                            <td>
                              <span
                                className={
                                  user.is_paid ? "mw-user-pill is-paid" : "mw-user-pill is-free"
                                }
                              >
                                {user.status}
                              </span>
                            </td>
                            <td>
                              {user.plan_expires_at
                                ? formatWhen(user.plan_expires_at)
                                : user.is_paid
                                  ? "Хугацаагүй"
                                  : "—"}
                            </td>
                            <td>{formatWhen(user.last_login_at)}</td>
                            <td>{user.last_check_at ? formatWhen(user.last_check_at) : "—"}</td>
                            <td>
                              <button
                                type="button"
                                className="mw-btn"
                                onClick={() => {
                                  setEditingUser(user);
                                  const plan =
                                    user.plan === "pro_3m" || user.plan === "pro_year"
                                      ? user.plan
                                      : user.plan === "pro"
                                        ? "pro_year"
                                        : "free";
                                  setEditPlan(plan);
                                  setEditExpiry(
                                    user.plan_expires_at
                                      ? user.plan_expires_at.slice(0, 10)
                                      : "",
                                  );
                                }}
                              >
                                Засах
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="mw-lex-pager">
                    <button
                      type="button"
                      className="mw-btn"
                      disabled={usersOffset <= 0 || usersLoading}
                      onClick={() => {
                        const next = Math.max(0, usersOffset - USERS_PAGE);
                        setUsersOffset(next);
                        void loadUsers({ offset: next });
                      }}
                    >
                      Өмнөх
                    </button>
                    <span className="mw-muted">
                      {usersOffset + 1}–
                      {Math.min(usersOffset + users.length, usersTotal)} / {usersTotal}
                    </span>
                    <button
                      type="button"
                      className="mw-btn"
                      disabled={usersOffset + users.length >= usersTotal || usersLoading}
                      onClick={() => {
                        const next = usersOffset + USERS_PAGE;
                        setUsersOffset(next);
                        void loadUsers({ offset: next });
                      }}
                    >
                      Дараах
                    </button>
                  </div>
                </>
              )}

              {editingUser ? (
                <div className="mw-user-edit" role="dialog" aria-label="Төлөвлөгөө засах">
                  <h3>{editingUser.email || editingUser.name || editingUser.id}</h3>
                  <label>
                    Төлөвлөгөө
                    <select
                      value={editPlan}
                      onChange={(event) =>
                        setEditPlan(event.target.value as "free" | "pro_3m" | "pro_year")
                      }
                    >
                      <option value="free">Үнэгүй</option>
                      <option value="pro_3m">3 сар · ₮6,000</option>
                      <option value="pro_year">1 жил · ₮19,900</option>
                    </select>
                  </label>
                  {editPlan !== "free" ? (
                    <label>
                      Дуусах огноо (хоосон бол автоматаар)
                      <input
                        type="date"
                        value={editExpiry}
                        onChange={(event) => setEditExpiry(event.target.value)}
                      />
                    </label>
                  ) : null}
                  <div className="mw-admin-row">
                    <button
                      type="button"
                      className="mw-btn-primary"
                      disabled={acting === `user-${editingUser.id}`}
                      onClick={() => void onSaveUserPlan()}
                    >
                      Хадгалах
                    </button>
                    <button
                      type="button"
                      className="mw-btn"
                      disabled={
                        acting === `user-dev-${editingUser.id}` ||
                        !(editingUser.device_count && editingUser.device_count > 0)
                      }
                      onClick={() => void onClearUserDevices()}
                      title="Төхөөрөмжийн бүртгэлийг цэвэрлэж дахин нэвтрэх боломжтой болгоно"
                    >
                      Төхөөрөмж цэвэрлэх
                      {editingUser.device_count
                        ? ` (${editingUser.device_count}/2)`
                        : ""}
                    </button>
                    <button type="button" className="mw-btn" onClick={() => setEditingUser(null)}>
                      Болих
                    </button>
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}

          {section === "hunspell" ? (
            <section className="mw-admin-card" id="hunspell-candidates">
              <h2>
                Hunspell үгс
                {hunspellWords.length ? ` · ${hunspellWords.length}` : ""}
              </h2>

              <form className="mw-harvest-box" onSubmit={(event) => void onHarvest(event)}>
                <textarea
                  value={harvestText}
                  onChange={(event) => setHarvestText(event.target.value)}
                  rows={5}
                  placeholder="Энд бичнэ үү"
                />
                <button type="submit" className="mw-btn-primary" disabled={busy || !harvestText.trim()}>
                  {busy ? "Цуглуулж байна…" : "Цуглуулах"}
                </button>
              </form>
              <p className="mw-muted mw-hunspell-hint">
                Зөвхөн эргэлзээтэй үгс. Илт алдаатай / дүрмийн тодорхой алдаа энд орногүй.
              </p>

              {hunspellWords.length === 0 ? (
                <p className="mw-muted">Эргэлзээтэй үг алга</p>
              ) : (
                <>
                  <div className="mw-select-box">
                    <label className="mw-select-box-label" htmlFor="mw-selected-words">
                      Сонгосон{selectedHunspell.length ? ` · ${selectedHunspell.length}` : ""}
                    </label>
                    <textarea
                      id="mw-selected-words"
                      className="mw-selected-words"
                      value={selectedWordsText(selectedHunspell)}
                      onChange={(event) => applySelectedText(event.target.value)}
                      rows={4}
                    />
                    <div className="mw-admin-row mw-select-actions">
                      <button type="button" className="mw-btn" onClick={selectAllHunspell}>
                        Бүгдийг сонгох
                      </button>
                      <button
                        type="button"
                        className="mw-btn"
                        disabled={!selectedHunspell.length}
                        onClick={clearHunspellSelection}
                      >
                        Арилгах
                      </button>
                      <button
                        type="button"
                        className="mw-btn-primary"
                        disabled={!selectedHunspell.length || acting === "approve"}
                        onClick={() => void approveMany(selectedHunspell.map((item) => item.word))}
                      >
                        {acting === "approve"
                          ? "Нэмж байна…"
                          : selectedHunspell.length
                            ? `Санд нэмэх · ${selectedHunspell.length}`
                            : "Санд нэмэх"}
                      </button>
                      <button
                        type="button"
                        className="mw-btn"
                        disabled={!selectedHunspell.length || acting === "reject"}
                        onClick={() => void rejectMany(selectedHunspell.map((item) => item.word))}
                      >
                        {acting === "reject"
                          ? "Устгаж байна…"
                          : selectedHunspell.length
                            ? `Устгах · ${selectedHunspell.length}`
                            : "Устгах"}
                      </button>
                    </div>
                  </div>

                  {reliable.length ? (
                    <div className="mw-list-block">
                      <div className="mw-list-block-head">
                        <h3>Найдвартай · {reliable.length}</h3>
                        <button
                          type="button"
                          className="mw-btn"
                          onClick={() =>
                            setSelected((current) => {
                              const next = new Set(current);
                              for (const item of reliable) next.add(item.folded);
                              return next;
                            })
                          }
                        >
                          Энэ хэсгийг сонгох
                        </button>
                      </div>
                      <div className="mw-admin-scroll">
                        <ul className="mw-admin-list">
                          {reliable.map((item) => (
                            <li key={item.folded}>
                              <label className="mw-candidate-main">
                                <input
                                  type="checkbox"
                                  checked={selected.has(item.folded)}
                                  onChange={(event) => toggleWord(item.folded, event.target.checked)}
                                />
                                <strong title={item.reason}>{item.word}</strong>
                                <span className="mw-muted">{item.count}×</span>
                              </label>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : null}

                  {doubt.length ? (
                    <div className="mw-list-block">
                      <div className="mw-list-block-head">
                        <h3>Эргэлзээтэй · {doubt.length}</h3>
                        <button
                          type="button"
                          className="mw-btn"
                          onClick={() =>
                            setSelected((current) => {
                              const next = new Set(current);
                              for (const item of doubt) next.add(item.folded);
                              return next;
                            })
                          }
                        >
                          Энэ хэсгийг сонгох
                        </button>
                      </div>
                      <div className="mw-admin-scroll">
                        <ul className="mw-admin-list">
                          {doubt.map((item) => (
                            <li key={item.folded}>
                              <label className="mw-candidate-main">
                                <input
                                  type="checkbox"
                                  checked={selected.has(item.folded)}
                                  onChange={(event) => toggleWord(item.folded, event.target.checked)}
                                />
                                <strong title={item.reason}>{item.word}</strong>
                                <span className="mw-muted">
                                  {item.suggestion ? `→ ${item.suggestion}` : ""} {item.count}×
                                </span>
                              </label>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
