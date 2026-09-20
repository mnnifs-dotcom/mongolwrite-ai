"use client";

import { FormEvent, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { submitFeedback } from "@/lib/api";

const CATEGORIES = [
  { id: "spelling", label: "Зөв бичгийн алдаа (буруу тэмдэглэсэн үг)" },
  { id: "bichig", label: "Монгол бичиг хөрвүүлэлт" },
  { id: "site", label: "Сайтын алдаа, саатал" },
  { id: "other", label: "Бусад" },
] as const;

type CategoryId = (typeof CATEGORIES)[number]["id"];

export function ReportErrorForm() {
  const params = useSearchParams();
  const initialWord = useMemo(() => (params.get("word") || "").trim(), [params]);
  const initialCategory = useMemo((): CategoryId => {
    const raw = (params.get("type") || "").trim();
    if (CATEGORIES.some((row) => row.id === raw)) return raw as CategoryId;
    return "spelling";
  }, [params]);

  const [category, setCategory] = useState<CategoryId>(initialCategory);
  const [word, setWord] = useState(initialWord);
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = message.trim();
    if (trimmed.length < 8) {
      setError("Тайлбарыг арай дэлгэрэнгүй бичнэ үү.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await submitFeedback({
        category,
        word: word.trim(),
        message: trimmed,
        email: email.trim(),
        page: typeof window !== "undefined" ? window.location.pathname : "/aldaa-medegdeh",
      });
      setDone(true);
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Илгээж чадсангүй.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="mw-report-done" role="status">
        <strong>Баярлалаа.</strong>
        <p>Мэдэгдлээ хүлээж авлаа. Шаардлагатай бол хариу бичнэ.</p>
        <button type="button" className="mw-seo-cta mw-seo-cta-inline" onClick={() => setDone(false)}>
          Дахин илгээх
        </button>
      </div>
    );
  }

  return (
    <form className="mw-report-form" onSubmit={(event) => void onSubmit(event)}>
      <label className="mw-report-field">
        <span>Төрөл</span>
        <select value={category} onChange={(event) => setCategory(event.target.value as CategoryId)}>
          {CATEGORIES.map((row) => (
            <option key={row.id} value={row.id}>
              {row.label}
            </option>
          ))}
        </select>
      </label>

      <label className="mw-report-field">
        <span>Үг, хэсэг (заавал биш)</span>
        <input
          type="text"
          value={word}
          onChange={(event) => setWord(event.target.value)}
          placeholder="Жишээ: төгөлдөр"
          maxLength={200}
        />
      </label>

      <label className="mw-report-field">
        <span>Тайлбар</span>
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Юу буруу байсан, зөв нь юу байх ёстойг товч бичнэ үү."
          rows={5}
          maxLength={4000}
          required
        />
      </label>

      <label className="mw-report-field">
        <span>И-мэйл (заавал биш)</span>
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Хариу авах бол"
          maxLength={200}
        />
      </label>

      {error ? <p className="mw-report-error">{error}</p> : null}

      <button type="submit" className="mw-seo-cta mw-seo-cta-inline" disabled={busy}>
        {busy ? "Илгээж байна…" : "Илгээх"}
      </button>
    </form>
  );
}
