"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  adminAddedWords,
  adminApproveCandidates,
  adminCandidates,
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

  const loadLists = useCallback(async () => {
    const [nextOverview, nextReliable, nextDoubt, nextAdded] = await Promise.all([
      adminOverview(),
      adminCandidates("reliable"),
      adminCandidates("doubt"),
      adminAddedWords(),
    ]);
    setOverview(nextOverview);
    setReliable(nextReliable.items);
    setDoubt(nextDoubt.items);
    setAddedWords(nextAdded.items);
  }, []);

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
          ? `${result.queued} шинэ/шинэчилсэн нэр дэвшигч`
          : "Шинэ нэр дэвшигч олдсонгүй.",
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
            <p className="mw-muted">Hunspell нэр дэвшигч үгсийг эндээс хяана.</p>
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

  const selectedReliable = reliable.filter((item) => selected.has(item.folded));

  return (
    <div className="mw-admin-page">
      <header className="mw-admin-bar">
        <strong>MongolWrite · Админ</strong>
        <a className="mw-btn" href="/">
          Засварлагч
        </a>
        <button type="button" className="mw-btn" onClick={() => void onLogout()}>
          Гарах
        </button>
      </header>
      <div className="mw-admin">
        {error ? <p className="mw-banner">{error}</p> : null}
        {status ? <p className="mw-admin-status">{status}</p> : null}

        {overview ? (
          <section className="mw-admin-card">
            <div className="mw-health-head">
              <h2>Сайтын төлөв</h2>
              {overview.health ? (
                <span className={`mw-health-pill is-${overview.health.status}`}>
                  {healthLabel(overview.health.status)}
                </span>
              ) : null}
            </div>
            {overview.health ? (
              <>
                <p className="mw-health-advice">{overview.health.advice}</p>
                <p className="mw-muted">
                  Сүүлийн 24 цагт {overview.health.checks_24h} шалгалт · дундаж хурд{" "}
                  {overview.health.warm_p95_ms_24h || overview.health.p95_ms_24h}мс · ажилласан{" "}
                  {formatUptime(overview.health.uptime_seconds)}
                  {overview.health.slow_24h
                    ? ` · удаан ${overview.health.slow_24h}`
                    : ""}
                </p>
                <button type="button" className="mw-btn" onClick={() => void loadLists()}>
                  Дахин харах
                </button>
              </>
            ) : null}
          </section>
        ) : null}

        {overview ? (
          <section className="mw-admin-card">
            <h2>Ерөнхий мэдээлэл</h2>
            <div className="mw-overview-grid">
              <div className="mw-overview-tile">
                <span>Үгийн сан (seed)</span>
                <strong>{overview.lexicon.seed.toLocaleString("mn-MN")}</strong>
                <em>Hunspell {overview.lexicon.has_hunspell ? "бэлэн" : "байхгүй"}</em>
              </div>
              <div className="mw-overview-tile">
                <span>Найдвартай</span>
                <strong>{overview.candidates.reliable}</strong>
                <em>Админ зөвшөөрсний дараа санд орно</em>
              </div>
              <div className="mw-overview-tile">
                <span>Эргэлзээтэй</span>
                <strong>{overview.candidates.doubt}</strong>
                <em>Hunspell зөвшөөрсөн ч давтамж бага</em>
              </div>
              <div className="mw-overview-tile">
                <span>Админ нэмсэн</span>
                <strong>{(overview.lexicon.admin_added ?? addedWords.length).toLocaleString("mn-MN")}</strong>
                <em>Сүүлд нэмснээс эхлэн харна</em>
              </div>
            </div>
          </section>
        ) : null}

        <section className="mw-admin-card">
          <h2>Сүүлд нэмсэн үгс{addedWords.length ? ` · ${addedWords.length}` : ""}</h2>
          <p className="mw-muted">Админаас санд оруулсан үгс. Шинээр нэмсэн нь хамгийн дээр.</p>
          {addedWords.length === 0 ? (
            <p className="mw-muted">Одоогоор админ нэмсэн үг алга.</p>
          ) : (
            <ul className="mw-admin-list">
              {addedWords.map((item) => (
                <li key={`${item.folded}-${item.added_at}`}>
                  <strong>{item.word}</strong>
                  <span className="mw-muted">{formatWhen(item.added_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="mw-admin-card">
          <h2>Найдвартай шинэ үгс{reliable.length ? ` · ${reliable.length}` : ""}</h2>
          <p className="mw-muted">
            Санд байхгүй, Hunspell зөв гэсэн, Википедиа дээр түгээмэл үгс. Багцаар санд нэмнэ.
          </p>
          {reliable.length === 0 ? (
            <p className="mw-muted">Одоогоор найдвартай нэр дэвшигч алга.</p>
          ) : (
            <>
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
                  disabled={!selectedReliable.length || acting === "approve"}
                  onClick={() => void approveMany(selectedReliable.map((item) => item.word))}
                >
                  {acting === "approve"
                    ? "Нэмж байна…"
                    : `Сонгосон ${selectedReliable.length} үгийг санд нэмэх`}
                </button>
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
                        <em className="mw-muted"> · {item.count} удаа · {item.reason}</em>
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
            </>
          )}
        </section>

        <section className="mw-admin-card">
          <h2>Эргэлзээтэй (Hunspell){doubt.length ? ` · ${doubt.length}` : ""}</h2>
          <p className="mw-muted">
            Hunspell зөвшөөрсөн боловч давтамж бага эсвэл ойрхон илүү түгээмэл хувилбар байгаа.
          </p>
          {doubt.length === 0 ? (
            <p className="mw-muted">Эргэлзээтэй нэр дэвшигч алга.</p>
          ) : (
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
          )}
        </section>

        <section className="mw-admin-card">
          <h2>Текстээс цуглуулах</h2>
          <p className="mw-muted">
            Шалгалт бүрт автоматаар цугларна. Эндээс нэмэлт текст буулгаад шууд harvest хийж болно.
          </p>
          <form onSubmit={(event) => void onHarvest(event)}>
            <textarea
              value={harvestText}
              onChange={(event) => setHarvestText(event.target.value)}
              rows={6}
              placeholder="Монгол текст…"
            />
            <button type="submit" className="mw-btn-primary" disabled={busy || !harvestText.trim()}>
              {busy ? "Цуглуулж байна…" : "Нэр дэвшигч цуглуулах"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
