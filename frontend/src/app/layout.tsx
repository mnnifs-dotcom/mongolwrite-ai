import type { Metadata, Viewport } from "next";
import { Noto_Sans, Noto_Serif } from "next/font/google";
import "./globals.css";

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

export const metadata: Metadata = {
  metadataBase: new URL("https://mongolwrite-ai.fly.dev"),
  title: "MongolWrite AI",
  description: "Монгол зөв бичих · Монгол бичиг хөрвүүлэх",
  applicationName: "MongolWrite",
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
    title: "MongolWrite AI",
    description: "Монгол зөв бичих · Монгол бичиг хөрвүүлэх",
    siteName: "MongolWrite",
    images: [{ url: "/logo-512.png", width: 512, height: 512, alt: "MongolWrite" }],
  },
  twitter: {
    card: "summary",
    title: "MongolWrite AI",
    description: "Монгол зөв бичих · Монгол бичиг хөрвүүлэх",
    images: ["/logo-512.png"],
  },
  manifest: "/site.webmanifest",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="mn" className={`${sans.variable} ${display.variable}`}>
      <body>{children}</body>
    </html>
  );
}
