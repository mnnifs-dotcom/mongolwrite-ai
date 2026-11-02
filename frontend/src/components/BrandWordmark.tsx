type BrandWordmarkProps = {
  /** Full label for aria / admin suffixes, e.g. "MongolWrite · Админ" */
  label?: string;
  className?: string;
};

/** Two-tone MongolWrite mark: navy "Mongol" + bright blue "Write". */
export function BrandWordmark({ label = "MongolWrite", className = "" }: BrandWordmarkProps) {
  const suffix = label.startsWith("MongolWrite") ? label.slice("MongolWrite".length) : "";
  const showSplit = label.startsWith("MongolWrite");

  return (
    <span className={["mw-brand-text", className].filter(Boolean).join(" ")}>
      {showSplit ? (
        <>
          <span className="mw-brand-mongol">Mongol</span>
          <span className="mw-brand-write">Write</span>
          {suffix ? <span className="mw-brand-suffix">{suffix}</span> : null}
        </>
      ) : (
        label
      )}
    </span>
  );
}
