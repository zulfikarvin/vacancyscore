import { cn } from "@/lib/utils";

interface ProgressProps {
  /** 0-100. */
  value: number;
  className?: string;
  /** Tailwind background class for the filled portion. */
  indicatorClassName?: string;
  label?: string;
}

/**
 * A labelled bar. Used for the hero sub-scores and the CV similarity list, so
 * it takes its fill colour from the caller rather than assuming one.
 */
function Progress({ value, className, indicatorClassName, label }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-violet-100", className)}
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div
        className={cn(
          "h-full rounded-full bg-accent transition-[width] duration-700 ease-out",
          indicatorClassName,
        )}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

export { Progress };
