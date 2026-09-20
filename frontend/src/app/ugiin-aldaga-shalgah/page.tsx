import type { Metadata } from "next";
import Link from "next/link";

import { BrandWordmark } from "@/components/BrandWordmark";
import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Үгийн алдаа шалгах | MongolWrite",
  },
  description:
    "Монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай. Монгол бичиг рүү хөрвүүлэх, Word файлаар татах.",
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
    description: "Монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай.",
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
          <BrandWordmark />
        </Link>
        <Link href="/" className="mw-seo-cta">
          Шалгах
        </Link>
      </header>

      <article className="mw-seo-article">
        <h1>Үгийн алдаа шалгах</h1>
        <p className="mw-seo-lead">
          MongolWrite дээр монгол кирилл текстээ оруулаад үгийн алдааг шалгана. Алдаатай
          үгийг засаад, хүсвэл уламжлалт монгол бичиг рүү хөрвүүлж Word файлаар татна.
        </p>

        <p>
          <Link href="/" className="mw-seo-cta mw-seo-cta-inline">
            Үгийн алдаагаа шалгах →
          </Link>
        </p>

        <h2>Үгийн алдаа гэж юу вэ?</h2>
        <p>
          Үгийн алдаа гэдэг нь үгийг зөв бичгийн дүрмийн дагуу бичээгүй байхыг хэлнэ.
          Жишээлбэл, үгийн эцэс, холбоос, өөрөөсөө хамаарах нэмэлтүүдийг буруу бичсэн тохиолдолд
          утга өөрчлөгдөж, уншихад төвөгтэй болно.
        </p>
        <p>
          Ийм алдааг нүдээр олох хэцүү. Тиймээс текстээ энд оруулаад шалгавал алдаатай
          үгсийг тэмдэглэж, зөв хэлбэрийг санал болгоно.
        </p>

        <h2>Юу хийж чадах вэ?</h2>
        <p>
          Текстээ бичээд эсвэл файл нээгээд <strong>Шалгах</strong> товч дарна. Систем
          алдаатай үгсийг тэмдэглэж, засах санал гаргана. Та зөв хэлбэрийг сонгоод солино.
        </p>
        <p>
          Мөн кириллээс монгол бичиг рүү хөрвүүлж, бэлэн болсон бичвэрээ Word (.docx)
          файлаар авч болно. Вэб дээр шууд ажиллана — суулгах программ шаардлагагүй.
        </p>

        <h2>Хэрхэн ашиглах вэ?</h2>
        <ol>
          <li>
            <Link href="/">Нүүр хуудас</Link> руу орно
          </li>
          <li>Текстээ бичнэ, эсвэл Word, текст файл нээнэ</li>
          <li>
            <strong>Шалгах</strong> товч дарна
          </li>
          <li>Алдаатай үгийг засаад, хүсвэл монгол бичиг рүү хөрвүүлж татна</li>
        </ol>

        <h2>Хязгаар ба төлбөр</h2>
        <p>
          Зочин болон үнэгүй бүртгэлтэй хэрэглэгч бага хэмжээний текстээр туршиж үзнэ.
          Урт бичвэр, монгол бичиг хөрвүүлэх зэрэг бүрэн боломжийг төлбөртэй эрхээр нээнэ.
          Дэлгэрэнгүйг <Link href="/tolbor">төлбөрийн багц</Link> хуудаснаас үзнэ үү.
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
