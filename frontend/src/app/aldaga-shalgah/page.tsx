import type { Metadata } from "next";
import Link from "next/link";

import { BrandWordmark } from "@/components/BrandWordmark";
import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";
const CANONICAL = "/aldaa-shalgah";

/** Legacy slug kept for old links; canonical points at /aldaa-shalgah. */
export const metadata: Metadata = {
  title: {
    absolute: "Алдаа шалгах | Монгол үгийн алдаа шалгагч — MongolWrite",
  },
  description:
    "Алдаа шалгах онлайн. Монгол кирилл бичвэрийн үгийн алдааг шууд шалгаж засаарай. MongolWrite.",
  keywords: ["алдаа шалгах", "үгийн алдаа шалгах", "MongolWrite"],
  alternates: { canonical: CANONICAL },
  robots: { index: false, follow: true },
  openGraph: {
    title: "Алдаа шалгах | MongolWrite",
    description: "Монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай.",
    url: `${SITE}${CANONICAL}`,
    type: "website",
    locale: "mn_MN",
    images: [{ url: "/logo-512.png", width: 512, height: 512, alt: "MongolWrite" }],
  },
};

export default function AldagaShalgahRedirectPage() {
  return (
    <main className="mw-seo-page">
      <header className="mw-seo-top">
        <Link href="/" className="mw-seo-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="" width={36} height={33} />
          <BrandWordmark />
        </Link>
        <Link href={CANONICAL} className="mw-seo-cta">
          Алдаа шалгах
        </Link>
      </header>

      <article className="mw-seo-article">
        <h1>Алдаа шалгах</h1>
        <p className="mw-seo-lead">
          Энэ хуудас шилжсэн. Монгол бичвэрийн алдаагаа шалгахын тулд шинэ хуудсыг нээнэ үү.
        </p>
        <p>
          <Link href={CANONICAL} className="mw-seo-cta mw-seo-cta-inline">
            Алдаа шалгах хуудас руу очих →
          </Link>
        </p>
        <p>
          Эсвэл шууд <Link href="/">mongolwrite.com</Link> дээр текстээ шалгана.
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
