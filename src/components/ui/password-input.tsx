"use client";

import { useState, type ComponentProps } from "react";
import { Eye, EyeOff } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function PasswordInput({ className, disabled, ...props }: Omit<ComponentProps<typeof Input>, "type">) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      <Input
        {...props}
        type={visible ? "text" : "password"}
        disabled={disabled}
        className={cn("pr-12", className)}
      />
      <button
        type="button"
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
        aria-controls={props.id}
        disabled={disabled}
        onClick={() => setVisible((current) => !current)}
        className="absolute inset-y-0 right-1 flex w-10 items-center justify-center rounded-lg text-ink-muted outline-none hover:text-accent focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
      >
        {visible ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}
      </button>
    </div>
  );
}
