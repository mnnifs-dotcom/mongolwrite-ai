"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import {
  adminApproveCandidates,
  adminApprovePending,
  adminHarvest,
  adminLegalImport,
  adminLegalPreview,
  adminLexiconRemove,
  adminLexiconWords,
  adminLogin,
  adminLogout,
  adminMe,
  adminOverview,
  adminRejectCandidates,
  adminRejectPending,
  type AdminAddedWord,
  type HunspellCandidate,
  type LegalImportPreview,
  type LexiconLetter,
  type PendingSkippedWord,
  type SiteOverview,
} from "@/lib/api";
import { BrandLogo } from "@/components/BrandLogo";

type AdminSection =
  | "overview"
  | "lexicon"
  | "hunspell"
  | "pending"
  | "added"
  | "legal"
  | "health";

const PAGE_SIZE = 80;

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
  const [pendingSkipped, setPendingSkipped] = useState<PendingSkippedWord[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [harvestText, setHarvestText] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [acting, setActing] = useState<string | null>(null);
  const [legalPreview, setLegalPreview] = useState<LegalImportPreview | null>(null);
  const [section, setSection] = useState<AdminSection>("lexicon");
  const [lexQuery, setLexQuery] = useState("");
  const [lexLetter, setLexLetter] = useState("");
  const [lexOffset, setLexOffset] = useState(0);
  const [lexWords, setLexWords] = useState<string[]>([]);
  const [lexTotal, setLexTotal] = useState(0);
  const [lexLetters, setLexLetters] = useState<LexiconLetter[]>([]);
  const [lexSelected, setLexSelected] = useState<Set<string>>(new Set());
  const [lexLoading, setLexLoading] = useState(false);

  const applyOverview = useCallback((next: SiteOverview) => {
    setOverview(next);
    setReliable(next.candidates.reliable_items ?? []);
    setDoubt(next.candidates.doubt_items ?? []);
    setAddedWords(next.added_words ?? []);
    setPendingSkipped(next.pending_skipped ?? []);
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
    setSelected(new Set());
    setStatus("");
    setError(null);
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
        `Legalinfo: санд ${result.added_to_lexicon} · админд ${result.queued_for_admin}`,
      );
      await loadLists();
      await loadLexicon({ offset: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Импорт амжилтгүй");
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
    {
      id: "legal",
      label: "legalinfo.mn",
      count: legalPreview?.trusted_count,
      hide: !legalPreview?.present,
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
                {overview.health.checks_24h} шалгалт ·{" "}
                {overview.health.warm_p95_ms_24h || overview.health.p95_ms_24h}мс ·{" "}
                {formatUptime(overview.health.uptime_seconds)}
              </p>
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
                      ? `Hunspell ${(overview.lexicon.hunspell_stems / 1000).toFixed(0)} мянга`
                      : overview.lexicon.has_hunspell
                        ? "Hunspell"
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

          {section === "legal" && legalPreview?.present ? (
            <section className="mw-admin-card" id="legalinfo-import">
              <h2>legalinfo.mn үгс</h2>
              <p className="mw-muted">
                Шинэ найдвартай {legalPreview.trusted_count.toLocaleString("mn-MN")} · админ шалгах{" "}
                {legalPreview.doubt_count.toLocaleString("mn-MN")}
              </p>
              {legalPreview.corpus?.articles ? (
                <p className="mw-muted">
                  {(legalPreview.corpus.articles ?? 0).toLocaleString("mn-MN")} хуулийн өгүүллээс ·{" "}
                  {(legalPreview.corpus.already_in_seed ?? 0).toLocaleString("mn-MN")} үг аль хэдийн
                  тольд байсан
                </p>
              ) : null}
              <div className="mw-admin-row">
                <button
                  type="button"
                  className="mw-btn-primary"
                  disabled={acting === "legal"}
                  onClick={() => void onLegalImport()}
                >
                  {acting === "legal" ? "Импортлож байна…" : "Импортлох"}
                </button>
              </div>
            </section>
          ) : null}

          {section === "pending" ? (
            <section className="mw-admin-card" id="pending-skipped">
              <h2>Алгассан үгс{pendingSkipped.length ? ` · ${pendingSkipped.length}` : ""}</h2>
              {pendingSkipped.length === 0 ? (
                <p className="mw-muted">Хоосон</p>
              ) : (
                <div className="mw-admin-scroll">
                  <ul className="mw-admin-list">
                    {pendingSkipped.map((item) => (
                      <li key={item.folded}>
                        <div className="mw-candidate-main">
                          <strong>{item.word}</strong>
                          <span className="mw-muted">
                            {item.count}× · {formatWhen(item.updated_at)}
                          </span>
                        </div>
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
              )}
            </section>
          ) : null}

          {section === "added" ? (
            <section className="mw-admin-card" id="admin-added">
              <h2>Нэмсэн үгс{addedWords.length ? ` · ${addedWords.length}` : ""}</h2>
              {addedWords.length === 0 ? (
                <p className="mw-muted">Хоосон</p>
              ) : (
                <div className="mw-admin-scroll">
                  <ul className="mw-admin-list">
                    {addedWords.map((item) => (
                      <li key={`${item.folded}-${item.added_at || "file"}`}>
                        <strong>{item.word}</strong>
                        <span className="mw-muted">{formatWhen(item.added_at)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
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
                  placeholder="Текст…"
                />
                <button type="submit" className="mw-btn-primary" disabled={busy || !harvestText.trim()}>
                  {busy ? "Цуглуулж байна…" : "Цуглуулах"}
                </button>
              </form>

              {hunspellWords.length === 0 ? (
                <p className="mw-muted">Хоосон</p>
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
