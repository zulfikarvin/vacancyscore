"use client";

import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { CVScore } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Step 1 of the pipeline, made visible: which CV won and by how much. The
 * combines local semantic fit with a transparent evidence-strength heuristic.
 */
export function RecommendedCVCard({
  scores,
  recommendedId,
  recommendedLabel,
}: {
  scores: CVScore[];
  recommendedId: number | null;
  recommendedLabel: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recommended CV</CardTitle>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <Badge>
            <Sparkles className="size-3.5" />
            {recommendedLabel}
          </Badge>
          <span className="text-sm text-ink-muted">
            strongest relevant CV out of {scores.length}{" "}
            {scores.length === 1 ? "CV" : "CVs"}
          </span>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {scores.map((score) => {
          const isWinner = score.cv_id === recommendedId;
          const strength = score.strength_score ?? 0;
          const selection = score.selection_score || score.similarity;
          return (
            <div key={score.cv_id}>
              <div className="flex items-baseline justify-between gap-3">
                <span
                  className={cn(
                    "truncate text-sm",
                    isWinner ? "font-medium text-primary" : "text-ink-muted",
                  )}
                >
                  {score.label}
                </span>
                <span
                  className={cn(
                    "tabular shrink-0 text-sm",
                    isWinner ? "font-semibold text-accent" : "text-ink-muted",
                  )}
                >
                  {selection.toFixed(0)}%
                </span>
              </div>
              <Progress
                className="mt-2"
                value={selection}
                label={`${score.label} overall selection score`}
                indicatorClassName={cn(
                  isWinner
                    ? "bg-gradient-to-r from-accent to-accent-light"
                    : "bg-violet-200",
                )}
              />
              <p className="mt-1.5 text-xs text-ink-muted">
                Vacancy fit {score.similarity.toFixed(0)}% · CV strength {strength.toFixed(0)}%
              </p>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
