"use client";

import { ArrowDown, Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { FitGauge } from "@/components/results/fit-gauge";
import type { SubScores, VacancyAnalysis } from "@/lib/types";
import { cn, scoreBand, scoreOnDark } from "@/lib/utils";

const ENCOURAGEMENT = {
  weak: "Sizeable gaps here — start with the high-severity rows below.",
  fair: "Score can improve — tailor your CV for this vacancy.",
  strong: "Strong match — tighten the details below and send it.",
} as const;

/**
 * The one dark card in the app: a spotlight for the score, the matched skills
 * and the three sub-scores. Everything else on the page is white-on-off-white.
 */
export function HeroCard({
  analysis,
  subScores,
  onViewSuggestions,
}: {
  analysis: VacancyAnalysis;
  subScores: SubScores;
  onViewSuggestions: () => void;
}) {
  const band = scoreBand(analysis.fit_score);
  const matched = analysis.matched_keywords;

  return (
    <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary-dark via-primary-dark to-primary p-7 shadow-hero sm:p-9">
      {/* Soft spotlight behind the gauge. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-24 -top-24 size-80 rounded-full bg-accent/25 blur-3xl"
      />

      <div className="relative flex flex-col gap-9 lg:flex-row lg:items-start lg:gap-10">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center lg:shrink-0">
          <FitGauge score={analysis.fit_score} />

          <div className="max-w-xs text-center sm:text-left">
            <h2
              className={cn(
                "text-3xl font-semibold tracking-tight",
                scoreOnDark[band],
              )}
            >
              {analysis.fit_label}
            </h2>
            <p className="mt-1 text-sm text-violet-200">
              {matched.length} relevant {matched.length === 1 ? "skill" : "skills"}
            </p>
            <p className="mt-4 text-sm leading-relaxed text-white/70">
              {analysis.summary}
            </p>
          </div>
        </div>

        <div className="flex-1 lg:border-l lg:border-white/10 lg:pl-10">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-violet-300">
            Matched skills
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {matched.length === 0 ? (
              <p className="text-sm text-white/60">
                Nothing in this CV matched the vacancy requirements.
              </p>
            ) : (
              matched.map((item) => (
                <span
                  key={item.keyword}
                  title={`Found in ${item.location}`}
                  className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white ring-1 ring-white/15"
                >
                  <Check className="size-3.5 text-violet-300" strokeWidth={3} />
                  {item.keyword}
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="relative mt-9 grid gap-5 border-t border-white/10 pt-7 sm:grid-cols-3 sm:gap-8">
        <DarkBar label="Profile" value={subScores.profile} />
        <DarkBar label="Skills" value={subScores.skills} />
        <DarkBar label="Summary" value={subScores.summary} />
      </div>

      <div className="relative mt-8 flex flex-col items-start gap-4 border-t border-white/10 pt-7 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-violet-200">{ENCOURAGEMENT[band]}</p>
        <Button variant="cta" onClick={onViewSuggestions} className="shrink-0">
          View suggestions
          <ArrowDown />
        </Button>
      </div>
    </section>
  );
}

function DarkBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium text-white/85">{label}</span>
        <span
          className={cn("tabular text-sm font-semibold", scoreOnDark[scoreBand(value)])}
        >
          {value}%
        </span>
      </div>
      <div
        className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-accent to-violet-300 transition-[width] duration-1000 ease-out"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}
