"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { QpayCheckoutPanel } from "@/components/QpayCheckoutPanel";
import {
  fetchSttOrder,
  sttCheckout,
  sttResult,
  sttStatus,
  sttTranscribe,
  syncSttOrder,
  type BillingOrder,
  type SttPublicStatus,
} from "@/lib/api";

function formatHours(seconds: number): string {
  if (seconds <= 0) return "0 мин";
  if (seconds < 3600) return `${Math.max(1, Math.round(seconds / 60))} мин`;
  const h = seconds / 3600;
  return `${h.toLocaleString("mn-MN", { maximumFractionDigits: 2 })} цаг`;
}

function estimateMnt(seconds: number, pricePerHour: number): number {
  const minutes = Math.max(1, Math.ceil(Math.max(0, seconds) / 60));
  return Math.max(1, Math.round((minutes / 60) * pricePerHour));
}

const MAX_STT_BYTES = 40 * 1024 * 1024;

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

type Phase = "idle" | "checkout" | "paying" | "uploading" | "waiting" | "done";

export function SpeechToTextForm() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<SttPublicStatus | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [clientSeconds, setClientSeconds] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [charged, setCharged] = useState<{ seconds: number; mnt: number } | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState("");
  const [payOrder, setPayOrder] = useState<BillingOrder | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [checkoutReady, setCheckoutReady] = useState(false);
  const convertAfterPayRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const next = await sttStatus();
        if (!cancelled) {
          setStatus(next);
          setCheckoutReady(Boolean(next.checkout_ready));
        }
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
    setText("");
    setCharged(null);
    setPhase("idle");
    setProgress(0);
    setProgressLabel("");
    setPayOrder(null);
    setAccessToken("");
    setClientSeconds(null);
    convertAfterPayRef.current = false;
    if (!next) {
      setFile(null);
      setError(null);
      return;
    }
    // Fail fast before metadata/upload — large files used to hang then show size error.
    if (next.size > MAX_STT_BYTES) {
      setFile(null);
      setError(
        `Файл хэт том (дээд хэмжээ 40MB). Одоо ${(next.size / (1024 * 1024)).toLocaleString("mn-MN", {
          maximumFractionDigits: 1,
        })}MB байна.`,
      );
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setFile(next);
    setError(null);
    const seconds = await readClientDuration(next);
    setClientSeconds(seconds);
  }

  async function runConversion(paidOrder: BillingOrder, token: string, audio: File) {
    setBusy(true);
    setError(null);
    setText("");
    setPhase("uploading");
    setProgress(8);
    setProgressLabel("Файл илгээж байна…");
    const started = Date.now();
    const expectedMs = Math.max(15_000, (clientSeconds ?? 60) * 800);
    let progressTimer: number | null = null;
    try {
      progressTimer = window.setInterval(() => {
        setProgress((prev) => {
          if (prev >= 92) return prev;
          const elapsed = Date.now() - started;
          const timed = Math.min(90, Math.round((elapsed / expectedMs) * 90));
          return Math.max(prev, Math.max(12, timed));
        });
      }, 400);

      const submitted = await sttTranscribe(audio, {
        orderId: paidOrder.id,
        accessToken: token,
      });
      setCharged({ seconds: submitted.duration_seconds, mnt: submitted.mnt });
      setPhase("waiting");
      setProgress((prev) => Math.max(prev, 35));
      setProgressLabel("Бичвэр болгож байна…");

      let attempts = 0;
      while (attempts < 600) {
        attempts += 1;
        const row = await sttResult(submitted.uuid);
        const serverPct = row.progress_percent ?? 0;
        const elapsed = Date.now() - started;
        const timed = Math.min(95, Math.round((elapsed / expectedMs) * 95));
        setProgress(row.done ? 100 : Math.max(35, serverPct, timed));
        if (row.done) {
          setText(row.transcription || "");
          setPhase("done");
          setProgress(100);
          setProgressLabel("Дууслаа");
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      throw new Error("Хөрвүүлэлт удаан байна. Дахин оролдоно уу.");
    } catch (err) {
      setPhase("idle");
      setProgress(0);
      setProgressLabel("");
      setError(err instanceof Error ? err.message : "Хөрвүүлэлт амжилтгүй");
    } finally {
      if (progressTimer != null) window.clearInterval(progressTimer);
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
      setPayOrder(null);
      setAccessToken("");
      convertAfterPayRef.current = false;
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || busy) return;
    if (clientSeconds == null || clientSeconds <= 0) {
      setError("Файлын үргэлжлэх хугацаа уншигдсангүй. Өөр файл сонгоно уу.");
      return;
    }
    setBusy(true);
    setError(null);
    setText("");
    setPhase("checkout");
    setProgress(0);
    setProgressLabel("Төлбөрийн дүн тооцоолж байна…");
    try {
      const quoted = await sttCheckout({
        duration_seconds: clientSeconds,
        filename: file.name,
      });
      const token = quoted.order.access_token || "";
      if (!token) throw new Error("Төлбөрийн эрх үүссэнгүй.");
      setAccessToken(token);
      setPayOrder(quoted.order);
      setCheckoutReady(quoted.checkout_ready);
      setCharged({
        seconds: quoted.billable_seconds,
        mnt: quoted.amount_mnt,
      });
      if (quoted.order.status === "paid") {
        convertAfterPayRef.current = true;
        await runConversion(quoted.order, token, file);
        return;
      }
      if (!quoted.checkout_ready || !quoted.order.qpay_invoice_id) {
        throw new Error(
          quoted.order.note || "QPay төлбөр одоогоор бэлэн биш байна. Дахин оролдоно уу.",
        );
      }
      setPhase("paying");
      setProgressLabel("QPay-ээр төлнө үү");
      convertAfterPayRef.current = true;
    } catch (err) {
      setPhase("idle");
      setPayOrder(null);
      setAccessToken("");
      setError(err instanceof Error ? err.message : "Төлбөр үүсгэж чадсангүй");
    } finally {
      setBusy(false);
    }
  }

  async function onPaid(order: BillingOrder) {
    if (!file || !accessToken || !convertAfterPayRef.current) return;
    if (busy) return;
    setPayOrder(order);
    await runConversion(order, accessToken, file);
  }

  async function copyText() {
    if (!text) return;
    await navigator.clipboard.writeText(text);
  }

  const serviceBlocked =
    status != null && (!status.enabled || status.needs_renewal);
  const showProgress = phase === "uploading" || phase === "waiting" || (phase === "done" && progress === 100);

  return (
    <div className="mw-stt">
      <div className="mw-stt-meta">
        <p>
          Үнэ:{" "}
          <strong>
            {(status?.price_mnt_per_hour ?? 7000).toLocaleString("mn-MN")}₮ / цаг
          </strong>
        </p>
        <p className="mw-muted">
          Формат: wav, mp3, m4a, mp4, aac, ogg, flac, webm · дээд хэмжээ 40MB
        </p>
        <p className="mw-muted">Эхлээд QPay-ээр төлөөд дараа нь бичвэр бэлтгэнэ.</p>
        {serviceBlocked ? (
          <p className="mw-stt-warn">
            {!status?.enabled
              ? "Үйлчилгээ түр унтарсан."
              : "Үйлчилгээ түр ашиглах боломжгүй."}
          </p>
        ) : null}
      </div>

      <form className="mw-stt-form" onSubmit={(event) => void onSubmit(event)}>
        <input
          ref={inputRef}
          type="file"
          accept="audio/*,video/mp4,video/webm,.wav,.mp3,.m4a,.mp4,.aac,.ogg,.flac,.webm,.wma"
          hidden
          disabled={busy || serviceBlocked || phase === "paying"}
          onChange={(event) => {
            const next = event.target.files?.[0] ?? null;
            void onPick(next);
          }}
        />
        <div className="mw-stt-actions">
          <button
            type="button"
            className="mw-seo-cta mw-seo-cta-inline mw-stt-pick"
            disabled={busy || serviceBlocked || phase === "paying"}
            onClick={() => inputRef.current?.click()}
          >
            {file ? "Файл солих" : "Файл оруулах"}
          </button>
          <button
            type="submit"
            className="mw-seo-cta mw-seo-cta-inline"
            disabled={
              busy ||
              !file ||
              serviceBlocked ||
              phase === "paying" ||
              phase === "uploading" ||
              phase === "waiting"
            }
          >
            {phase === "checkout"
              ? "Төлбөр бэлдэж байна…"
              : phase === "paying"
                ? "Төлбөр хүлээж байна…"
                : phase === "uploading"
                  ? `Илгээж байна… ${progress}%`
                  : phase === "waiting"
                    ? `Хөрвүүлж байна… ${progress}%`
                    : "Бичвэр болгох"}
          </button>
        </div>
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
      </form>

      {payOrder && phase === "paying" && accessToken ? (
        <QpayCheckoutPanel
          order={payOrder}
          checkoutReady={checkoutReady}
          paidNote="Төлбөр амжилттай. Бичвэр бэлтгэж байна…"
          onBack={() => {
            setPhase("idle");
            setPayOrder(null);
            setAccessToken("");
            convertAfterPayRef.current = false;
          }}
          fetchOrder={(id) => fetchSttOrder(id, accessToken)}
          syncOrder={(id) => syncSttOrder(id, accessToken)}
          onPaid={(order) => void onPaid(order)}
        />
      ) : null}

      {showProgress ? (
        <div className="mw-stt-progress" aria-live="polite">
          <div className="mw-stt-progress-head">
            <span>{progressLabel || "Явц"}</span>
            <strong>{progress}%</strong>
          </div>
          <div className="mw-stt-progress-track">
            <div className="mw-stt-progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : null}

      {error ? <p className="mw-banner">{error}</p> : null}
      {charged && phase !== "paying" ? (
        <p className="mw-muted">
          Төлбөр: {formatHours(charged.seconds)} · {charged.mnt.toLocaleString("mn-MN")}₮
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
