import type { Metadata } from "next";
import Link from "next/link";
import { EditorApp } from "@/components/EditorApp";

export const metadata: Metadata = {
  title: {
    absolute: "Үгийн алдаа шалгах | MongolWrite — монгол үгийн алдаа шалгагч",
  },
  description:
    "Үгийн алдаа шалгах онлайн. Монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай. Монгол бичиг рүү хөрвүүлэх, Word файлаар татах.",
  alternates: { canonical: "/" },
  openGraph: {
    title: "Үгийн алдаа шалгах | MongolWrite",
    description:
      "Монгол кирилл бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай.",
    url: "https://mongolwrite.com/",
  },
};

export default function Home() {
  return (
    <>
      <h1 className="mw-seo-sr-only">
        Үгийн алдаа шалгах — монгол үгийн алдаа шалгагч | MongolWrite
      </h1>
      <EditorApp />
      <nav className="mw-seo-sr-only" aria-label="Нэмэлт холбоос">
        <Link href="/ugiin-aldaga-shalgah">Үгийн алдаа шалгах</Link>
        <Link href="/aldaga-shalgah">Алдаа шалгах тухай</Link>
        <Link href="/uilchilgeenii-nokhtsol">Үйлчилгээний нөхцөл</Link>
        <Link href="/aldaa-medegdeh">Алдаа мэдэгдэх</Link>
      </nav>
    </>
  );
}
