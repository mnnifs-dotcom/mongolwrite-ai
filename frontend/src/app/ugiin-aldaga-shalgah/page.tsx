import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Үгийн алдаа шалгах | MongolWrite",
  },
  description:
    "Монгол үгийн алдааг онлайнаар шалгаж засаарай. Монгол бичиг рүү хөрвүүлэх, Word файлаар татах.",
  keywords: [
    "алдаа шалгах",
    "үгийн алдаа шалгах",
    "үгийн алдаа шалгагч",
    "монгол үгийн алдаа шалгах",
    "бичгийн алдаа шалгах",
    "монгол хэлний алдаа шалгагч",
    "монгол зөв бичих",
    "MongolWrite",
  ],
  alternates: { canonical: "/ugiin-aldaga-shalgah" },
  openGraph: {
    title: "Үгийн алдаа шалгах | MongolWrite",
    description: "Монгол үгийн алдааг онлайнаар шалгаж засаарай.",
    url: `${SITE}/ugiin-aldaga-shalgah`,
    type: "website",
    locale: "mn_MN",
    images: [{ url: "/logo-512.png", width: 512, height: 512, alt: "MongolWrite" }],
  },
};

export default function UgiinAldagaShalgahPage() {
  return (
    <main className="mw-seo-page">
      <header className="mw-seo-top">
        <Link href="/" className="mw-seo-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="" width={36} height={33} />
          <span>MongolWrite</span>
        </Link>
        <Link href="/" className="mw-seo-cta">
          Шалгах
        </Link>
      </header>

      <article className="mw-seo-article">
        <h1>Үгийн алдаа шалгах</h1>
        <p className="mw-seo-lead">
          Кирилл текстээ оруулаад монгол үгийн алдааг шалгана. Алдаатай үгийг засаад,
          хүсвэл монгол бичиг рүү хөрвүүлж Word файлаар татна.
        </p>

        <p>
          <Link href="/" className="mw-seo-cta mw-seo-cta-inline">
            Үгийн алдаагаа шалгах →
          </Link>
        </p>

        <h2>Яагаад шалгах хэрэгтэй вэ?</h2>
        <p>
          Албан бичиг, даалгавар, пост бичихэд үгийн алдаа гарвал утга өөрчлөгдөж,
          уншихад төвөгтэй болно. Текстээ энд оруулаад хэдхэн секундэд шалгаж болно.
        </p>

        <h2>Юу хийж чадах вэ?</h2>
        <ul>
          <li>
            <strong>Үгийн алдаа шалгах</strong> — алдаатай үгийг тэмдэглэнэ
          </li>
          <li>
            <strong>Засах</strong> — зөв хэлбэрийг сонгоно
          </li>
          <li>
            <strong>Монгол бичиг хөрвүүлэх</strong> — кириллээс уламжлалт бичиг рүү
          </li>
          <li>
            <strong>Word татах</strong> — .docx файлаар авна
          </li>
        </ul>

        <h2>Хэрхэн ашиглах вэ?</h2>
        <ol>
          <li>Нүүр хуудас руу орно</li>
          <li>Текстээ бичнэ эсвэл Word, текст файл нээнэ</li>
          <li>
            <strong>Шалгах</strong> товч дарна
          </li>
          <li>
            Шаардлагатай бол <strong>Засах</strong> эсвэл монгол бичиг рүү хөрвүүлнэ
          </li>
        </ol>

        <h2>Бусад хайлт</h2>
        <p>
          «алдаа шалгах», «бичгийн алдаа шалгах», «монгол зөв бичих» гэсэн хайлтад
          ч тохирно. Суулгахгүйгээр шууд вэб дээр ажиллана.
        </p>

        <p className="mw-seo-foot-cta">
          <Link href="/" className="mw-seo-cta">
            Одоо шалгах
          </Link>
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
