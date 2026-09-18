"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  adminApproveCandidates,
  adminHarvest,
  adminLogin,
  adminLogout,
  adminMe,
  adminOverview,
  adminRejectCandidates,
  type AdminAddedWord,
  type HunspellCandidate,
  type SiteOverview,
} from "@/lib/api";

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
  return "Ачаалж байна";
}

export function AdminApp() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [overview, setOverview] = useState<SiteOverview | null>(null);
  const [reliable, setReliable] = useState<HunspellCandidate[]>([]);
  const [doubt, setDoubt] = useState<HunspellCandidate[]>([]);
  const [addedWords, setAddedWords] = useState<AdminAddedWord[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [harvestText, setHarvestText] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [acting, setActing] = useState<string | null>(null);

  const applyOverview = useCallback((next: SiteOverview) => {
    setOverview(next);
    setReliable(next.candidates.reliable_items ?? []);
    setDoubt(next.candidates.doubt_items ?? []);
    setAddedWords(next.added_words ?? []);
  }, []);

  const loadLists = useCallback(async () => {
    const nextOverview = await adminOverview();
    applyOverview(nextOverview);
  }, [applyOverview]);

  useEffect(() => {
    void (async () => {
      try {
        const ok = await adminMe();
        setAuthed(ok);
        if (ok) await loadLists();
      } catch {
        setAuthed(false);
      } finally {
        setReady(true);
      }
    })();
  }, [loadLists]);

  async function onLogin(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await adminLogin(username, password);
      setAuthed(true);
      setPassword("");
      await loadLists();
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
    setSelected(new Set());
    setStatus("");
    setError(null);
  }

  function toggleWord(word: string, enabled: boolean) {
    setSelected((current) => {
      const next = new Set(current);
      if (enabled) next.add(word);
      else next.delete(word);
      return next;
    });
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

  async function rejectOne(word: string) {
    if (acting) return;
    setActing(word);
    setError(null);
    try {
      await adminRejectCandidates([word]);
      setStatus(`«${word}» хасагдлаа`);
      setSelected((current) => {
        const next = new Set(current);
        next.delete(word);
        return next;
      });
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
          ? `${result.queued} үг жагсаалтад орлоо/шинэчлэгдлээ`
          : "Шинэ үг олдсонгүй (бүгд аль хэдийн санд байсан эсвэл татгалзсан).",
      );
      await loadLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Цуглуулж чадсангүй");
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return (
      <div className="mw-admin-page">
        <div className="mw-admin">
          <p className="mw-muted">Уншиж байна…</p>
        </div>
      </div>
    );
  }

  if (!authed) {
    return (
      <div className="mw-admin-page">
        <div className="mw-admin">
          <form className="mw-admin-card mw-admin-login" onSubmit={(event) => void onLogin(event)}>
            <h1>Админ нэвтрэх</h1>
            <p className="mw-muted">Үгийн сан, Hunspell нэр дэвшигч, нэмсэн үгсийг эндээс хяана.</p>
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

  return (
    <div className="mw-admin-page">
      <header className="mw-admin-bar">
        <strong>MongolWrite · Админ</strong>
        <a className="mw-btn" href="/">
          Засварлагч
        </a>
        <button type="button" className="mw-btn" onClick={() => void loadLists()}>
          Шинэчлэх
        </button>
        <button type="button" className="mw-btn" onClick={() => void onLogout()}>
          Гарах
        </button>
      </header>
      <div className="mw-admin">
        {error ? <p className="mw-banner">{error}</p> : null}
        {status ? <p className="mw-admin-status">{status}</p> : null}

        {overview?.health ? (
          <section className="mw-admin-card">
            <div className="mw-health-head">
              <h2>Сайтын төлөв</h2>
              <span className={`mw-health-pill is-${overview.health.status}`}>
                {healthLabel(overview.health.status)}
              </span>
            </div>
            <p className="mw-health-advice">{overview.health.advice}</p>
            <p className="mw-muted">
              Сүүлийн 24 цагт {overview.health.checks_24h} шалгалт · хурд{" "}
              {overview.health.warm_p95_ms_24h || overview.health.p95_ms_24h}мс · ажилласан{" "}
              {formatUptime(overview.health.uptime_seconds)}
            </p>
          </section>
        ) : null}

        {overview ? (
          <section className="mw-admin-card">
            <h2>Тойм</h2>
            <div className="mw-overview-grid">
              <div className="mw-overview-tile">
                <span>Үгийн сан</span>
                <strong>{overview.lexicon.seed.toLocaleString("mn-MN")}</strong>
                <em>Hunspell {overview.lexicon.has_hunspell ? "бэлэн" : "байхгүй"}</em>
              </div>
              <div className="mw-overview-tile">
                <span>Hunspell нэр дэвшигч</span>
                <strong>{hunspellWords.length}</strong>
                <em>
                  Найдвартай {reliable.length} · эргэлзээтэй {doubt.length}
                </em>
              </div>
              <div className="mw-overview-tile">
                <span>Админаас нэмсэн</span>
                <strong>{addedWords.length.toLocaleString("mn-MN")}</strong>
                <em>Шинэ нь дээр харагдана</em>
              </div>
            </div>
          </section>
        ) : null}

        <section className="mw-admin-card" id="admin-added">
          <h2>Админаас нэмсэн үгс{addedWords.length ? ` · ${addedWords.length}` : ""}</h2>
          <p className="mw-muted">
            Админ санд оруулсан үгсийн жагсаалт. Хамгийн сүүлд нэмсэн нь дээр байна.
          </p>
          {addedWords.length === 0 ? (
            <p className="mw-muted">Одоогоор нэмсэн үг алга. Доорх жагсаалтаас зөвшөөрч нэмнэ.</p>
          ) : (
            <ul className="mw-admin-list">
              {addedWords.map((item) => (
                <li key={`${item.folded}-${item.added_at || "file"}`}>
                  <strong>{item.word}</strong>
                  <span className="mw-muted">{formatWhen(item.added_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="mw-admin-card" id="hunspell-candidates">
          <h2>
            Hunspell-ээс зөв гэсэн үгс
            {hunspellWords.length ? ` · ${hunspellWords.length}` : ""}
          </h2>
          <p className="mw-muted">
            Санд байхгүй боловч Hunspell зөв гэсэн (эсвэл текстэд гарсан шинэ) үгс. Эндээс санд
            оруулна.
          </p>

          <form className="mw-harvest-box" onSubmit={(event) => void onHarvest(event)}>
            <textarea
              value={harvestText}
              onChange={(event) => setHarvestText(event.target.value)}
              rows={4}
              placeholder="Текст буулгаад Hunspell нэр дэвшигч цуглуулна…"
            />
            <button type="submit" className="mw-btn-primary" disabled={busy || !harvestText.trim()}>
              {busy ? "Цуглуулж байна…" : "Жагсаалт руу цуглуулах"}
            </button>
          </form>

          {hunspellWords.length === 0 ? (
            <p className="mw-muted">
              Жагсаалт хоосон. Дээр текст буулгаад цуглуулна, эсвэл засварлагч дээр шалгалт хийнэ —
              автоматаар цугларна.
            </p>
          ) : (
            <>
              {reliable.length ? (
                <div className="mw-list-block">
                  <div className="mw-list-block-head">
                    <h3>Найдвартай · {reliable.length}</h3>
                    <div className="mw-admin-row">
                      <button
                        type="button"
                        className="mw-btn"
                        onClick={() => setSelected(new Set(reliable.map((item) => item.folded)))}
                      >
                        Бүгдийг сонгох
                      </button>
                      <button
                        type="button"
                        className="mw-btn-primary"
                        disabled={!selectedHunspell.length || acting === "approve"}
                        onClick={() =>
                          void approveMany(selectedHunspell.map((item) => item.word))
                        }
                      >
                        {acting === "approve"
                          ? "Нэмж байна…"
                          : `Сонгосон ${selectedHunspell.length}-ыг санд нэмэх`}
                      </button>
                    </div>
                  </div>
                  <ul className="mw-admin-list">
                    {reliable.map((item) => (
                      <li key={item.folded}>
                        <label className="mw-candidate-main">
                          <input
                            type="checkbox"
                            checked={selected.has(item.folded)}
                            onChange={(event) => toggleWord(item.folded, event.target.checked)}
                          />
                          <span>
                            <strong>{item.word}</strong>
                            <em className="mw-muted">
                              {" "}
                              · {item.count} удаа · {item.reason}
                            </em>
                          </span>
                        </label>
                        <button
                          type="button"
                          className="mw-btn"
                          disabled={acting === item.word}
                          onClick={() => void rejectOne(item.word)}
                        >
                          Татгалзах
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {doubt.length ? (
                <div className="mw-list-block">
                  <h3>Эргэлзээтэй · {doubt.length}</h3>
                  <ul className="mw-admin-list">
                    {doubt.map((item) => (
                      <li key={item.folded}>
                        <div>
                          <strong>{item.word}</strong>
                          <p className="mw-muted">
                            {item.reason}
                            {item.suggestion ? ` · санал: «${item.suggestion}»` : ""}
                            {` · ${item.count} удаа`}
                          </p>
                        </div>
                        <div className="mw-admin-row">
                          <button
                            type="button"
                            className="mw-btn-primary"
                            disabled={!!acting}
                            onClick={() => void approveMany([item.word])}
                          >
                            Санд нэмэх
                          </button>
                          <button
                            type="button"
                            className="mw-btn"
                            disabled={acting === item.word}
                            onClick={() => void rejectOne(item.word)}
                          >
                            Татгалзах
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
