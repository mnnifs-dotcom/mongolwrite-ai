import type { Metadata } from "next";
import Link from "next/link";
import { EditorApp } from "@/components/EditorApp";

export const metadata: Metadata = {
  title: {
    absolute: "Алдаа шалгах | MongolWrite — монгол үгийн алдаа шалгагч",
  },
  description:
    "Алдаа шалгах онлайн. Монгол текстээ буулгаад үгийн алдааг олж засаарай. Монгол бичиг хөрвүүлэх, Word татах.",
  alternates: { canonical: "/" },
};

export default function Home() {
  return (
    <>
      <h1 className="mw-seo-sr-only">Алдаа шалгах — монгол үгийн алдаа шалгагч онлайн | MongolWrite</h1>
      <EditorApp />
      <nav className="mw-seo-sr-only" aria-label="SEO холбоос">
        <Link href="/aldaga-shalgah">Алдаа шалгах тухай</Link>
        <Link href="/ugiin-aldaga-shalgah">Үгийн алдаа шалгах</Link>
      </nav>
    </>
  );
}
