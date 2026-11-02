"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  sttResult,
  sttStatus,
  sttTranscribe,
  type SttPublicStatus,
} from "@/lib/api";

function formatHours(seconds: number): string {
  if (seconds <= 0) return "0 мин";
  if (seconds < 3600) return `${Math.max(1, Math.round(seconds / 60))} мин`;
  const h = seconds / 3600;
  return `${h.toLocaleString("mn-MN", { maximumFractionDigits: 2 })} цаг`;
}

function estimateMnt(seconds: number, pricePerHour: number): number {
  return Math.round((Math.max(0, seconds) / 3600) * pricePerHour);
}

async function readClientDuration(file: File): Promise<number | null> {
  const url = URL.createObjectURL(file);
  try {
    const duration = await new Promise<number | null>((resolve) => {
      const audio = document.createElement("audio");
      audio.preload = "metadata";
      audio.onloadedmetadata = () => {
        const value = Number.isFinite(audio.duration) ? audio.duration : null;
        resolve(value && value > 0 ? value : null);
      };
      audio.onerror = () => resolve(null);
      audio.src = url;
    });
    return duration;
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function SpeechToTextForm() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<SttPublicStatus | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [clientSeconds, setClientSeconds] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<"idle" | "uploading" | "waiting" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [charged, setCharged] = useState<{ seconds: number; mnt: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const next = await sttStatus();
        if (!cancelled) setStatus(next);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Төлөв уншигдсангүй");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const estimate = useMemo(() => {
    if (!status || clientSeconds == null) return null;
    return estimateMnt(clientSeconds, status.price_mnt_per_hour);
  }, [status, clientSeconds]);

  async function onPick(next: File | null) {
    setFile(next);
    setText("");
    setCharged(null);
    setError(null);
    setPhase("idle");
    setClientSeconds(null);
    if (!next) return;
    const seconds = await readClientDuration(next);
    setClientSeconds(seconds);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    setText("");
    setPhase("uploading");
    try {
      const submitted = await sttTranscribe(file);
      setCharged({ seconds: submitted.duration_seconds, mnt: submitted.mnt });
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              remaining_seconds: submitted.remaining_seconds,
              remaining_hours: submitted.remaining_hours,
              needs_renewal: submitted.remaining_seconds <= 0,
              low_balance: submitted.remaining_seconds <= 30 * 60,
            }
          : prev,
      );
      setPhase("waiting");
      // Poll Chimege via our proxy; audio never stored on our server.
      let attempts = 0;
      while (attempts < 600) {
        attempts += 1;
        const row = await sttResult(submitted.uuid);
        if (row.done) {
          setText(row.transcription || "");
          setPhase("done");
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      throw new Error("Хөрвүүлэлт удаан байна. Дахин оролдоно уу.");
    } catch (err) {
      setPhase("idle");
      setError(err instanceof Error ? err.message : "Хөрвүүлэлт амжилтгүй");
    } finally {
      setBusy(false);
      // Drop local file handle from UI state after send — browser temp only.
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function copyText() {
    if (!text) return;
    await navigator.clipboard.writeText(text);
  }

  return (
    <div className="mw-stt">
      <div className="mw-stt-meta">
        <p>
          Үнэ:{" "}
          <strong>
            {(status?.price_mnt_per_hour ?? 7000).toLocaleString("mn-MN")}₮ / цаг
          </strong>
          {" · "}
          Файл серверт хадгалагдахгүй — Chimege рүү шууд хөрвүүлнэ.
        </p>
        {status ? (
          <p className={status.needs_renewal || status.low_balance ? "mw-stt-warn" : "mw-muted"}>
            {status.enabled
              ? status.needs_renewal
                ? "Үйлчилгээ түр зогссон — урьдчилсан эрх дууссан."
                : `Боломжтой эрх: ${formatHours(status.remaining_seconds)}`
              : "Үйлчилгээ түр унтарсан (API тохируулаагүй)."}
          </p>
        ) : (
          <p className="mw-muted">Төлөв шалгаж байна…</p>
        )}
      </div>

      <form className="mw-stt-form" onSubmit={(event) => void onSubmit(event)}>
        <label className="mw-stt-file">
          <span>Аудио / видео файл</span>
          <input
            ref={inputRef}
            type="file"
            accept="audio/*,video/mp4,video/webm,.wav,.mp3,.m4a,.mp4,.ogg,.flac,.webm"
            disabled={busy || !status?.enabled || !!status?.needs_renewal}
            onChange={(event) => {
              const next = event.target.files?.[0] ?? null;
              void onPick(next);
            }}
          />
        </label>
        {file ? (
          <p className="mw-muted">
            {file.name} · {(file.size / (1024 * 1024)).toLocaleString("mn-MN", {
              maximumFractionDigits: 2,
            })}{" "}
            MB
            {clientSeconds != null
              ? ` · ~${formatHours(clientSeconds)}${
                  estimate != null ? ` · ~${estimate.toLocaleString("mn-MN")}₮` : ""
                }`
              : ""}
          </p>
        ) : null}
        <button
          type="submit"
          className="mw-seo-cta mw-seo-cta-inline"
          disabled={busy || !file || !status?.enabled || !!status?.needs_renewal}
        >
          {phase === "uploading"
            ? "Илгээж байна…"
            : phase === "waiting"
              ? "Хөрвүүлж байна…"
              : "Бичвэр болгох"}
        </button>
      </form>

      {error ? <p className="mw-banner">{error}</p> : null}
      {charged ? (
        <p className="mw-muted">
          Хассан: {formatHours(charged.seconds)} · {charged.mnt.toLocaleString("mn-MN")}₮
        </p>
      ) : null}

      {phase === "done" || text ? (
        <div className="mw-stt-result">
          <div className="mw-stt-result-head">
            <h2>Бичвэр</h2>
            <button type="button" className="mw-btn" onClick={() => void copyText()} disabled={!text}>
              Хуулах
            </button>
          </div>
          <textarea
            className="mw-stt-textarea"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={12}
            placeholder="Хөрвүүлсэн бичвэр энд гарна."
          />
        </div>
      ) : null}
    </div>
  );
}
