import * as React from "react";

import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full resize-none rounded-2xl border border-hairline bg-surface p-5 text-sm leading-relaxed text-ink outline-none transition-colors",
      "placeholder:text-ink-muted/70",
      "focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/20",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export { Textarea };
