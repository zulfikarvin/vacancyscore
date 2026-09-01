"use client";

import { Check } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Anchored as #tips: the hero CTA scrolls here.
 */
export function TipsList({ tips }: { tips: string[] }) {
  return (
    <Card id="tips" className="scroll-mt-24">
      <CardHeader>
        <CardTitle>Do these edits</CardTitle>
        <p className="text-sm text-ink-muted">
          Concrete changes to this CV, in the order they pay off.
        </p>
      </CardHeader>
      <CardContent>
        {tips.length === 0 ? (
          <p className="text-sm text-ink-muted">No edits suggested.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {tips.map((tip, index) => (
              <li
                key={index}
                className="flex items-start gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-violet-100/60"
              >
                <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-md border border-hairline bg-canvas text-accent">
                  <Check className="size-3.5" strokeWidth={3} />
                </span>
                <span className="text-sm leading-relaxed text-ink">{tip}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
