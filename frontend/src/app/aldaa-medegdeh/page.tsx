import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { ReportErrorForm } from "@/components/ReportErrorForm";
import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Алдаа мэдэгдэх | MongolWrite",
  },
  description:
    "Буруу тэмдэглэсэн үг, монгол бичиг хөрвүүлэлт, сайтын алдааг мэдэгдэх.",
  alternates: { canonical: "/aldaa-medegdeh" },
  openGraph: {
    title: "Алдаа мэдэгдэх | MongolWrite",
    description: "Буруу тэмдэглэсэн үг, хөрвүүлэлт, сайтын алдаагаа илгээнэ үү.",
    url: `${SITE}/aldaa-medegdeh`,
    type: "website",
    locale: "mn_MN",
  },
  robots: { index: true, follow: true },
};

export default function ReportErrorPage() {
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
        <h1>Алдаа мэдэгдэх</h1>
        <p className="mw-seo-lead">
          Буруу тэмдэглэсэн үг, монгол бичиг хөрвүүлэлтийн алдаа, сайтын саатлыг энд
          бичнэ үү. Бид шалгаад засна.
        </p>

        <Suspense fallback={<p className="mw-muted">Уншиж байна…</p>}>
          <ReportErrorForm />
        </Suspense>

        <p className="mw-report-note">
          <Link href="/uilchilgeenii-nokhtsol">Үйлчилгээний нөхцөл</Link>-тэй танилцана уу.
        </p>
      </article>

      <SiteFooter />
    </main>
  );
}
