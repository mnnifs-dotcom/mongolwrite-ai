import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Алдаа шалгах | Монгол үгийн алдаа шалгагч — MongolWrite",
  },
  description:
    "Монгол бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай. Программ суулгахгүй. Монгол бичиг рүү хөрвүүлэх, Word татах.",
  keywords: [
    "алдаа шалгах",
    "үгийн алдаа шалгах",
    "бичгийн алдаа шалгах",
    "монгол алдаа шалгах",
    "алдаа шалгагч",
    "монгол зөв бичих",
    "MongolWrite",
  ],
  alternates: { canonical: "/aldaga-shalgah" },
  openGraph: {
    title: "Алдаа шалгах | MongolWrite",
    description: "Монгол бичвэрийн алдааг онлайнаар шалгаж засаарай.",
    url: `${SITE}/aldaga-shalgah`,
    type: "website",
    locale: "mn_MN",
    images: [{ url: "/logo-512.png", width: 512, height: 512, alt: "MongolWrite" }],
  },
};

export default function AldagaShalgahPage() {
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
        <h1>Алдаа шалгах</h1>
        <p className="mw-seo-lead">
          MongolWrite дээр монгол кирилл текстээ бичээд үгийн алдааг шууд шалгана.
          Алдаатай үгийг засаад, хүсвэл монгол бичиг рүү хөрвүүлж Word файлаар авна.
        </p>

        <p>
          <Link href="/" className="mw-seo-cta mw-seo-cta-inline">
            Эндээс шалгах →
          </Link>
        </p>

        <h2>Алдаа шалгах гэж юу вэ?</h2>
        <p>
          Бичвэрт үг буруу бичигдсэн, зай, цэг таслал алдаатай байвал утга өөрчлөгдөнө.
          Онлайн алдаа шалгагч текстээ үзэж, алдаатай хэсгийг тэмдэглэнэ.
        </p>

        <h2>MongolWrite юу хийдэг вэ?</h2>
        <ul>
          <li>
            <strong>Алдаа шалгах</strong> — үгийн алдааг олж харуулна
          </li>
          <li>
            <strong>Засах</strong> — зөв хэлбэрээр солино
          </li>
          <li>
            <strong>Монгол бичиг</strong> — кириллээс уламжлалт бичиг рүү хөрвүүлнэ
          </li>
          <li>
            <strong>Word татах</strong> — .docx файлаар авна
          </li>
        </ul>

        <h2>Хэрхэн шалгах вэ?</h2>
        <ol>
          <li>
            <Link href="/">mongolwrite.com</Link> руу орно
          </li>
          <li>Текстээ бичнэ эсвэл файл нээнэ</li>
          <li>
            <strong>Шалгах</strong> товч дарна
          </li>
          <li>Алдаатай үгийг засаж, шаардлагатай бол монгол бичиг рүү хөрвүүлнэ</li>
        </ol>

        <h2>Бусад хайлт</h2>
        <p>
          «үгийн алдаа шалгах», «бичгийн алдаа шалгах», «монгол зөв бичих» гэж хайж
          байгаа бол мөн эндээс эхэлж болно. Программ суулгахгүйгээр вэб дээр ажиллана.
        </p>

        <p className="mw-seo-foot-cta">
          <Link href="/" className="mw-seo-cta">
            Алдаа шалгах
          </Link>
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
