"use client";

import { useEffect, useRef, useState } from "react";

import { fetchBillingOrder, syncBillingOrder, type BillingOrder } from "@/lib/api";

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
  onBack?: () => void;
};

/** Local order status only — never auto-hit QPay payment/check. */
const LOCAL_POLL_MS = 5_000;
const LOCAL_POLL_MAX_MS = 30 * 60 * 1000;

export function QpayCheckoutPanel({
  order: initial,
  checkoutReady,
  onPaid,
  onBack,
}: Props) {
  const [order, setOrder] = useState(initial);
  const [syncing, setSyncing] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const onPaidRef = useRef(onPaid);
  onPaidRef.current = onPaid;

  useEffect(() => {
    setOrder(initial);
  }, [initial]);

  useEffect(() => {
    panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [order.id, order.qpay_invoice_id]);

  useEffect(() => {
    if (order.status === "paid") return;
    if (!order.qpay_invoice_id) return;
    let cancelled = false;
    const started = Date.now();
    const tick = async () => {
      if (Date.now() - started > LOCAL_POLL_MAX_MS) return;
      try {
        const result = await fetchBillingOrder(order.id);
        if (cancelled) return;
        setOrder(result.order);
        if (result.order.status === "paid") onPaidRef.current?.(result.order);
      } catch {
        /* ignore */
      }
    };
    void tick();
    const id = window.setInterval(() => {
      if (Date.now() - started > LOCAL_POLL_MAX_MS) {
        window.clearInterval(id);
        return;
      }
      void tick();
    }, LOCAL_POLL_MS);
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
  const ready = checkoutReady && Boolean(order.qpay_invoice_id);

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
    <div className="mw-qpay-panel" role="status" ref={panelRef} tabIndex={-1}>
      <div className="mw-qpay-panel-head">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/qpay-mark.svg" alt="QPay" width={72} height={22} className="mw-qpay-mark" />
        <strong>
          {paid
            ? "Төлбөр амжилттай"
            : `${order.plan_name} · ${formatPrice(order.amount_mnt)}`}
        </strong>
        {onBack && !paid ? (
          <button type="button" className="mw-qpay-back" onClick={onBack}>
            Буцах
          </button>
        ) : null}
      </div>

      {paid ? (
        <p className="mw-muted">Эрх идэвхжлээ.</p>
      ) : ready ? (
        <>
          {qrSrc ? (
            <div className="mw-qpay-qr-wrap">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={qrSrc} alt="QPay QR" className="mw-qpay-qr" width={260} height={260} />
            </div>
          ) : null}

          <div className="mw-qpay-actions">
            {order.qpay_short_url ? (
              <a
                href={order.qpay_short_url}
                target="_blank"
                rel="noreferrer"
                className="mw-seo-cta mw-seo-cta-inline"
              >
                Аппаар нээх
              </a>
            ) : null}
            <button
              type="button"
              className="mw-btn"
              disabled={syncing}
              onClick={() => void onManualSync()}
            >
              {syncing ? "Шалгаж байна…" : "Төлбөр шалгах"}
            </button>
          </div>

          {urls.length ? (
            <ul className="mw-qpay-banks" aria-label="Банкны апп">
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
          ) : null}
        </>
      ) : (
        <p className="mw-muted">{order.note || "Нэхэмжлэх үүсгэж байна…"}</p>
      )}
    </div>
  );
}
