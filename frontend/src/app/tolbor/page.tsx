import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { PricingPlans } from "@/components/PricingPlans";
import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Төлбөр · багц | MongolWrite",
  },
  description:
    "MongolWrite төлбөрийн багц: үнэгүй, 3 сар ₮6,000, 1 жил ₮19,900. QPay-ээр төлөхөд бэлэн.",
  alternates: { canonical: "/tolbor" },
  openGraph: {
    title: "Төлбөр · багц | MongolWrite",
    description: "3 сар ₮6,000 · 1 жил ₮19,900",
    url: `${SITE}/tolbor`,
    type: "website",
    locale: "mn_MN",
  },
};

export default function PricingPage() {
  return (
    <main className="mw-seo-page">
      <header className="mw-seo-top">
        <Link href="/" className="mw-seo-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="" width={36} height={33} />
          <span>MongolWrite</span>
        </Link>
        <Link href="/" className="mw-seo-cta">
          Алдаа шалгах
        </Link>
      </header>

      <article className="mw-seo-article">
        <h1>Төлбөрийн багц</h1>
        <Suspense fallback={<p className="mw-muted">Уншиж байна…</p>}>
          <PricingPlans />
        </Suspense>
      </article>

      <SiteFooter />
    </main>
  );
}
