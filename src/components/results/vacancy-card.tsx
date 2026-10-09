"use client";

import { useState } from "react";
import { ChevronDown, PencilLine } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * The pasted vacancy, parked at the bottom of the results so it stays readable
 * without competing with the score.
 */
export function VacancyCard({
  text,
  onEdit,
}: {
  text: string;
  onEdit?: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 p-5">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="flex flex-1 items-center gap-3 rounded-lg text-left outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <ChevronDown
            className={cn(
              "size-4 shrink-0 text-ink-muted transition-transform duration-200",
              open && "rotate-180",
            )}
          />
          <span className="text-sm font-medium text-primary">
            Vacancy text
            <span className="tabular ml-2 font-normal text-ink-muted">
              {text.length.toLocaleString()} chars
            </span>
          </span>
        </button>

        {onEdit && (
          <Button variant="ghost" size="sm" onClick={onEdit}>
            <PencilLine />
            Edit and re-run
          </Button>
        )}
      </div>

      {open && (
        <div className="scroll-slim max-h-[28rem] overflow-y-auto border-t border-hairline bg-canvas/50 px-5 py-5">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-muted">
            {text}
          </p>
        </div>
      )}
    </Card>
  );
}
