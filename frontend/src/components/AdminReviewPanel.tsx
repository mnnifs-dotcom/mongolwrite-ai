"use client";

import { FormEvent, useCallback, useState } from "react";

import {
  adminReviewConfirm,
  adminReviewPreview,
  adminReviewWords,
  type ReviewBatch,
  type ReviewPreview,
  type ReviewWordItem,
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

function kindLabel(kinds: string[]): string {
  const map: Record<string, string> = {
    pending: "алгассан",
    hunspell: "hunspell",
    legalinfo: "legalinfo",
    added: "нэмсэн",
  };
  return kinds.map((k) => map[k] || k).join(" · ");
}

type Props = {
  onDone?: () => void;
};

export function AdminReviewPanel({ onDone }: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [since, setSince] = useState(today);
  const [until, setUntil] = useState(today);
  const [query, setQuery] = useState("");
  const [batch, setBatch] = useState<ReviewBatch | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [preview, setPreview] = useState<ReviewPreview | null>(null);
  const [removeSelected, setRemoveSelected] = useState<Set<string>>(new Set());
  const [rejectSelected, setRejectSelected] = useState<Set<string>>(new Set());
  const [keepOverride, setKeepOverride] = useState<Set<string>>(new Set());
  const [acting, setActing] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadBatch = useCallback(
    async (event?: FormEvent) => {
      event?.preventDefault();
      setLoading(true);
      setError(null);
      setMessage(null);
      setPreview(null);
      setPasteText("");
      setRemoveSelected(new Set());
      setRejectSelected(new Set());
      setKeepOverride(new Set());
      try {
        const data = await adminReviewWords({
          since: since || undefined,
          until: until || undefined,
          q: query || undefined,
        });
        setBatch(data);
        if (!data.count) setMessage("Сонгосон хугацаанд үг олдсонгүй");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Татаж чадсангүй");
      } finally {
        setLoading(false);
      }
    },
    [since, until, query],
  );

  async function copyAll() {
    if (!batch?.text) return;
    try {
      await navigator.clipboard.writeText(batch.text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setError("Хуулж чадсангүй");
    }
  }

  async function runPreview() {
    if (!batch) return;
    setActing("preview");
    setError(null);
    setMessage(null);
    try {
      const data = await adminReviewPreview({
        batch_words: batch.words,
        approved_text: pasteText,
      });
      setPreview(data);
      setRemoveSelected(new Set(data.remove_from_lexicon.map((w) => w.toLocaleLowerCase("mn"))));
      setRejectSelected(new Set(data.do_not_add.map((w) => w.toLocaleLowerCase("mn"))));
      setKeepOverride(new Set());
      setMessage(
        `Үлдээх ${data.keep_count} · сангаас хасах ${data.remove_from_lexicon.length} · оруулахгүй ${data.do_not_add.length}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Урьдчилсан харьцуулалт амжилтгүй");
    } finally {
      setActing("");
    }
  }

  async function runConfirm() {
    if (!preview) return;
    setActing("confirm");
    setError(null);
    try {
      // Words unchecked from remove/reject buckets are kept instead.
      const remove = preview.remove_from_lexicon.filter(
        (w) => removeSelected.has(w.toLocaleLowerCase("mn")) && !keepOverride.has(w.toLocaleLowerCase("mn")),
      );
      const reject = preview.do_not_add.filter(
        (w) => rejectSelected.has(w.toLocaleLowerCase("mn")) && !keepOverride.has(w.toLocaleLowerCase("mn")),
      );
      const keepFromDrops = [
        ...preview.remove_from_lexicon,
        ...preview.do_not_add,
      ].filter((w) => keepOverride.has(w.toLocaleLowerCase("mn")));
      const keep = [...preview.keep, ...preview.keep_extra, ...keepFromDrops];

      const result = await adminReviewConfirm({
        keep,
        remove_from_lexicon: remove,
        do_not_add: reject,
      });
      setMessage(
        `Баталгаажлаа · үлдээсэн ${result.kept_count} · устгасан ${result.removed_count} · цуцалсан ${result.rejected_count}`,
      );
      setPreview(null);
      setBatch(null);
      setPasteText("");
      onDone?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Баталгаажуулалт амжилтгүй");
    } finally {
      setActing("");
    }
  }

  function toggleSet(setter: (fn: (prev: Set<string>) => Set<string>) => void, word: string) {
    const folded = word.toLocaleLowerCase("mn");
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(folded)) next.delete(folded);
      else next.add(folded);
      return next;
    });
  }

  function markKeepInstead(word: string) {
    const folded = word.toLocaleLowerCase("mn");
    setKeepOverride((prev) => new Set(prev).add(folded));
    setRemoveSelected((prev) => {
      const next = new Set(prev);
      next.delete(folded);
      return next;
    });
    setRejectSelected((prev) => {
      const next = new Set(prev);
      next.delete(folded);
      return next;
    });
  }

  return (
    <section className="mw-admin-card" id="review-words">
      <h2>Шалгуулах үг татах</h2>
      <p className="mw-muted">
        Огноо сонгоод тухайн хугацаанд орсон алгассан, hunspell, legalinfo үгсийг нэг дор татна.
        Хуулж аваад гадна шалгаад зөвхөн үлдээх үгсээ буцааж paste хийнэ. Үлдээсэн үгс л үгийн санд
        нэмэгдэнэ — бусад нь оруулахгүй эсвэл сангаас хасагдана.
      </p>

      <form className="mw-admin-row" onSubmit={(event) => void loadBatch(event)}>
        <label className="mw-muted">
          Эхлэх
          <input type="date" value={since} onChange={(e) => setSince(e.target.value)} />
        </label>
        <label className="mw-muted">
          Дуусах
          <input type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
        </label>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Шүүлт (заавал биш)"
          aria-label="Үг хайх"
        />
        <button type="submit" className="mw-btn-primary" disabled={loading}>
          {loading ? "Татаж байна…" : "Шалгуулах үг татах"}
        </button>
      </form>

      {error ? <p className="mw-report-error">{error}</p> : null}
      {message ? <p className="mw-muted">{message}</p> : null}

      {batch && batch.count > 0 ? (
        <>
          <div className="mw-select-box">
            <label className="mw-select-box-label" htmlFor="mw-review-batch">
              Татсан үгс · {batch.count}
            </label>
            <textarea
              id="mw-review-batch"
              className="mw-selected-words"
              value={batch.text}
              readOnly
              rows={Math.min(14, Math.max(6, Math.ceil(batch.count / 4)))}
              spellCheck={false}
            />
            <div className="mw-admin-row mw-lex-actions">
              <button type="button" className="mw-btn" onClick={() => void copyAll()}>
                {copied ? "Хуулсан" : "Бүгдийг хуулах"}
              </button>
            </div>
          </div>

          <div className="mw-admin-scroll" style={{ maxHeight: 220 }}>
            <ul className="mw-admin-list">
              {batch.items.slice(0, 200).map((item: ReviewWordItem) => (
                <li key={item.folded}>
                  <div className="mw-candidate-main">
                    <strong>{item.word}</strong>
                    <span className="mw-muted">
                      {kindLabel(item.kinds)} · {formatWhen(item.when)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
            {batch.count > 200 ? (
              <p className="mw-muted">…болон дахин {batch.count - 200} үг (бүгд textarea-д бий)</p>
            ) : null}
          </div>

          <div className="mw-select-box" style={{ marginTop: 16 }}>
            <label className="mw-select-box-label" htmlFor="mw-review-paste">
              Зөвшөөрсөн үгс (paste)
            </label>
            <textarea
              id="mw-review-paste"
              className="mw-selected-words"
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              rows={8}
              spellCheck={false}
              placeholder="Зөвхөн санд үлдээх/оруулах үгсээ энд буулгана"
            />
            <div className="mw-admin-row mw-lex-actions">
              <button
                type="button"
                className="mw-btn-primary"
                disabled={!pasteText.trim() || acting === "preview"}
                onClick={() => void runPreview()}
              >
                {acting === "preview" ? "Харьцуулж байна…" : "Урьдчилан харах"}
              </button>
            </div>
          </div>
        </>
      ) : null}

      {preview ? (
        <div className="mw-legal-bulk" style={{ marginTop: 18 }}>
          <h3>Урьдчилсан үр дүн</h3>
          <p className="mw-muted">
            Үлдээх {preview.keep_count} · сангаас хасах {preview.remove_from_lexicon.length} ·
            оруулахгүй {preview.do_not_add.length}. Доороос заримыг нь үлдээж болно.
          </p>

          {preview.remove_from_lexicon.length ? (
            <>
              <h4>Сангаас устгах гэж байна</h4>
              <ul className="mw-admin-list">
                {preview.remove_from_lexicon.map((word) => {
                  const folded = word.toLocaleLowerCase("mn");
                  const kept = keepOverride.has(folded);
                  return (
                    <li key={`rm-${folded}`}>
                      <label className="mw-candidate-main">
                        <input
                          type="checkbox"
                          checked={removeSelected.has(folded) && !kept}
                          disabled={kept}
                          onChange={() => toggleSet(setRemoveSelected, word)}
                        />
                        <strong>{word}</strong>
                      </label>
                      <button type="button" className="mw-btn" onClick={() => markKeepInstead(word)}>
                        {kept ? "Үлдээнэ" : "Санд үлдээх"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : null}

          {preview.do_not_add.length ? (
            <>
              <h4>Санд оруулахгүй / цуцлах гэж байна</h4>
              <ul className="mw-admin-list">
                {preview.do_not_add.map((word) => {
                  const folded = word.toLocaleLowerCase("mn");
                  const kept = keepOverride.has(folded);
                  return (
                    <li key={`na-${folded}`}>
                      <label className="mw-candidate-main">
                        <input
                          type="checkbox"
                          checked={rejectSelected.has(folded) && !kept}
                          disabled={kept}
                          onChange={() => toggleSet(setRejectSelected, word)}
                        />
                        <strong>{word}</strong>
                      </label>
                      <button type="button" className="mw-btn" onClick={() => markKeepInstead(word)}>
                        {kept ? "Үлдээнэ" : "Санд үлдээх"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : null}

          <div className="mw-admin-row mw-lex-actions">
            <button
              type="button"
              className="mw-btn-primary"
              disabled={acting === "confirm"}
              onClick={() => void runConfirm()}
            >
              {acting === "confirm" ? "Хадгалж байна…" : "Баталгаажуулах"}
            </button>
            <button type="button" className="mw-btn" onClick={() => setPreview(null)}>
              Буцах
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
