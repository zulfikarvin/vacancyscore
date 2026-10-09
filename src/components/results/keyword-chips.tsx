"use client";

import { Check, X } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { MatchedKeyword } from "@/lib/types";

export function KeywordChips({
  matched,
  missing,
}: {
  matched: MatchedKeyword[];
  missing: string[];
}) {
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>
            Matched keywords
            <span className="tabular ml-2 font-normal text-ink-muted">
              {matched.length}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {matched.length === 0 ? (
            <Empty>No vacancy keywords are evidenced in this CV.</Empty>
          ) : (
            matched.map((item) => (
              <Tooltip key={item.keyword}>
                <TooltipTrigger asChild>
                  <span
                    tabIndex={0}
                    className="inline-flex cursor-default items-center gap-1.5 rounded-full bg-violet-100 px-3 py-1.5 text-xs font-medium text-secondary outline-none transition-colors hover:bg-violet-200/60 focus-visible:ring-2 focus-visible:ring-accent"
                  >
                    <Check className="size-3.5 text-accent" strokeWidth={3} />
                    {item.keyword}
                  </span>
                </TooltipTrigger>
                <TooltipContent>Found in {item.location}</TooltipContent>
              </Tooltip>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            Missing keywords
            <span className="tabular ml-2 font-normal text-ink-muted">
              {missing.length}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {missing.length === 0 ? (
            <Empty>Nothing missing — this CV covers every keyword.</Empty>
          ) : (
            missing.map((keyword) => (
              <span
                key={keyword}
                className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-canvas px-3 py-1.5 text-xs font-medium text-ink-muted"
              >
                <X className="size-3.5 text-danger/70" strokeWidth={3} />
                {keyword}
              </span>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-ink-muted">{children}</p>;
}
