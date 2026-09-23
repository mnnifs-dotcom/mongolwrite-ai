"use client";

import { useEffect, useState } from "react";

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

export function QpayCheckoutPanel({ order: initial, checkoutReady, onPaid }: Props) {
  const [order, setOrder] = useState(initial);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    setOrder(initial);
  }, [initial]);

  useEffect(() => {
    if (order.status === "paid") return;
    if (!order.qpay_invoice_id) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const result = await syncBillingOrder(order.id);
        if (cancelled) return;
        setOrder(result.order);
        if (result.paid) onPaid?.(result.order);
      } catch {
        /* ignore transient poll errors */
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 4000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [order.id, order.qpay_invoice_id, order.status, onPaid]);

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
      if (result.paid) onPaid?.(result.order);
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="mw-qpay-panel" role="status">
      <strong>
        {paid ? "Төлбөр амжилттай" : "Захиалга бүртгэгдлээ"}
      </strong>
      <p>
        {order.plan_name} · {formatPrice(order.amount_mnt)} · {order.sender_invoice_no}
      </p>

      {paid ? (
        <p className="mw-muted">Эрх идэвхжүүлэгдлээ. Хуудсыг шинэчилж үргэлжлүүлнэ үү.</p>
      ) : checkoutReady && order.qpay_invoice_id ? (
        <>
          <p className="mw-muted">
            Доорх QR кодыг банкны аппаар уншуулж, эсвэл банкны холбоосоор төлнө үү.
          </p>
          {qrSrc ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={qrSrc} alt="QPay QR" className="mw-qpay-qr" width={220} height={220} />
          ) : null}
          {order.qpay_short_url ? (
            <p>
              <a href={order.qpay_short_url} target="_blank" rel="noreferrer" className="mw-seo-cta mw-seo-cta-inline">
                QPay холбоосоор нээх
              </a>
            </p>
          ) : null}
          {urls.length ? (
            <ul className="mw-qpay-banks">
              {urls.map((row) => {
                const href = row.link || "";
                const label = row.name || row.description || "Банк";
                if (!href) return null;
                return (
                  <li key={`${label}-${href}`}>
                    <a href={href} target="_blank" rel="noreferrer">
                      {label}
                    </a>
                  </li>
                );
              })}
            </ul>
          ) : null}
          <button type="button" className="mw-btn" disabled={syncing} onClick={() => void onManualSync()}>
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
