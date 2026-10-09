"use client";

import { useMemo, useState } from "react";
import { ArrowDownWideNarrow, ArrowUpNarrowWide } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GapRow } from "@/lib/types";
import { cn, severityChip, severityRank } from "@/lib/utils";

export function GapTable({ gaps }: { gaps: GapRow[] }) {
  const [descending, setDescending] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...gaps];
    copy.sort((a, b) => {
      const delta = severityRank[a.severity] - severityRank[b.severity];
      return descending ? -delta : delta;
    });
    return copy;
  }, [gaps, descending]);

  if (gaps.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Gaps</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-ink-muted">
            No gaps found against the stated requirements.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Gaps
          <span className="tabular ml-2 font-normal text-ink-muted">
            {gaps.length}
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent className="px-0 pb-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-y border-hairline bg-canvas/60">
                <Th className="w-[24%]">Requirement</Th>
                <Th className="w-[26%]">Your CV shows</Th>
                <Th className="w-[12%]">
                  <button
                    type="button"
                    onClick={() => setDescending((d) => !d)}
                    className="inline-flex items-center gap-1.5 rounded outline-none transition-colors hover:text-accent focus-visible:ring-2 focus-visible:ring-accent"
                    aria-label={
                      descending
                        ? "Sort by severity, lowest first"
                        : "Sort by severity, highest first"
                    }
                  >
                    Severity
                    {descending ? (
                      <ArrowDownWideNarrow className="size-3.5" />
                    ) : (
                      <ArrowUpNarrowWide className="size-3.5" />
                    )}
                  </button>
                </Th>
                <Th className="w-[38%]">Suggested fix</Th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((gap, index) => (
                <tr
                  key={`${gap.requirement}-${index}`}
                  className="border-b border-hairline last:border-0 hover:bg-violet-100/50"
                >
                  <td className="px-6 py-4 align-top font-medium text-ink">
                    {gap.requirement}
                  </td>
                  <td className="px-6 py-4 align-top text-ink-muted">
                    {gap.cv_evidence || (
                      <span className="italic text-ink-muted/70">Nothing yet</span>
                    )}
                  </td>
                  <td className="px-6 py-4 align-top">
                    <span
                      className={cn(
                        "inline-flex rounded-full px-2.5 py-1 text-xs font-medium capitalize ring-1",
                        severityChip[gap.severity],
                      )}
                    >
                      {gap.severity}
                    </span>
                  </td>
                  <td className="px-6 py-4 align-top leading-relaxed text-ink">
                    {gap.suggested_fix}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function Th({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <th
      scope="col"
      className={cn(
        "px-6 py-3 text-xs font-medium uppercase tracking-wider text-ink-muted",
        className,
      )}
    >
      {children}
    </th>
  );
}
