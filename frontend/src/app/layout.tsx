import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MongolWrite AI",
  description: "Монгол хэлний бичгийн туслах",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="mn">
      <body>{children}</body>
    </html>
  );
}
