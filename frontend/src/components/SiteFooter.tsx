import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mw-site-footer">
      <nav className="mw-site-footer-nav" aria-label="Холбоос">
        <Link href="/uilchilgeenii-nokhtsol">Үйлчилгээний нөхцөл</Link>
        <Link href="/aldaa-medegdeh">Алдаа мэдэгдэх</Link>
        <Link href="/aldaga-shalgah">Алдаа шалгах</Link>
      </nav>
      <p className="mw-site-footer-copy">© {new Date().getFullYear()} MongolWrite · mongolwrite.com</p>
    </footer>
  );
}
