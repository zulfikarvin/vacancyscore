import { cn } from "@/lib/utils";

/**
 * Wordmark. The mark is a filled gauge arc, echoing the fit-score gauge that
 * is the centrepiece of the results.
 */
export function Logo({
  className,
  onDark = false,
}: {
  className?: string;
  onDark?: boolean;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <svg viewBox="0 0 32 32" className="size-7" aria-hidden="true">
        <circle
          cx="16"
          cy="16"
          r="12"
          fill="none"
          stroke={onDark ? "rgba(255,255,255,0.18)" : "var(--color-violet-100)"}
          strokeWidth="5"
        />
        <circle
          cx="16"
          cy="16"
          r="12"
          fill="none"
          stroke="url(#logo-arc)"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${0.68 * 2 * Math.PI * 12} ${2 * Math.PI * 12}`}
          transform="rotate(-90 16 16)"
        />
        <defs>
          <linearGradient id="logo-arc" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--color-accent)" />
            <stop offset="100%" stopColor="var(--color-accent-light)" />
          </linearGradient>
        </defs>
      </svg>
      <span
        className={cn(
          "text-lg font-semibold tracking-tight",
          onDark ? "text-white" : "text-primary",
        )}
      >
        Vacancy<span className="text-accent">Score</span>
      </span>
    </span>
  );
}
