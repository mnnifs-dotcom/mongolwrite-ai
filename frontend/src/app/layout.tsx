import type { Metadata, Viewport } from "next";
import "./globals.css";

const SITE = "https://mongolwrite.com";

export const viewport: Viewport = {
  themeColor: "#1f6fad",
};

const titleDefault = "Үгийн алдаа шалгах | MongolWrite — монгол үгийн алдаа шалгагч";
const descriptionDefault =
  "Үгийн алдаа шалгах онлайн. Монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай. Монгол бичиг рүү хөрвүүлэх, Word файлаар татах.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: {
    default: titleDefault,
    template: "%s | MongolWrite",
  },
  description: descriptionDefault,
  applicationName: "MongolWrite",
  keywords: [
    "үгийн алдаа шалгах",
    "үгийн алдаа шалгагч",
    "монгол үгийн алдаа шалгах",
    "монгол үгийн алдаа шалгагч",
    "алдаа шалгах",
    "монгол алдаа шалгах",
    "бичгийн алдаа шалгах",
    "монгол хэлний алдаа шалгагч",
    "монгол зөв бичих",
    "онлайн алдаа шалгагч",
    "монгол бичиг хөрвүүлэх",
    "spellcheck",
    "MongolWrite",
  ],
  authors: [{ name: "MongolWrite" }],
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-48.png", sizes: "48x48", type: "image/png" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
    shortcut: ["/favicon.ico"],
  },
  openGraph: {
    title: titleDefault,
    description: descriptionDefault,
    url: SITE,
    siteName: "MongolWrite",
    locale: "mn_MN",
    type: "website",
    images: [{ url: "/logo-512.png", width: 512, height: 512, alt: "MongolWrite үгийн алдаа шалгагч" }],
  },
  twitter: {
    card: "summary",
    title: titleDefault,
    description: descriptionDefault,
    images: ["/logo-512.png"],
  },
  manifest: "/site.webmanifest",
  category: "productivity",
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${SITE}/#website`,
      url: SITE,
      name: "MongolWrite",
      alternateName: [
        "Үгийн алдаа шалгах",
        "Монгол үгийн алдаа шалгагч",
        "Алдаа шалгах",
      ],
      description: descriptionDefault,
      inLanguage: "mn",
      potentialAction: {
        "@type": "ReadAction",
        target: `${SITE}/ugiin-aldaga-shalgah`,
      },
    },
    {
      "@type": "WebApplication",
      "@id": `${SITE}/#app`,
      name: "MongolWrite",
      alternateName: "Үгийн алдаа шалгах — MongolWrite",
      url: SITE,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      inLanguage: "mn",
      description: descriptionDefault,
      offers: [
        {
          "@type": "Offer",
          name: "3 сар",
          price: "6000",
          priceCurrency: "MNT",
          category: "төлбөртэй эрх — 3 сар",
        },
        {
          "@type": "Offer",
          name: "1 жил",
          price: "19900",
          priceCurrency: "MNT",
          category: "төлбөртэй эрх — жилийн эрх",
        },
      ],
      featureList: [
        "Үгийн алдаа шалгах",
        "Бичгийн алдаа засах",
        "Монгол бичиг хөрвүүлэх",
        "Word татах",
      ],
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="mn">
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        {children}
      </body>
    </html>
  );
}
