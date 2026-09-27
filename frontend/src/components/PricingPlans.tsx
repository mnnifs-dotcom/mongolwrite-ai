"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  authMe,
  createBillingCheckout,
  fetchBillingPlans,
  type AuthUser,
  type BillingOrder,
  type BillingPlan,
  type BillingStatus,
} from "@/lib/api";
import { loginWithGooglePopup } from "@/lib/googleLogin";
import { formatDateMn } from "@/lib/formatDate";
import { PlanIconFree, PlanIconQuarter, PlanIconYear } from "@/components/PlanIcons";
import { QpayCheckoutPanel } from "@/components/QpayCheckoutPanel";

function formatPrice(mnt: number): string {
  return `₮${mnt.toLocaleString("mn-MN")}`;
}

export function PricingPlans() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [order, setOrder] = useState<BillingOrder | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshAuth = useCallback(async () => {
    const me = await authMe();
    setUser(me.user);
    setClientId(me.google_client_id);
    return me;
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const [billing, me] = await Promise.all([fetchBillingPlans(), refreshAuth()]);
        setStatus(billing);
        setUser(me.user);
        setClientId(me.google_client_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Уншиж чадсангүй");
      }
    })();
  }, [refreshAuth]);

  useEffect(() => {
    const onAuth = () => {
      void refreshAuth().catch(() => null);
    };
    window.addEventListener("mw-auth-changed", onAuth);
    return () => window.removeEventListener("mw-auth-changed", onAuth);
  }, [refreshAuth]);

  async function ensureAuthed(): Promise<AuthUser> {
    if (user) return user;
    if (!clientId) {
      throw new Error("Google нэвтрэлт бэлэн биш. Хуудсыг шинэчилээд дахин оролдоно уу.");
    }
    const next = await loginWithGooglePopup(clientId);
    setUser(next);
    return next;
  }

  async function onBuy(plan: BillingPlan) {
    if (plan.id !== "pro_3m" && plan.id !== "pro_year") return;
    setBusy(plan.id);
    setError(null);
    setOrder(null);
    try {
      await ensureAuthed();
      const result = await createBillingCheckout(plan.id);
      setOrder(result.order);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Захиалга амжилтгүй";
      if (message.includes("цуцлагдлаа")) {
        setError(null);
      } else {
        setError(message);
      }
    } finally {
      setBusy(null);
    }
  }

  const free = status?.all_plans?.find((row) => row.id === "free");
  const paid = status?.plans ?? [];
  const authed = Boolean(user);
  const expiryLabel =
    user?.is_paid && user.plan_expires_at ? formatDateMn(user.plan_expires_at) : "";

  return (
    <div className="mw-pricing">
      {user?.is_paid && expiryLabel ? (
        <p className="mw-pricing-active" role="status">
          Таны төлбөртэй эрх: <strong>{user.plan_name}</strong> ·{" "}
          <strong>{expiryLabel}</strong> хүртэл. Дахин төлбөр хийвэл энэ хугацаан дээр нэмэгдэнэ.
        </p>
      ) : null}

      {error ? <p className="mw-report-error">{error}</p> : null}

      {order ? (
        <QpayCheckoutPanel
          order={order}
          checkoutReady={Boolean(status?.checkout_ready)}
          onPaid={(next) => {
            setOrder(next);
            void refreshAuth()
              .then(() => window.dispatchEvent(new Event("mw-auth-changed")))
              .catch(() => null);
          }}
          onBack={() => setOrder(null)}
        />
      ) : (
        <div className="mw-pricing-grid">
          {free ? (
            <article className="mw-pricing-card">
              <div className="mw-pricing-icon" aria-hidden>
                <PlanIconFree />
              </div>
              <h2>{free.name}</h2>
              <p className="mw-pricing-price">{formatPrice(0)}</p>
              <p className="mw-muted">{free.blurb || "Туршиж үзэхэд тохиромжтой"}</p>
              <ul>
                {(free.features || []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {!authed ? (
                <button
                  type="button"
                  className="mw-seo-cta mw-seo-cta-inline"
                  disabled={busy === "free-login"}
                  onClick={() => {
                    void (async () => {
                      setBusy("free-login");
                      setError(null);
                      try {
                        await ensureAuthed();
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
                  {busy === "free-login" ? "Нэвтэрч байна…" : "Нэвтэрч турших"}
                </button>
              ) : (
                <Link className="mw-seo-cta mw-seo-cta-inline" href="/">
                  Засварлагч руу
                </Link>
              )}
            </article>
          ) : null}

          {paid.map((plan) => (
            <article
              key={plan.id}
              className={plan.id === "pro_year" ? "mw-pricing-card is-featured" : "mw-pricing-card"}
            >
              <div className="mw-pricing-icon" aria-hidden>
                {plan.id === "pro_year" ? <PlanIconYear /> : <PlanIconQuarter />}
              </div>
              <h2>{plan.name}</h2>
              <p className="mw-pricing-price">{formatPrice(plan.price_mnt)}</p>
              {plan.badge ? <p className="mw-pricing-badge">{plan.badge}</p> : null}
              <ul>
                {(plan.features || []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <button
                type="button"
                className="mw-seo-cta mw-seo-cta-inline"
                disabled={busy === plan.id}
                onClick={() => void onBuy(plan)}
              >
                {busy === plan.id
                  ? authed
                    ? "Захиалж байна…"
                    : "Нэвтэрч байна…"
                  : authed
                    ? user?.is_paid
                      ? "Сунгах"
                      : "Сонгох"
                    : "Нэвтэрээд сонгох"}
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
