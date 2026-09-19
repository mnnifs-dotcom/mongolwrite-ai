"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import {
  checkText,
  checkTextWithAI,
  getSettings,
  importDocument,
  improveText,
  skipSpellingWord,
} from "@/lib/api";
import { cyrillicToBichig } from "@/lib/bichig";
import { IssueHighlight, setIssueDecorations } from "@/lib/highlight";
import { mapRange, plainTextFromDoc } from "@/lib/offsets";
import { type Correction } from "@/lib/types";
import { AuthButton } from "@/components/AuthButton";
import { BrandLogo } from "@/components/BrandLogo";

const STYLE = "government_official";
const DOC_TYPE = "official_letter";

const SAMPLE =
  "Манай байгууллагаас ирүүлсэн хүсэлтийг хүлээн авч, танилцан холбогдох арга хэмжээ авч ажиллана уу.\n\nШинжилгээний хариу  одөр ирүүлсэн болно. байгууллагаaс дахин хүсэлт хүсэлт ирүүлнэ үү.\n\nЯгаад өдрээс хойш хариу ирүүлээгүй байна үү. Гэхмэт ажиллажбайна.";

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function textToHtml(text: string): string {
  return text
    .split("\n")
    .map((line) => `<p>${escapeHtml(line) || "<br>"}</p>`)
    .join("");
}

function remapCorrections(
  items: Correction[],
  oldText: string,
  newText: string,
): Correction[] {
  if (oldText === newText) return items;
  let start = 0;
  const shared = Math.min(oldText.length, newText.length);
  while (start < shared && oldText[start] === newText[start]) start += 1;
  let oldEnd = oldText.length;
  let newEnd = newText.length;
  while (oldEnd > start && newEnd > start && oldText[oldEnd - 1] === newText[newEnd - 1]) {
    oldEnd -= 1;
    newEnd -= 1;
  }
  const delta = newText.length - oldText.length;
  return items.flatMap((row) => {
    let next = row;
    if (row.end <= start) next = row;
    else if (row.start >= oldEnd) {
      next = { ...row, start: row.start + delta, end: row.end + delta };
    } else {
      return [];
    }
    if (newText.slice(next.start, next.end) !== next.original_text) return [];
    return [next];
  });
}

function locateOriginal(
  text: string,
  original: string,
  hint: number,
): { start: number; end: number } | null {
  if (!original) return null;
  if (text.slice(hint, hint + original.length) === original) {
    return { start: hint, end: hint + original.length };
  }
  let best = -1;
  let bestDist = Number.POSITIVE_INFINITY;
  let from = 0;
  while (from <= text.length) {
    const idx = text.indexOf(original, from);
    if (idx < 0) break;
    const dist = Math.abs(idx - hint);
    if (dist < bestDist) {
      best = idx;
      bestDist = dist;
    }
    from = idx + 1;
  }
  if (best < 0) return null;
  return { start: best, end: best + original.length };
}

function suggestionList(item: Correction): string[] {
  const words = [item.suggested_text, ...(item.suggestions ?? [])];
  return [...new Set(words.filter((word) => word && word !== item.original_text))];
}

function canFix(item: Correction): boolean {
  if (item.rule_id === "unknown_word") return false;
  return item.suggested_text !== item.original_text;
}

function dismissKey(item: Correction): string {
  return `${item.original_text.toLocaleLowerCase("mn")}|${item.rule_id}`;
}

function statusLabel(items: Correction[]): string {
  if (!items.length) return "Алдаагүй";
  return `${items.length} зөв бичгийн алдаа`;
}

function SuggestionPopover({
  item,
  onApply,
  onDismiss,
  onClose,
}: {
  item: Correction;
  onApply: (item: Correction, word?: string) => void;
  onDismiss: (id: string) => void;
  onClose: () => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  const place = useCallback(() => {
    const mark = document.querySelector(`.mw-prose [data-issue-id="${item.id}"]`);
    if (!(mark instanceof HTMLElement)) return;
    const rect = mark.getBoundingClientRect();
    const width = 240;
    const left = Math.min(Math.max(12, rect.left), window.innerWidth - width - 12);
    const top = rect.bottom + 6;
    setPos({ top, left });
  }, [item.id]);

  useLayoutEffect(() => {
    place();
    const onMove = () => place();
    window.addEventListener("scroll", onMove, true);
    window.addEventListener("resize", onMove);
    return () => {
      window.removeEventListener("scroll", onMove, true);
      window.removeEventListener("resize", onMove);
    };
  }, [place]);

  useEffect(() => {
    const onDoc = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (box.current?.contains(target)) return;
      if (target.closest("[data-issue-id]")) return;
      if (target.closest("[data-card-id]")) return;
      onClose();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [item.id, onClose]);

  const words = suggestionList(item);
  const removeOnly = !words.length && item.suggested_text === "" && item.rule_id !== "unknown_word";

  return createPortal(
    <div
      ref={box}
      className="mw-pop"
      style={{ top: pos.top, left: pos.left }}
      role="dialog"
      aria-label="Санал болгох үгс"
    >
      <p className="mw-pop-word">
        <s>{item.original_text}</s>
      </p>
      {words.length ? (
        <>
          <p className="mw-pop-label">Санал болгох үгс</p>
          <div className="mw-pop-sugs">
            {words.map((word, index) => (
              <button
                key={word}
                type="button"
                className={index === 0 ? "mw-sug best" : "mw-sug"}
                onClick={() => onApply(item, word)}
              >
                {word}
              </button>
            ))}
          </div>
        </>
      ) : removeOnly ? (
        <button type="button" className="mw-sug best" onClick={() => onApply(item, "")}>
          Хасах
        </button>
      ) : null}
      <button type="button" className="mw-pop-skip" onClick={() => onDismiss(item.id)}>
        Алгасах
      </button>
    </div>,
    document.body,
  );
}

export function EditorApp() {
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [counts, setCounts] = useState({ words: 0, chars: 0 });
  const [maxChars, setMaxChars] = useState(100_000);
  const [error, setError] = useState<string | null>(null);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [empty, setEmpty] = useState(true);
  const [shown, setShown] = useState(false);
  const [checking, setChecking] = useState(false);
  const [showBichig, setShowBichig] = useState(false);
  const [draft, setDraft] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const checkSeq = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const lastLen = useRef(0);
  const lastText = useRef("");
  const aiEnabledRef = useRef(false);
  const dismissed = useRef(new Set<string>());
  const shownRef = useRef(false);
  const applying = useRef(false);
  const pending = useRef<{ text: string; result: Awaited<ReturnType<typeof checkText>> } | null>(
    null,
  );
  const inflight = useRef<Promise<void> | null>(null);
  const correctionsRef = useRef<Correction[]>([]);
  aiEnabledRef.current = aiEnabled;
  correctionsRef.current = corrections;

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        blockquote: false,
        horizontalRule: false,
        bulletList: false,
        orderedList: false,
        listItem: false,
        code: false,
      }),
      IssueHighlight,
    ],
    content: "<p></p>",
    editorProps: {
      attributes: {
        class: "mw-prose",
        spellcheck: "false",
      },
    },
  });

  const applyResult = useCallback((result: Awaited<ReturnType<typeof checkText>>) => {
    const kept = result.corrections.filter((item) => !dismissed.current.has(dismissKey(item)));
    setCorrections(kept);
    setCounts({ words: result.word_count, chars: result.character_count });
    if (typeof result.ai_enabled === "boolean") setAiEnabled(result.ai_enabled);
    setError(null);
    setActiveId((current) => (kept.some((item) => item.id === current) ? current : null));
  }, []);

  const hideMarks = useCallback(() => {
    shownRef.current = false;
    setShown(false);
    setChecking(false);
    setCorrections([]);
    setActiveId(null);
  }, []);

  const runCheck = useCallback(async (text: string) => {
    const seq = ++checkSeq.current;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    if (!text.trim()) {
      pending.current = null;
      setCounts({ words: 0, chars: text.length });
      return;
    }
    setCounts({
      words: text.trim() ? text.trim().split(/\s+/).length : 0,
      chars: text.length,
    });
    const work = (async () => {
      try {
        const result = await checkText(text, {
          document_type: DOC_TYPE,
          style: STYLE,
          signal: ac.signal,
        });
        if (seq !== checkSeq.current) return;
        pending.current = { text, result };
        if (shownRef.current) applyResult(result);
      } catch (err) {
        if (seq !== checkSeq.current) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (err instanceof Error && err.name === "AbortError") return;
        if (shownRef.current) {
          setError(err instanceof Error ? err.message : "Алдаа");
        }
      }
    })();
    inflight.current = work;
    await work;
  }, [applyResult]);

  const runThink = useCallback(async (text: string) => {
    if (!text.trim() || !aiEnabledRef.current || !shownRef.current) return;
    const seq = checkSeq.current;
    try {
      const result = await checkTextWithAI(text, {
        document_type: DOC_TYPE,
        style: STYLE,
      });
      if (seq !== checkSeq.current || !shownRef.current) return;
      pending.current = { text, result };
      applyResult(result);
    } catch {
      /* Fast check already showed a result. */
    }
  }, [applyResult]);

  const showErrors = useCallback(async () => {
    if (!editor || checking) return;
    const text = plainTextFromDoc(editor.state.doc);
    if (!text.trim()) {
      setError(null);
      return;
    }
    shownRef.current = true;
    setShown(true);
    setError(null);
    setChecking(true);
    const started = Date.now();
    try {
      const ready = pending.current;
      if (ready && ready.text === text) {
        applyResult(ready.result);
        if (aiEnabledRef.current) void runThink(text);
        return;
      }
      await runCheck(text);
      const next = pending.current;
      if (next && next.text === text && shownRef.current) {
        applyResult(next.result);
      }
      if (aiEnabledRef.current) void runThink(text);
    } finally {
      const wait = 700 - (Date.now() - started);
      if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
      setChecking(false);
    }
  }, [applyResult, checking, editor, runCheck, runThink]);

  useEffect(() => {
    if (!editor) return;
    const schedule = ({ transaction }: { transaction: { docChanged: boolean } }) => {
      if (!transaction.docChanged) return;
      abortRef.current?.abort();
      checkSeq.current += 1;
      const text = plainTextFromDoc(editor.state.doc);
      setEmpty(!text.trim());
      setDraft(text);
      setCounts({
        words: text.trim() ? text.trim().split(/\s+/).length : 0,
        chars: text.length,
      });
      if (!text.trim()) {
        lastText.current = text;
        lastLen.current = text.length;
        if (shownRef.current) hideMarks();
        return;
      }
      if (!applying.current && shownRef.current) {
        const next = remapCorrections(correctionsRef.current, lastText.current, text);
        correctionsRef.current = next;
        setCorrections(next);
        setActiveId((id) => (id && next.some((item) => item.id === id) ? id : null));
      }
      lastText.current = text;
      if (timer.current) clearTimeout(timer.current);
      const jumped = Math.abs(text.length - lastLen.current) > 20;
      lastLen.current = text.length;
      timer.current = setTimeout(() => {
        void runCheck(text);
      }, jumped ? 0 : 40);
    };
    editor.on("update", schedule);
    const text = plainTextFromDoc(editor.state.doc);
    lastText.current = text;
    lastLen.current = text.length;
    void runCheck(text);
    return () => {
      editor.off("update", schedule);
      if (timer.current) clearTimeout(timer.current);
    };
  }, [editor, hideMarks, runCheck]);

  useEffect(() => {
    if (!editor) return;
    setIssueDecorations(editor, corrections, activeId);
  }, [editor, corrections, activeId]);

  useEffect(() => {
    void getSettings().then((result) => {
      setAiEnabled(result.ai_enabled);
      if (result.check_max_chars && result.check_max_chars > 0) {
        setMaxChars(result.check_max_chars);
      }
    });
  }, []);

  useEffect(() => {
    const onSelect = (event: Event) => {
      const id = (event as CustomEvent<string>).detail;
      setActiveId((current) => (current === id ? null : id));
    };
    window.addEventListener("mw-select-issue", onSelect);
    return () => window.removeEventListener("mw-select-issue", onSelect);
  }, []);

  useEffect(() => {
    if (!activeId) return;
    document.querySelector(`.mw-prose [data-issue-id="${activeId}"]`)?.scrollIntoView({
      block: "nearest",
      behavior: "smooth",
    });
    document.querySelector(`[data-card-id="${activeId}"]`)?.scrollIntoView({
      block: "nearest",
      behavior: "smooth",
    });
  }, [activeId]);

  const visible = corrections;
  const bichigText = useMemo(() => (showBichig ? cyrillicToBichig(draft) : ""), [showBichig, draft]);

  const activeItem = useMemo(
    () => corrections.find((item) => item.id === activeId) ?? null,
    [corrections, activeId],
  );

  const fixableCount = useMemo(
    () => corrections.filter(canFix).length,
    [corrections],
  );

  function closeMenu() {
    setMenuOpen(false);
  }

  useEffect(() => {
    if (!menuOpen) return;
    const onDoc = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  function apply(item: Correction, replacement?: string) {
    const suggested = replacement ?? item.suggested_text;
    if (!editor || suggested === item.original_text) return;
    const text = plainTextFromDoc(editor.state.doc);
    const found = locateOriginal(text, item.original_text, item.start);
    if (!found) {
      setError("Энэ үгийг текст дээр олохгүй байна.");
      return;
    }
    const range = mapRange(editor.state.doc, found.start, found.end);
    if (!range) {
      setError("Энэ үгийг текст дээр олохгүй байна.");
      return;
    }
    const delta = suggested.length - item.original_text.length;
    applying.current = true;
    editor.view.dispatch(
      editor.state.tr.insertText(suggested, range.from, range.to),
    );
    applying.current = false;
    setActiveId(null);
    setCorrections((prev) =>
      prev.flatMap((row) => {
        if (row.id === item.id) return [];
        if (row.end <= found.start) return [row];
        if (row.start >= found.end) {
          return [{ ...row, start: row.start + delta, end: row.end + delta }];
        }
        return [];
      }),
    );
  }

  function dismiss(id: string) {
    const item = corrections.find((row) => row.id === id);
    if (item) {
      dismissed.current.add(dismissKey(item));
      if (item.category === "SPELLING" && item.original_text.trim()) {
        void skipSpellingWord(item.original_text.trim(), item.rule_id);
      }
    }
    setCorrections((prev) => prev.filter((row) => row.id !== id));
    if (activeId === id) setActiveId(null);
  }

  async function copyText() {
    if (!editor) return;
    await navigator.clipboard.writeText(plainTextFromDoc(editor.state.doc));
    closeMenu();
  }

  async function improveDocument() {
    if (!editor) return;
    const text = plainTextFromDoc(editor.state.doc);
    try {
      const result = await improveText(text, {
        document_type: DOC_TYPE,
        style: STYLE,
      });
      applying.current = true;
      editor.commands.setContent(textToHtml(result.text || ""));
      applying.current = false;
      shownRef.current = true;
      setShown(true);
      applyResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Сайжруулж чадсангүй");
    }
  }

  function loadSample() {
    editor?.commands.setContent(textToHtml(SAMPLE));
    closeMenu();
    editor?.commands.focus("end");
  }

  async function onPickFile(file: File | undefined) {
    if (!file || !editor) return;
    setError(null);
    closeMenu();
    try {
      const imported = await importDocument(file);
      editor.commands.setContent(textToHtml(imported.text || ""));
      editor.commands.focus("start");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Файл нээгдсэнгүй");
    }
  }

  function newDocument() {
    dismissed.current.clear();
    pending.current = null;
    lastText.current = "";
    lastLen.current = 0;
    shownRef.current = false;
    setShown(false);
    setChecking(false);
    editor?.commands.setContent("<p></p>");
    setCorrections([]);
    setDraft("");
    setCounts({ words: 0, chars: 0 });
    setError(null);
    closeMenu();
    editor?.commands.focus();
  }

  async function copyBichig() {
    if (!bichigText.trim()) return;
    await navigator.clipboard.writeText(bichigText);
  }

  return (
    <div className={showBichig ? "mw-shell is-bichig-open" : "mw-shell"}>
      <main className="mw-main">
        <header className="mw-top">
          <BrandLogo size="md" />
          <div className="mw-top-spacer" />
          <div className="mw-top-actions">
            <AuthButton />
            <div className="mw-menu" ref={menuRef}>
              <button
                type="button"
                className={menuOpen ? "mw-menu-trigger is-open" : "mw-menu-trigger"}
                aria-label="Цэс"
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                onClick={() => setMenuOpen((open) => !open)}
              >
                ⋯
              </button>
              {menuOpen ? (
                <div className="mw-menu-list" role="menu">
                  <button type="button" role="menuitem" onClick={newDocument}>
                    Шинэ
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      closeMenu();
                      fileRef.current?.click();
                    }}
                  >
                    Файл
                  </button>
                  <button type="button" role="menuitem" onClick={() => void copyText()}>
                    Хуулах
                  </button>
                  <button type="button" role="menuitem" onClick={loadSample}>
                    Жишээ
                  </button>
                </div>
              ) : null}
            </div>
            <span className="mw-top-rule" aria-hidden />
            <input
              ref={fileRef}
              type="file"
              accept=".docx,.txt,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                void onPickFile(file);
              }}
            />
            <button
              type="button"
              className={showBichig ? "mw-btn mw-btn-toggle is-on" : "mw-btn mw-btn-toggle"}
              onClick={() => setShowBichig((open) => !open)}
              aria-pressed={showBichig}
            >
              Монгол бичиг
            </button>
            <button
              type="button"
              className={checking ? "mw-btn-primary is-busy" : "mw-btn-primary"}
              onClick={() => void showErrors()}
              disabled={empty || checking}
              aria-busy={checking}
            >
              {checking ? (
                <>
                  <span className="mw-spinner" aria-hidden />
                  …
                </>
              ) : (
                "Шалгах"
              )}
            </button>
            <button
              type="button"
              className="mw-btn"
              onClick={() => void improveDocument()}
              disabled={aiEnabled ? !counts.words && !counts.chars : !fixableCount}
            >
              Засах
            </button>
          </div>
        </header>
        {error ? <p className="mw-banner">{error}</p> : null}
        <div className="mw-stage">
          <div className={empty ? "mw-editor is-empty" : "mw-editor"} aria-busy={checking}>
            <div className="mw-editor-scroll">
              <EditorContent editor={editor} />
            </div>
            <footer className="mw-editor-footer" aria-live="polite">
              <div className="mw-count">
                <span>Үгийн тоо</span>
                <strong>{counts.words.toLocaleString("mn-MN")}</strong>
              </div>
              <div className="mw-count">
                <span>Тэмдэгтийн тоо</span>
                <strong>
                  {counts.chars.toLocaleString("mn-MN")}/{maxChars.toLocaleString("mn-MN")}
                </strong>
              </div>
            </footer>
            {checking ? (
              <div className="mw-checking-overlay" role="status" aria-live="polite">
                <span className="mw-spinner lg" aria-hidden />
              </div>
            ) : null}
          </div>
          {showBichig ? (
            <aside className="mw-bichig-panel" aria-label="Монгол бичиг хөрвүүлэлт">
              <div className="mw-bichig-head">
                <div className="mw-bichig-title">Монгол бичиг</div>
                <button
                  type="button"
                  className="mw-btn"
                  onClick={() => void copyBichig()}
                  disabled={!bichigText.trim()}
                >
                  Хуулах
                </button>
              </div>
              {bichigText.trim() ? (
                <div className="mw-bichig-body" lang="mn-Mong">
                  {bichigText}
                </div>
              ) : (
                <div className="mw-bichig-empty" aria-hidden />
              )}
            </aside>
          ) : null}
        </div>
      </main>

      <aside className="mw-right">
        <div className="mw-right-head">
          <h2>
            {checking
              ? "Шалгаж байна…"
              : corrections.length
                ? statusLabel(corrections)
                : shown
                  ? "Алдаагүй"
                  : "Алдаатай үгс"}
          </h2>
        </div>
        <ul className="mw-list">
          {checking ? (
            <li className="mw-checking-panel">
              <span className="mw-spinner lg" aria-hidden />
            </li>
          ) : visible.length === 0 ? null : (
            visible.map((item) => (
              <li key={item.id} data-card-id={item.id}>
                <div
                  className={["mw-hit", activeId === item.id ? "on" : ""].filter(Boolean).join(" ")}
                >
                  <button
                    type="button"
                    className="mw-hit-main"
                    onClick={() => setActiveId((current) => (current === item.id ? null : item.id))}
                  >
                    <span className="mw-hit-word">{item.original_text}</span>
                    <span className="mw-hit-cat">Зөв бичиг</span>
                  </button>
                  <button
                    type="button"
                    className="mw-hit-x"
                    aria-label="Алгасах"
                    onClick={() => dismiss(item.id)}
                  >
                    ×
                  </button>
                </div>
              </li>
            ))
          )}
        </ul>
      </aside>
      {activeItem ? (
        <SuggestionPopover
          item={activeItem}
          onApply={apply}
          onDismiss={dismiss}
          onClose={() => setActiveId(null)}
        />
      ) : null}
    </div>
  );
}
