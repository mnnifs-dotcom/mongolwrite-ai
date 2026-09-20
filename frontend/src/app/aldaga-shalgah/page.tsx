import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";

export const metadata: Metadata = {
  title: {
    absolute: "Алдаа шалгах | Монгол үгийн алдаа шалгагч — MongolWrite",
  },
  description:
    "Монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай. Монгол бичиг рүү хөрвүүлэх, Word файлаар татах. Программ суулгахгүй.",
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
    description: "Монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай.",
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
          MongolWrite бол монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгадаг хэрэгсэл.
          Текстээ бичээд эсвэл файл нээгээд шалгахад алдаатай үгсийг тэмдэглэж, зөв хэлбэрийг
          санал болгоно.
        </p>

        <p>
          <Link href="/" className="mw-seo-cta mw-seo-cta-inline">
            Эндээс шалгах →
          </Link>
        </p>

        <h2>Яагаад үгийн алдаагаа шалгах вэ?</h2>
        <p>
          Албан бичиг, сургуулийн даалгавар, нийтлэл бичихэд нэг үг буруу орвол утга
          өөрчлөгдөж, уншигчид найдваргүй сэтгэгдэл үлдээнэ. Бүхэл текстээ гараар дахин
          уншиж олох нь цаг авна, заримдаа алдааг өөрөө анзаарахгүй өнгөрнө.
        </p>
        <p>
          Онлайн алдаа шалгагч ашиглавал текстээ хэдхэн секундэд шалгаж, эргэлзээтэй үгсийг
          нэг дор харж болно. Ингэснээр засах ажил хурдан, цэгцтэй болно.
        </p>

        <h2>MongolWrite юу хийдэг вэ?</h2>
        <p>
          Гол зорилго нь монгол үгийн зөв бичгийг шалгах явдал. Та текстээ оруулахад систем
          үг бүрийг үгийн сан, дүрэмтэй тулган үзэж, алдаатай эсвэл эргэлзээтэй хэсгийг
          тэмдэглэнэ. Дараа нь санал болгосон зөв хэлбэрээс сонгоод солино.
        </p>
        <p>
          Шаардлагатай бол кирилл текстээ уламжлалт монгол бичиг рүү хөрвүүлж, Word (.docx)
          файлаар татаж авч болно. Бүгд вэб дээр ажиллана — тусад нь программ суулгах
          шаардлагагүй.
        </p>

        <h2>Хэрхэн ашиглах вэ?</h2>
        <ol>
          <li>
            <Link href="/">mongolwrite.com</Link> руу орно
          </li>
          <li>Текстээ бичнэ, эсвэл Word, текст файл нээнэ</li>
          <li>
            <strong>Шалгах</strong> товч дарна
          </li>
          <li>Алдаатай үгийг засаад, хүсвэл монгол бичиг рүү хөрвүүлж татна</li>
        </ol>

        <h2>Хэн хэрэглэж болох вэ?</h2>
        <p>
          Сурагч, багш, албан хаагч, сэтгүүлч — монголоор бичдэг хэн бүхэнд хэрэгтэй. Зочин
          хэрэглэгч бага хэмжээний текстээр туршиж үзэж болно. Илүү урт бичвэр шалгах,
          монгол бичиг хөрвүүлэх зэрэг бүрэн боломжийг төлбөртэй эрхээр нээнэ. Дэлгэрэнгүйг{" "}
          <Link href="/tolbor">төлбөрийн багц</Link> хуудаснаас үзнэ үү.
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
