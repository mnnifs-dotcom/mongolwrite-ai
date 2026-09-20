import type { Metadata } from "next";
import Link from "next/link";
import { EditorApp } from "@/components/EditorApp";

export const metadata: Metadata = {
  title: {
    absolute: "Алдаа шалгах | MongolWrite — монгол үгийн алдаа шалгагч",
  },
  description:
    "Монгол бичвэрийн үгийн алдааг онлайнаар шалгаж засаарай. Монгол бичиг рүү хөрвүүлэх, Word файлаар татах.",
  alternates: { canonical: "/" },
};

export default function Home() {
  return (
    <>
      <h1 className="mw-seo-sr-only">Алдаа шалгах — монгол үгийн алдаа шалгагч | MongolWrite</h1>
      <EditorApp />
      <nav className="mw-seo-sr-only" aria-label="Нэмэлт холбоос">
        <Link href="/aldaga-shalgah">Алдаа шалгах тухай</Link>
        <Link href="/ugiin-aldaga-shalgah">Үгийн алдаа шалгах</Link>
        <Link href="/uilchilgeenii-nokhtsol">Үйлчилгээний нөхцөл</Link>
        <Link href="/aldaa-medegdeh">Алдаа мэдэгдэх</Link>
      </nav>
    </>
  );
}
