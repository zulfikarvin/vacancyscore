import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-violet-100 text-secondary",
        outline: "border border-hairline bg-surface text-ink-muted",
        muted: "bg-canvas text-ink-muted",
        dark: "bg-white/10 text-white ring-1 ring-white/15",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

interface BadgeProps
  extends React.ComponentProps<"span">,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
