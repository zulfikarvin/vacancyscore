import * as React from "react";

import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "h-11 w-full rounded-xl border border-hairline bg-surface px-3.5 text-sm text-ink outline-none transition-colors",
        "placeholder:text-ink-muted/70",
        "focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25",
        "file:mr-3 file:h-full file:cursor-pointer file:rounded-lg file:border-0 file:bg-violet-100 file:px-3 file:text-sm file:font-medium file:text-secondary",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
