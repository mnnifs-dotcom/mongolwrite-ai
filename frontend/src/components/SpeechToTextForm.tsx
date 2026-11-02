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

/** Keep words whole — strip soft hyphens and "-" line wraps from STT text. */
function normalizeTranscript(value: string): string {
  return value
    .replace(/[\u00ad\u200b\ufeff]/g, "")
    .replace(/([^\s-])-\s*[\r\n]+([^\s-])/g, "$1$2");
}

const MAX_STT_BYTES = 120 * 1024 * 1024;
const MAX_STT_MB = Math.round(MAX_STT_BYTES / (1024 * 1024));
const STT_PAY_KEY = "mw_stt_paid_order";

type PaidSession = {
  orderId: string;
  accessToken: string;
  amountMnt: number;
  billableSeconds: number;
};

function loadPaidSession(): PaidSession | null {
  try {
    const raw = sessionStorage.getItem(STT_PAY_KEY);
    if (!raw) return null;
    const row = JSON.parse(raw) as PaidSession;
    if (!row?.orderId || !row?.accessToken) return null;
    return row;
  } catch {
    return null;
  }
}

function savePaidSession(row: PaidSession | null) {
  try {
    if (!row) sessionStorage.removeItem(STT_PAY_KEY);
    else sessionStorage.setItem(STT_PAY_KEY, JSON.stringify(row));
  } catch {
    /* ignore */
  }
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

type Phase = "idle" | "checkout" | "paying" | "uploading" | "waiting" | "done";

export function SpeechToTextForm() {
  const inputRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<File | null>(null);
  const accessTokenRef = useRef("");
  const busyRef = useRef(false);
  const convertAfterPayRef = useRef(false);
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

  useEffect(() => {
    busyRef.current = busy;
  }, [busy]);

  useEffect(() => {
    accessTokenRef.current = accessToken;
  }, [accessToken]);

  useEffect(() => {
    fileRef.current = file;
  }, [file]);

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
    setPhase("idle");
    setProgress(0);
    setProgressLabel("");
    setClientSeconds(null);
    // Keep a paid-but-undelivered session so retry does not charge again.
    const paid = loadPaidSession();
    if (!paid) {
      setPayOrder(null);
      setAccessToken("");
      setCharged(null);
      convertAfterPayRef.current = false;
    }
    if (!next) {
      setFile(null);
      setError(null);
      return;
    }
    // Fail fast before metadata/upload — large files used to hang then show size error.
    if (next.size > MAX_STT_BYTES) {
      setFile(null);
      setError(
        `Файл хэт том (дээд хэмжээ ${MAX_STT_MB}MB). Одоо ${(next.size / (1024 * 1024)).toLocaleString("mn-MN", {
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
    setProgress(4);
    setProgressLabel("Файл илгээж байна…");
    savePaidSession({
      orderId: paidOrder.id,
      accessToken: token,
      amountMnt: paidOrder.amount_mnt,
      billableSeconds: Number(paidOrder.duration_seconds || clientSeconds || 60),
    });
    const payment = { orderId: paidOrder.id, accessToken: token };
    const started = Date.now();
    // Long audio (e.g. 40+ мин) needs generous poll budget; Chimege often finishes faster.
    const expectedMs = Math.max(45_000, (clientSeconds ?? 60) * 350);
    let progressTimer: number | null = null;
    try {
      const submitted = await sttTranscribe(audio, payment, {
        onUploadProgress: (pct) => {
          // Map raw upload 0–100 → UI 5–42 while bytes leave the browser.
          const mapped = Math.max(5, Math.min(42, Math.round(5 + pct * 0.37)));
          setProgress((prev) => Math.max(prev, mapped));
          setProgressLabel("Файл илгээж байна…");
        },
      });
      setCharged({ seconds: submitted.duration_seconds, mnt: submitted.mnt });
      setPhase("waiting");
      setProgress((prev) => Math.max(prev, submitted.pending ? 45 : 55));
      setProgressLabel(
        submitted.pending ? "Сервер Chimege-д илгээж байна…" : "Бичвэр болгож байна…",
      );

      let pollUuid = submitted.uuid;
      progressTimer = window.setInterval(() => {
        setProgress((prev) => {
          if (prev >= 92) return prev;
          const elapsed = Date.now() - started;
          const timed = Math.min(90, Math.round(45 + (elapsed / expectedMs) * 45));
          return Math.max(prev, timed);
        });
      }, 500);

      let attempts = 0;
      while (attempts < 900) {
        attempts += 1;
        const row = await sttResult(pollUuid, payment);
        if (row.uuid && row.uuid !== pollUuid) pollUuid = row.uuid;
        const serverPct = row.progress_percent ?? 0;
        const elapsed = Date.now() - started;
        const timed = Math.min(95, Math.round(45 + (elapsed / expectedMs) * 50));
        const phaseLabel =
          row.phase === "queued" || row.phase === "uploading"
            ? "Сервер Chimege-д илгээж байна…"
            : "Бичвэр болгож байна…";
        setProgressLabel(phaseLabel);
        setProgress(row.done ? 100 : Math.max(45, serverPct, timed));
        if (row.done) {
          setText(normalizeTranscript(row.transcription || ""));
          setPhase("done");
          setProgress(100);
          setProgressLabel("Дууслаа");
          savePaidSession(null);
          setPayOrder(null);
          setAccessToken("");
          convertAfterPayRef.current = false;
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
      // Keep paid session — next click retries convert without new QPay.
      setAccessToken(token);
      setPayOrder(paidOrder);
      convertAfterPayRef.current = true;
    } finally {
      if (progressTimer != null) window.clearInterval(progressTimer);
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || busy) return;
    if (clientSeconds == null || clientSeconds <= 0) {
      setError("Файлын үргэлжлэх хугацаа уншигдсангүй. Өөр файл сонгоно уу.");
      return;
    }

    // Already paid this session — convert again, do not open QPay.
    const existing = loadPaidSession();
    if (existing) {
      setBusy(true);
      setError(null);
      try {
        const statusRow = await fetchSttOrder(existing.orderId, existing.accessToken);
        if (statusRow.order.status === "paid" && !statusRow.order.consumed) {
          setAccessToken(existing.accessToken);
          setPayOrder(statusRow.order);
          setCharged({
            seconds: existing.billableSeconds,
            mnt: existing.amountMnt,
          });
          await runConversion(statusRow.order, existing.accessToken, file);
          return;
        }
        if (statusRow.order.consumed) {
          // Delivered earlier — try to pull cached transcript without recharging.
          try {
            const uuid = String(statusRow.order.chimege_uuid || "");
            if (uuid) {
              const row = await sttResult(uuid, {
                orderId: existing.orderId,
                accessToken: existing.accessToken,
              });
              if (row.done && row.transcription) {
                setText(normalizeTranscript(row.transcription));
                setPhase("done");
                setProgress(100);
                setProgressLabel("Дууслаа");
                savePaidSession(null);
                setPayOrder(null);
                setAccessToken("");
                return;
              }
            }
          } catch {
            /* fall through */
          }
          savePaidSession(null);
        }
      } catch {
        /* fall through to new checkout */
      } finally {
        setBusy(false);
      }
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
      setError(err instanceof Error ? err.message : "Төлбөр үүсгэж чадсангүй");
    } finally {
      setBusy(false);
    }
  }

  async function onPaid(order: BillingOrder) {
    const audio = fileRef.current;
    const token = accessTokenRef.current;
    if (!audio || !token || !convertAfterPayRef.current) return;
    if (busyRef.current) return;
    setPayOrder(order);
    savePaidSession({
      orderId: order.id,
      accessToken: token,
      amountMnt: order.amount_mnt,
      billableSeconds: Number(order.duration_seconds || clientSeconds || 60),
    });
    await runConversion(order, token, audio);
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
          Формат: wav, mp3, m4a, mp4, aac, ogg, flac, webm · дээд хэмжээ {MAX_STT_MB}MB
        </p>
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
