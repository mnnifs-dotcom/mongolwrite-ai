"use client";

import { useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";

import {
  authMe,
  createBillingCheckout,
  fetchBillingPlans,
  type BillingOrder,
  type BillingPlan,
} from "@/lib/api";
import { loginWithGooglePopup } from "@/lib/googleLogin";
import { PlanIconFree, PlanIconQuarter, PlanIconYear } from "@/components/PlanIcons";
import { QpayCheckoutPanel } from "@/components/QpayCheckoutPanel";

function formatPrice(mnt: number): string {
  return `₮${mnt.toLocaleString("mn-MN")}`;
}

type PricingUpgradeModalProps = {
  open: boolean;
  onClose: () => void;
  limit?: number;
};

export function PricingUpgradeModal({ open, onClose, limit }: PricingUpgradeModalProps) {
  const titleId = useId();
  const [authed, setAuthed] = useState(false);
  const [clientId, setClientId] = useState<string | null>(null);
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [order, setOrder] = useState<BillingOrder | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkoutReady, setCheckoutReady] = useState(false);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setOrder(null);
    void (async () => {
      try {
        const [billing, me] = await Promise.all([fetchBillingPlans(), authMe()]);
        setAuthed(Boolean(me.authenticated));
        setClientId(me.google_client_id);
        setCheckoutReady(Boolean(billing.checkout_ready));
        const free = (billing.all_plans || []).find((row) => row.id === "free");
        const paid = billing.plans || [];
        setPlans(free ? [free, ...paid] : [...paid]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Уншиж чадсангүй");
      }
    })();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  async function onBuy(plan: BillingPlan) {
    if (plan.id !== "pro_3m" && plan.id !== "pro_year") return;
    setBusy(plan.id);
    setError(null);
    setOrder(null);
    try {
      if (!authed) {
        if (!clientId) {
          throw new Error("Google нэвтрэлт бэлэн биш. Хуудсыг шинэчилээд дахин оролдоно уу.");
        }
        await loginWithGooglePopup(clientId);
        setAuthed(true);
      }
      const result = await createBillingCheckout(plan.id);
      setOrder(result.order);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Захиалга амжилтгүй";
      if (!message.includes("цуцлагдлаа")) setError(message);
    } finally {
      setBusy(null);
    }
  }

  if (!open || typeof document === "undefined") return null;

  const free = plans.find((row) => row.id === "free");
  const paid = plans.filter((row) => row.id === "pro_3m" || row.id === "pro_year");

  return createPortal(
    <div
      className="mw-upgrade-overlay"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="mw-upgrade-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <button type="button" className="mw-upgrade-close" onClick={onClose} aria-label="Хаах">
          ×
        </button>
        <header className="mw-upgrade-header">
          <p className="mw-upgrade-kicker" id={titleId}>
            {order ? "ТӨЛБӨР" : "БАГЦ СОНГОХ"}
          </p>
          {order ? null : (
            <p>
              {limit
                ? `Таны хязгаар ${limit.toLocaleString("mn-MN")} тэмдэгт.`
                : "Тохирох багцаа сонгоно уу."}
            </p>
          )}
        </header>

        {error ? <p className="mw-report-error">{error}</p> : null}

        {order ? (
          <QpayCheckoutPanel
            order={order}
            checkoutReady={checkoutReady}
            onPaid={(next) => setOrder(next)}
            onBack={() => setOrder(null)}
          />
        ) : (
        <div className="mw-upgrade-grid">
          {free ? (
            <article className="mw-upgrade-card">
              <div className="mw-upgrade-icon" aria-hidden>
                <PlanIconFree />
              </div>
              <h3>{free.name}</h3>
              <p className="mw-upgrade-blurb">{free.blurb || "Туршиж үзэхэд тохиромжтой"}</p>
              <p className="mw-upgrade-price">{formatPrice(0)}</p>
              <ul>
                {(free.features || []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {!authed ? (
                <button
                  type="button"
                  className="mw-upgrade-btn mw-upgrade-btn-ghost"
                  disabled={busy === "free-login"}
                  onClick={() => {
                    void (async () => {
                      setBusy("free-login");
                      setError(null);
                      try {
                        if (!clientId) {
                          throw new Error("Google нэвтрэлт бэлэн биш");
                        }
                        await loginWithGooglePopup(clientId);
                        setAuthed(true);
                      } catch (err) {
                        const message =
                          err instanceof Error ? err.message : "Нэвтэрч чадсангүй";
                        if (!message.includes("цуцлагдлаа")) setError(message);
                      } finally {
                        setBusy(null);
                      }
                    })();
                  }}
                >
                  {busy === "free-login" ? "Нэвтэрч байна…" : "Нэвтэрээд 14 хоног турших →"}
                </button>
              ) : (
                <button type="button" className="mw-upgrade-btn mw-upgrade-btn-ghost" onClick={onClose}>
                  Үргэлжлүүлэх →
                </button>
              )}
            </article>
          ) : null}

          {paid.map((plan) => {
            const featured = plan.id === "pro_year";
            return (
              <article
                key={plan.id}
                className={featured ? "mw-upgrade-card is-featured" : "mw-upgrade-card"}
              >
                {featured ? (
                  <span className="mw-upgrade-ribbon">Хамгийн ашигтай</span>
                ) : null}
                <div className="mw-upgrade-icon" aria-hidden>
                  {featured ? <PlanIconYear /> : <PlanIconQuarter />}
                </div>
                <h3>{plan.name}</h3>
                <p className="mw-upgrade-blurb">
                  {plan.blurb ||
                    (plan.id === "pro_3m"
                      ? "Богино хугацаанд хэрэглэхэд"
                      : "Урт хугацаанд тохиромжтой")}
                </p>
                <p className="mw-upgrade-price">{formatPrice(plan.price_mnt)}</p>
                {plan.badge ? <p className="mw-upgrade-pill">{plan.badge}</p> : null}
                <ul>
                  {(plan.features || []).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <button
                  type="button"
                  className="mw-upgrade-btn"
                  disabled={busy === plan.id}
                  onClick={() => void onBuy(plan)}
                >
                  {busy === plan.id
                    ? authed
                      ? "Захиалж байна…"
                      : "Нэвтэрч байна…"
                    : authed
                      ? "Сонгох →"
                      : "Нэвтэрээд сонгох →"}
                </button>
              </article>
            );
          })}
        </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
