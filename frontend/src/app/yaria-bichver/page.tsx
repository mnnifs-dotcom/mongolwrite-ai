import type { Metadata } from "next";
import Link from "next/link";

import { BrandWordmark } from "@/components/BrandWordmark";
import { SiteFooter } from "@/components/SiteFooter";
import { SpeechToTextForm } from "@/components/SpeechToTextForm";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Яриа бичвэр | MongolWrite",
  },
  description:
    "Монгол яриа, аудио файлыг бичвэр болгох. Chimege STT — файл серверт хадгалагдахгүй.",
  alternates: { canonical: "/yaria-bichver" },
  openGraph: {
    title: "Яриа бичвэр | MongolWrite",
    description: "Аудио/видео файлаа бичвэр болгоорой. 7000₮/цаг.",
    url: `${SITE}/yaria-bichver`,
    type: "website",
    locale: "mn_MN",
  },
  robots: { index: true, follow: true },
};

export default function SpeechToTextPage() {
  return (
    <main className="mw-seo-page">
      <header className="mw-seo-top">
        <Link href="/" className="mw-seo-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="" width={36} height={33} />
          <BrandWordmark />
        </Link>
        <Link href="/" className="mw-seo-cta">
          Алдаа шалгах
        </Link>
      </header>

      <article className="mw-seo-article">
        <h1>Яриа → бичвэр</h1>
        <p className="mw-seo-lead">
          Аудио эсвэл видео файлаа оруулаад монгол бичвэр авна. Файл манай серверт
          үлдэхгүй — зөвхөн хөрвүүлээд үр дүнг харуулна.
        </p>
        <SpeechToTextForm />
      </article>

      <SiteFooter />
    </main>
  );
}
