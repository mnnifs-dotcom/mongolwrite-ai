import type { Metadata } from "next";
import Link from "next/link";
import { EditorApp } from "@/components/EditorApp";

export const metadata: Metadata = {
  title: {
    absolute: "Үгийн алдаа шалгах | MongolWrite — монгол зөв бичих",
  },
  description:
    "Монгол үгийн алдаа шалгах онлайн. Текстээ буулгаад алдаатай үгсийг олж засаарай. Монгол бичиг хөрвүүлэх, Word татах.",
  alternates: { canonical: "/" },
};

export default function Home() {
  return (
    <>
      <h1 className="mw-seo-sr-only">Үгийн алдаа шалгах — монгол зөв бичих онлайн | MongolWrite</h1>
      <EditorApp />
      <nav className="mw-seo-sr-only" aria-label="SEO холбоос">
        <Link href="/ugiin-aldaga-shalgah">Үгийн алдаа шалгах тухай</Link>
      </nav>
    </>
  );
}
