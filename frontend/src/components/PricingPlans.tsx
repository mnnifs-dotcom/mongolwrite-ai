"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  authMe,
  createBillingCheckout,
  fetchBillingPlans,
  type BillingOrder,
  type BillingPlan,
  type BillingStatus,
} from "@/lib/api";
import { PlanIconFree, PlanIconQuarter, PlanIconYear } from "@/components/PlanIcons";

function formatPrice(mnt: number): string {
  return `₮${mnt.toLocaleString("mn-MN")}`;
}

export function PricingPlans() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [authed, setAuthed] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [order, setOrder] = useState<BillingOrder | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [billing, me] = await Promise.all([fetchBillingPlans(), authMe()]);
        setStatus(billing);
        setAuthed(Boolean(me.authenticated));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Уншиж чадсангүй");
      }
    })();
  }, []);

  async function onBuy(plan: BillingPlan) {
    if (plan.id !== "pro_3m" && plan.id !== "pro_year") return;
    setBusy(plan.id);
    setError(null);
    setOrder(null);
    try {
      const result = await createBillingCheckout(plan.id);
      setOrder(result.order);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Захиалга амжилтгүй");
    } finally {
      setBusy(null);
    }
  }

  const free = status?.all_plans?.find((row) => row.id === "free");
  const paid = status?.plans ?? [];

  return (
    <div className="mw-pricing">
      <p className="mw-seo-lead">
        Үнэгүй: нэг удаа шалгахдаа 1500 хүртэл тэмдэгт. Төлбөртэй эрх: 3 сар ₮6,000 эсвэл 1 жил
        ₮19,900 · нэг удаа шалгахдаа 500000 хүртэл тэмдэгт.
      </p>

      {error ? <p className="mw-report-error">{error}</p> : null}

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
              <Link className="mw-seo-cta mw-seo-cta-inline" href="/">
                Нэвтэрч турших
              </Link>
            ) : null}
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
              {busy === plan.id ? "Захиалж байна…" : authed ? "Сонгох" : "Нэвтэрээд сонгох"}
            </button>
          </article>
        ))}
      </div>

      {order ? (
        <div className="mw-pricing-order" role="status">
          <strong>Захиалга бүртгэгдлээ</strong>
          <p>
            {order.plan_name} · {formatPrice(order.amount_mnt)} · {order.sender_invoice_no}
          </p>
          <p className="mw-muted">
            {status?.checkout_ready
              ? "QPay төлбөрийн цонх удахгүй нээгдэнэ."
              : "QPay код холбогдсны дараа төлбөр идэвхжинэ. Таны захиалга хадгалагдсан."}
          </p>
        </div>
      ) : null}
    </div>
  );
}
