"use client";

import { useEffect, useRef, useState } from "react";

import { syncBillingOrder, type BillingOrder } from "@/lib/api";

function formatPrice(mnt: number): string {
  return `₮${mnt.toLocaleString("mn-MN")}`;
}

type QpayUrl = {
  name?: string;
  description?: string;
  logo?: string;
  link?: string;
};

function asUrls(value: unknown): QpayUrl[] {
  if (!Array.isArray(value)) return [];
  return value.filter((row): row is QpayUrl => Boolean(row && typeof row === "object"));
}

type Props = {
  order: BillingOrder;
  checkoutReady: boolean;
  onPaid?: (order: BillingOrder) => void;
};

/** Poll gently — гэрээ 6.3.4: bill/check-ийг тасралтгүй дуудахгүй. */
const POLL_MS = 8_000;
const POLL_MAX_MS = 30 * 60 * 1000;

export function QpayCheckoutPanel({ order: initial, checkoutReady, onPaid }: Props) {
  const [order, setOrder] = useState(initial);
  const [syncing, setSyncing] = useState(false);
  const onPaidRef = useRef(onPaid);
  onPaidRef.current = onPaid;

  useEffect(() => {
    setOrder(initial);
  }, [initial]);

  useEffect(() => {
    if (order.status === "paid") return;
    if (!order.qpay_invoice_id) return;
    let cancelled = false;
    const started = Date.now();
    const tick = async () => {
      if (Date.now() - started > POLL_MAX_MS) return;
      try {
        const result = await syncBillingOrder(order.id);
        if (cancelled) return;
        setOrder(result.order);
        if (result.paid) onPaidRef.current?.(result.order);
      } catch {
        /* ignore transient poll errors */
      }
    };
    void tick();
    const id = window.setInterval(() => {
      if (Date.now() - started > POLL_MAX_MS) {
        window.clearInterval(id);
        return;
      }
      void tick();
    }, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [order.id, order.qpay_invoice_id, order.status]);

  const urls = asUrls(order.qpay_urls);
  const paid = order.status === "paid";
  const qrSrc = order.qpay_qr_image
    ? order.qpay_qr_image.startsWith("data:")
      ? order.qpay_qr_image
      : `data:image/png;base64,${order.qpay_qr_image}`
    : null;

  async function onManualSync() {
    setSyncing(true);
    try {
      const result = await syncBillingOrder(order.id);
      setOrder(result.order);
      if (result.paid) onPaidRef.current?.(result.order);
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="mw-qpay-panel" role="status">
      <div className="mw-qpay-panel-head">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/qpay-mark.svg" alt="QPay" width={72} height={22} className="mw-qpay-mark" />
        <strong>{paid ? "Төлбөр амжилттай" : "QPay-ээр төлнө үү"}</strong>
      </div>
      <p>
        {order.plan_name} · {formatPrice(order.amount_mnt)} · {order.sender_invoice_no}
      </p>
      <p className="mw-muted mw-qpay-fee-note">
        Дэлгэцэн дээрх үнээс нэмэлт шимтгэл авахгүй. Төлбөр QPay (QR / банкны апп) дамжина.
      </p>

      {paid ? (
        <p className="mw-muted">Эрх идэвхжүүлэгдлээ. Хуудсыг шинэчилж үргэлжлүүлнэ үү.</p>
      ) : checkoutReady && order.qpay_invoice_id ? (
        <>
          <p className="mw-muted">
            QR кодыг банкны аппаар уншуулна уу. Утаснаас бол доорх бүх төлбөрийн холбоосоос
            сонгоно уу.
          </p>
          {qrSrc ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={qrSrc} alt="QPay QR код" className="mw-qpay-qr" width={220} height={220} />
          ) : null}
          {order.qpay_short_url ? (
            <p>
              <a
                href={order.qpay_short_url}
                target="_blank"
                rel="noreferrer"
                className="mw-seo-cta mw-seo-cta-inline"
              >
                QPay холбоосоор нээх
              </a>
            </p>
          ) : null}
          {urls.length ? (
            <div className="mw-qpay-banks-wrap">
              <p className="mw-qpay-banks-label">Банк / төлбөрийн апп (бүтэн сонголт)</p>
              <ul className="mw-qpay-banks">
                {urls.map((row) => {
                  const href = row.link || "";
                  const label = row.name || row.description || "Банк";
                  if (!href) return null;
                  return (
                    <li key={`${label}-${href}`}>
                      <a href={href} target="_blank" rel="noreferrer">
                        {row.logo ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={row.logo} alt="" width={20} height={20} />
                        ) : null}
                        <span>{label}</span>
                      </a>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
          <button
            type="button"
            className="mw-btn"
            disabled={syncing}
            onClick={() => void onManualSync()}
          >
            {syncing ? "Шалгаж байна…" : "Төлбөр шалгах"}
          </button>
        </>
      ) : (
        <p className="mw-muted">
          {order.note ||
            (checkoutReady
              ? "QPay нэхэмжлэх үүсгэж байна…"
              : "QPay мерчантын код холбогдсны дараа төлбөр идэвхжинэ. Таны захиалга хадгалагдсан.")}
        </p>
      )}
    </div>
  );
}
