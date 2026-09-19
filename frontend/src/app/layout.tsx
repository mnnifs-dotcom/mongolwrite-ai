import type { Metadata, Viewport } from "next";
import { Noto_Sans, Noto_Serif } from "next/font/google";
import "./globals.css";

const SITE = "https://mongolwrite-ai.fly.dev";

const sans = Noto_Sans({
  subsets: ["cyrillic", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const display = Noto_Serif({
  subsets: ["cyrillic", "latin"],
  weight: ["600", "700"],
  variable: "--font-display",
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#1f6fad",
};

const titleDefault = "Үгийн алдаа шалгах | MongolWrite — монгол зөв бичих";
const descriptionDefault =
  "Монгол үгийн алдаа шалгах, бичгийн алдаа засах онлайн. Кирилл текстээ шалгаад засварлаж, монгол бичиг рүү хөрвүүлээд Word-оор татаж авна.";

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
    "бичгийн алдаа шалгах",
    "монгол хэлний алдаа шалгагч",
    "монгол зөв бичих",
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
      description: descriptionDefault,
      inLanguage: "mn",
    },
    {
      "@type": "WebApplication",
      "@id": `${SITE}/#app`,
      name: "MongolWrite",
      url: SITE,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      inLanguage: "mn",
      description: descriptionDefault,
      offers: {
        "@type": "Offer",
        price: "19900",
        priceCurrency: "MNT",
        category: "нээлтийн урамшуулал — жилийн эрх",
      },
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
    <html lang="mn" className={`${sans.variable} ${display.variable}`}>
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
