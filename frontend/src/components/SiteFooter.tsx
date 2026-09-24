import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mw-site-footer">
      <nav className="mw-site-footer-nav" aria-label="Холбоос">
        <Link href="/ugiin-aldaga-shalgah">Үгийн алдаа шалгах</Link>
        <Link href="/aldaga-shalgah">Алдаа шалгах</Link>
        <Link href="/tolbor">Төлбөр</Link>
        <Link href="/aldaa-medegdeh">Алдаа мэдэгдэх</Link>
        <Link href="/uilchilgeenii-nokhtsol">Үйлчилгээний нөхцөл</Link>
      </nav>
      <p className="mw-site-footer-copy">© {new Date().getFullYear()} MongolWrite · mongolwrite.com</p>
    </footer>
  );
}
