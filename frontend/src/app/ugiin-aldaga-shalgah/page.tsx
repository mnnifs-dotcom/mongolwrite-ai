import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Үгийн алдаа шалгах | Алдаа шалгах — MongolWrite",
  },
  description:
    "Үгийн алдаа шалгах, алдаа шалгах онлайн. Монгол текстээ шалгаад засварлаж, монгол бичиг рүү хөрвүүлээд Word татана.",
  keywords: [
    "алдаа шалгах",
    "үгийн алдаа шалгах",
    "үгийн алдаа шалгагч",
    "монгол үгийн алдаа шалгах",
    "бичгийн алдаа шалгах",
    "монгол хэлний алдаа шалгагч",
    "монгол зөв бичих",
    "spellcheck mongolian",
    "MongolWrite",
  ],
  alternates: { canonical: "/ugiin-aldaga-shalgah" },
  openGraph: {
    title: "Үгийн алдаа шалгах | Алдаа шалгах — MongolWrite",
    description:
      "Монгол үгийн алдаагаа онлайнаар шалгаж засаарай. Монгол бичиг хөрвүүлэх, Word татах.",
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
          Одоо шалгах
        </Link>
      </header>

      <article className="mw-seo-article">
        <h1>Үгийн алдаа шалгах — алдаа шалгах онлайн</h1>
        <p className="mw-seo-lead">
          MongolWrite нь монгол хэлний <strong>алдаа шалгах</strong>,{" "}
          <strong>үгийн алдаа шалгагч</strong> юм. Кирилл текстээ буулгаад алдаатай
          үгсийг олж засаарай. Мөн монгол бичиг рүү хөрвүүлж, Word файлаар татаж авна.
        </p>

        <p>
          <Link href="/" className="mw-seo-cta mw-seo-cta-inline">
            Үгийн алдаагаа энд шалгах →
          </Link>
        </p>

        <h2>Яагаад үгийн алдаа шалгах хэрэгтэй вэ?</h2>
        <p>
          Албан бичиг, сургуулийн даалгавар, нийгмийн сүлжээний пост — монгол бичвэрт
          үгийн алдаа гарвал утга өөрчлөгдөж, сэтгэгдэл муудана. Онлайн{" "}
          <strong>үгийн алдаа шалгах</strong> хэрэгслээр текстээ хэдхэн секундэд
          нягтална.
        </p>

        <h2>MongolWrite юу хийдэг вэ?</h2>
        <ul>
          <li>
            <strong>Үгийн алдаа шалгах</strong> — монгол кирилл бичвэрийн алдаатай үгсийг
            тодруулна
          </li>
          <li>
            <strong>Засах</strong> — санал болгосон зөв хэлбэрээр солих боломжтой
          </li>
          <li>
            <strong>Монгол бичиг хөрвүүлэх</strong> — кириллээс уламжлалт монгол бичиг рүү
          </li>
          <li>
            <strong>Word татах</strong> — хөрвүүлсэн бичвэрийг .docx-оор татана
          </li>
        </ul>

        <h2>Хэрхэн ашиглах вэ?</h2>
        <ol>
          <li>Нүүр хуудас руу орно</li>
          <li>Текстээ бичнэ эсвэл Word/текст файлаа нээнэ</li>
          <li>
            <strong>Шалгах</strong> товч дарж үгийн алдааг харна
          </li>
          <li>Шаардлагатай бол <strong>Засах</strong> эсвэл монгол бичиг рүү хөрвүүлнэ</li>
        </ol>

        <h2>Түгээмэл хайлтууд</h2>
        <p>
          Хүмүүс ихэвчлэн «үгийн алдаа шалгах», «монгол үгийн алдаа шалгагч», «бичгийн
          алдаа шалгах», «монгол зөв бичих» гэж хайдаг. MongolWrite эдгээр хэрэгцээг нэг
          газарт шийднэ — суулгахгүйгээр, шууд вэб дээр.
        </p>

        <p className="mw-seo-foot-cta">
          <Link href="/" className="mw-seo-cta">
            Үгийн алдаагаа одоо шалгах
          </Link>
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
