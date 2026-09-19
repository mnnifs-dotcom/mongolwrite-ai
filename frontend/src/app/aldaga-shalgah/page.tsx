import type { Metadata } from "next";
import Link from "next/link";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Алдаа шалгах | Монгол үгийн алдаа шалгагч — MongolWrite",
  },
  description:
    "Алдаа шалгах — монгол үг, бичгийн алдаагаа онлайнаар шалгаж засаарай. Суулгахгүй. Монгол бичиг хөрвүүлэх, Word татах.",
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
    description: "Монгол бичвэрийн алдаагаа онлайнаар шалгаж засаарай.",
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
          Одоо алдаа шалгах
        </Link>
      </header>

      <article className="mw-seo-article">
        <h1>Алдаа шалгах — монгол үгийн алдаа шалгагч</h1>
        <p className="mw-seo-lead">
          <strong>Алдаа шалгах</strong> гэж хайж байгаа бол эндээс эхлээрэй. MongolWrite
          дээр монгол кирилл текстээ буулгаад үгийн алдаа, бичгийн алдаагаа хэдхэн
          секундэд шалгана. Засаад, хүсвэл монгол бичиг рүү хөрвүүлж Word-оор татана.
        </p>

        <p>
          <Link href="/" className="mw-seo-cta mw-seo-cta-inline">
            Алдаагаа энд шалгах →
          </Link>
        </p>

        <h2>Алдаа шалгах гэж юу вэ?</h2>
        <p>
          Монгол бичвэрт үгийн зөв бичилт, зай, цэг таслал буруу байвал утга өөрчлөгдөнө.
          Онлайн <strong>алдаа шалгах</strong> хэрэгсэл текстээ автоматаар нягталж,
          алдаатай хэсгийг харуулна.
        </p>

        <h2>MongolWrite-аар алдаа шалгах давуу тал</h2>
        <ul>
          <li>
            <strong>Алдаа шалгах</strong> — монгол үгсийн алдааг тодруулна
          </li>
          <li>
            <strong>Засах</strong> — зөв хувилбараар солих боломжтой
          </li>
          <li>
            <strong>Монгол бичиг</strong> — кириллээс уламжлалт бичиг рүү хөрвүүлнэ
          </li>
          <li>
            <strong>Word татах</strong> — бэлэн файлаар авна
          </li>
        </ul>

        <h2>Хэрхэн алдаа шалгах вэ?</h2>
        <ol>
          <li>
            <Link href="/">mongolwrite.com</Link> руу орно
          </li>
          <li>Текстээ бичнэ эсвэл файл нээнэ</li>
          <li>
            <strong>Шалгах</strong> товч дарж алдаатай үгсийг харна
          </li>
          <li>Шаардлагатай бол засаж, монгол бичиг рүү хөрвүүлнэ</li>
        </ol>

        <h2>Түгээмэл хайлт</h2>
        <p>
          «алдаа шалгах», «үгийн алдаа шалгах», «бичгийн алдаа шалгах», «монгол зөв
          бичих» — эдгээр хэрэгцээг MongolWrite нэг дор шийднэ. Программ суулгахгүй,
          шууд вэб дээр ажиллана.
        </p>

        <p className="mw-seo-foot-cta">
          <Link href="/" className="mw-seo-cta">
            Одоо алдаа шалгах
          </Link>
        </p>
      </article>
    </main>
  );
}
