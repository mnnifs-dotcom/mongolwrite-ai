import { BrandWordmark } from "@/components/BrandWordmark";

type BrandLogoProps = {
  /** Compact header mark vs login/hero size */
  size?: "sm" | "md" | "lg";
  withWordmark?: boolean;
  wordmark?: string;
  className?: string;
};

const SIZES = {
  sm: 28,
  md: 36,
  lg: 72,
} as const;

export function BrandLogo({
  size = "md",
  withWordmark = true,
  wordmark = "MongolWrite",
  className = "",
}: BrandLogoProps) {
  const px = SIZES[size];
  const height = Math.round((px * 746) / 815);
  return (
    <div className={["mw-brand", className].filter(Boolean).join(" ")} aria-label={wordmark}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/logo.png"
        alt=""
        width={px}
        height={height}
        className="mw-brand-logo"
        decoding="async"
      />
      {withWordmark ? <BrandWordmark label={wordmark} /> : null}
    </div>
  );
}
