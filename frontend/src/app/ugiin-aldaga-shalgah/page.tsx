import type { Metadata } from "next";
import Link from "next/link";

import { BrandWordmark } from "@/components/BrandWordmark";
import { SiteFooter } from "@/components/SiteFooter";

const SITE = "https://mongolwrite.com";
const PATH = "/ugiin-aldaga-shalgah";
const TITLE = "Үгийн алдаа шалгах | Монгол үгийн алдаа шалгагч — MongolWrite";
const DESCRIPTION =
  "Үгийн алдаа шалгах онлайн хэрэгсэл. Монгол кирилл бичвэрийн үгийн алдааг шууд шалгаж засаарай. Монгол бичиг рүү хөрвүүлэх, Word файлаар татах.";

export const metadata: Metadata = {
  title: { absolute: TITLE },
  description: DESCRIPTION,
  keywords: [
    "үгийн алдаа шалгах",
    "үгийн алдаа шалгагч",
    "монгол үгийн алдаа шалгах",
    "монгол үгийн алдаа шалгагч",
    "алдаа шалгах",
    "бичгийн алдаа шалгах",
    "монгол алдаа шалгах",
    "монгол зөв бичих",
    "онлайн алдаа шалгагч",
    "MongolWrite",
  ],
  alternates: { canonical: PATH },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: `${SITE}${PATH}`,
    type: "article",
    locale: "mn_MN",
    siteName: "MongolWrite",
    images: [
      {
        url: "/logo-512.png",
        width: 512,
        height: 512,
        alt: "MongolWrite — үгийн алдаа шалгах",
      },
    ],
  },
  twitter: {
    card: "summary",
    title: TITLE,
    description: DESCRIPTION,
    images: ["/logo-512.png"],
  },
  robots: { index: true, follow: true },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebPage",
      "@id": `${SITE}${PATH}#webpage`,
      url: `${SITE}${PATH}`,
      name: TITLE,
      description: DESCRIPTION,
      inLanguage: "mn",
      isPartOf: { "@id": `${SITE}/#website` },
      about: {
        "@type": "Thing",
        name: "Үгийн алдаа шалгах",
      },
      primaryImageOfPage: {
        "@type": "ImageObject",
        url: `${SITE}/logo-512.png`,
      },
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        {
          "@type": "ListItem",
          position: 1,
          name: "Нүүр",
          item: SITE,
        },
        {
          "@type": "ListItem",
          position: 2,
          name: "Үгийн алдаа шалгах",
          item: `${SITE}${PATH}`,
        },
      ],
    },
    {
      "@type": "FAQPage",
      "@id": `${SITE}${PATH}#faq`,
      mainEntity: [
        {
          "@type": "Question",
          name: "Үгийн алдаа шалгах гэж юу вэ?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Үгийн алдаа шалгах гэдэг нь монгол кирилл бичвэр дэх зөв бичгийн алдаатай үгсийг олж, зөв хэлбэрийг санал болгохыг хэлнэ. MongolWrite дээр текстээ оруулаад онлайнаар шалгана.",
          },
        },
        {
          "@type": "Question",
          name: "Монгол үгийн алдаагаа хэрхэн шалгах вэ?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "mongolwrite.com руу орж текстээ бичнэ эсвэл файл нээнэ. Шалгах товч дарвал алдаатай үгс тэмдэглэгдэж, зөв хэлбэрийг сонгоод засна.",
          },
        },
        {
          "@type": "Question",
          name: "Үгийн алдаа шалгагч үнэгүй юу?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Зочин болон үнэгүй бүртгэлтэй хэрэглэгч бага хэмжээний текстээр үгийн алдаа шалгаж болно. Урт бичвэр, монгол бичиг хөрвүүлэх зэрэг бүрэн боломжийг төлбөртэй эрхээр нээнэ.",
          },
        },
        {
          "@type": "Question",
          name: "Программ суулгах шаардлагатай юу?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Үгүй. MongolWrite вэб дээр шууд ажиллана. Компьютер, утасны хөтчөөс үгийн алдаагаа шалгана.",
          },
        },
      ],
    },
  ],
};

export default function UgiinAldagaShalgahPage() {
  return (
    <main className="mw-seo-page">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <header className="mw-seo-top">
        <Link href="/" className="mw-seo-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="" width={36} height={33} />
          <BrandWordmark />
        </Link>
        <Link href="/" className="mw-seo-cta">
          Үгийн алдаа шалгах
        </Link>
      </header>

      <article className="mw-seo-article">
        <h1>Үгийн алдаа шалгах</h1>
        <p className="mw-seo-lead">
          MongolWrite бол монгол кирилл бичвэрийн <strong>үгийн алдаа шалгах</strong> онлайн
          хэрэгсэл. Текстээ оруулаад шалгахад алдаатай үгсийг тэмдэглэж, зөв хэлбэрийг санал
          болгоно. Хүсвэл уламжлалт монгол бичиг рүү хөрвүүлж, Word (.docx) файлаар татна.
        </p>

        <p>
          <Link href="/" className="mw-seo-cta mw-seo-cta-inline">
            Одоо үгийн алдаагаа шалгах →
          </Link>
        </p>

        <h2>Үгийн алдаа шалгах гэж юу вэ?</h2>
        <p>
          Үгийн алдаа гэдэг нь үгийг зөв бичгийн дүрмийн дагуу бичээгүй байхыг хэлнэ. Үгийн
          эцэс, холбоос, нэмэлтийг буруу бичвэл утга өөрчлөгдөж, уншихад төвөгтэй болно.
          Ийм алдааг нүдээр олох хэцүү тул онлайн үгийн алдаа шалгагч хэрэгтэй.
        </p>
        <p>
          MongolWrite дээр монгол текстээ оруулаад <strong>үгийн алдаа шалгах</strong> товч
          дарвал систем үг бүрийг үгийн сан, дүрэмтэй тулган үзэж, алдаатай эсвэл эргэлзээтэй
          хэсгийг тэмдэглэнэ.
        </p>

        <h2>Яагаад MongolWrite-аар шалгах вэ?</h2>
        <ul>
          <li>Монгол кирилл бичвэрт зориулсан үгийн алдаа шалгагч</li>
          <li>Онлайнаар шууд ажиллана — программ суулгахгүй</li>
          <li>Алдаатай үгийг засаад зөв хэлбэрийг сонгоно</li>
          <li>Кириллээс уламжлалт монгол бичиг рүү хөрвүүлнэ</li>
          <li>Бэлэн бичвэрээ Word файлаар татна</li>
        </ul>

        <h2>Үгийн алдаагаа хэрхэн шалгах вэ?</h2>
        <ol>
          <li>
            <Link href="/">mongolwrite.com</Link> нүүр хуудас руу орно
          </li>
          <li>Текстээ бичнэ, эсвэл Word, текст файл нээнэ</li>
          <li>
            <strong>Шалгах</strong> товч дарна
          </li>
          <li>Алдаатай үгийг засаад, хүсвэл монгол бичиг рүү хөрвүүлж татна</li>
        </ol>

        <h2>Түгээмэл асуулт</h2>
        <h3>Үгийн алдаа шалгагч үнэгүй юу?</h3>
        <p>
          Зочин болон үнэгүй бүртгэлтэй хэрэглэгч бага хэмжээний текстээр туршиж үзнэ. Урт
          бичвэр, монгол бичиг хөрвүүлэх зэрэг бүрэн боломжийг төлбөртэй эрхээр нээнэ.
          Дэлгэрэнгүйг <Link href="/tolbor">төлбөрийн багц</Link> хуудаснаас үзнэ үү.
        </p>
        <h3>Гар утсаар үгийн алдаа шалгаж болох уу?</h3>
        <p>
          Тийм. Хөтөч дээрээ mongolwrite.com нээгээд текстээ оруулаад шалгана. Тусдаа апп
          суулгах шаардлагагүй.
        </p>
        <h3>«Алдаа шалгах» болон «үгийн алдаа шалгах» юугаараа ойролцоо вэ?</h3>
        <p>
          Хоёулаа монгол бичвэрийн зөв бичгийг шалгах зорилготой. Дэлгэрэнгүй танилцуулгыг{" "}
          <Link href="/aldaga-shalgah">алдаа шалгах</Link> хуудаснаас уншиж болно.
        </p>

        <p className="mw-seo-foot-cta">
          <Link href="/" className="mw-seo-cta">
            Үгийн алдаа шалгах
          </Link>
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
