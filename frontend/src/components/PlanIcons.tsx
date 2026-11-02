/** Decorative plan icons for pricing cards / upgrade modal. */

type IconProps = { className?: string };

export function PlanIconFree({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 40 40" width="40" height="40" aria-hidden>
      <circle cx="20" cy="20" r="20" fill="#e8f6ee" />
      <path
        d="M20 10c.4 3.2 2.6 5.4 5.8 5.8-3.2.4-5.4 2.6-5.8 5.8-.4-3.2-2.6-5.4-5.8-5.8 3.2-.4 5.4-2.6 5.8-5.8Z"
        fill="#1f8a4c"
      />
      <circle cx="20" cy="20" r="2.2" fill="#fff" />
      <path
        d="M20 26.5v3.5M16.5 24.2l-2.2 2.2M23.5 24.2l2.2 2.2"
        stroke="#1f8a4c"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function PlanIconQuarter({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 40 40" width="40" height="40" aria-hidden>
      <circle cx="20" cy="20" r="20" fill="#e8f1fb" />
      <rect x="11" y="11" width="7.5" height="7.5" rx="1.6" fill="#1f6fad" />
      <rect x="21.5" y="11" width="7.5" height="7.5" rx="1.6" fill="#5a9ed0" />
      <rect x="11" y="21.5" width="7.5" height="7.5" rx="1.6" fill="#5a9ed0" />
      <rect x="21.5" y="21.5" width="7.5" height="7.5" rx="1.6" fill="#1f6fad" />
    </svg>
  );
}

export function PlanIconYear({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 40 40" width="40" height="40" aria-hidden>
      <circle cx="20" cy="20" r="20" fill="#e4eef8" />
      <path
        d="M20 8.5 24.2 16.8 33.5 18.2 26.8 24.6 28.4 33.8 20 29.4 11.6 33.8 13.2 24.6 6.5 18.2 15.8 16.8Z"
        fill="#1f6fad"
      />
      <path
        d="M20 13.2 22.3 17.8 27.4 18.6 23.7 22.1 24.6 27.2 20 24.8 15.4 27.2 16.3 22.1 12.6 18.6 17.7 17.8Z"
        fill="#7eb6de"
      />
    </svg>
  );
}
