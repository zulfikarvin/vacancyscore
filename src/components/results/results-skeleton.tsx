"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, Search, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Shown for the 5-15s a real analysis takes. Mirrors the final layout so the
 * page does not jump when the data lands -- never a dead spinner.
 */
const STEPS = [
  { title: "Reading the vacancy", detail: "Identifying the role, company, and core requirements." },
  { title: "Ranking your CVs", detail: "Comparing the vacancy with your saved CV versions." },
  { title: "Checking requirements", detail: "Separating must-haves from preferred skills and keywords." },
  { title: "Building your fit analysis", detail: "Finding evidence, gaps, and the strongest CV to send." },
  { title: "Preparing recommendations", detail: "Turning the findings into specific CV edits." },
];

export function ResultsSkeleton({ mode = "analysis" }: { mode?: "analysis" | "history" }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const activeStep = Math.min(Math.floor(elapsed / 3), STEPS.length - 1);

  return (
    <div className="flex flex-col gap-5">
      <section className="overflow-hidden rounded-2xl border border-violet-200 bg-surface shadow-card" aria-live="polite">
        <div className="flex items-start gap-4 bg-violet-100/70 px-5 py-4 sm:px-6">
          <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-full bg-white text-accent shadow-sm">
            {mode === "history" ? <Search className="size-5" /> : <Sparkles className="size-5" />}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold text-primary">{mode === "history" ? "Opening your saved analysis" : "Analyzing your CV fit"}</h2>
              <span className="tabular text-xs text-ink-muted">{elapsed}s</span>
            </div>
            <p className="mt-1 text-sm text-ink-muted">
              {mode === "history" ? "Loading the vacancy, selected CV, and recommendations." : STEPS[activeStep].detail}
            </p>
          </div>
        </div>
        {mode === "analysis" && (
          <div className="grid gap-2 px-5 py-4 sm:grid-cols-5 sm:px-6">
            {STEPS.map((step, index) => (
              <div key={step.title} className="flex items-center gap-2 sm:block">
                <span className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs ${index < activeStep ? "bg-good text-white" : index === activeStep ? "bg-accent text-white" : "bg-slate-100 text-ink-muted"}`}>
                  {index < activeStep ? <Check className="size-3.5" /> : index === activeStep ? <Loader2 className="size-3.5 animate-spin" /> : index + 1}
                </span>
                <p className={`text-xs sm:mt-2 ${index === activeStep ? "font-medium text-primary" : "text-ink-muted"}`}>{step.title}</p>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="rounded-2xl bg-gradient-to-br from-primary-dark via-primary-dark to-primary p-7 shadow-hero sm:p-9">
        <div className="flex flex-col gap-9 lg:flex-row lg:items-start lg:gap-10">
          <div className="flex flex-col items-center gap-6 sm:flex-row">
            <div className="size-52 shrink-0 animate-pulse rounded-full bg-white/10" />
            <div className="flex flex-col gap-3">
              <div className="h-8 w-40 animate-pulse rounded-lg bg-white/10" />
              <div className="h-4 w-28 animate-pulse rounded bg-white/10" />
              <div className="mt-2 h-3 w-64 animate-pulse rounded bg-white/10" />
              <div className="h-3 w-52 animate-pulse rounded bg-white/10" />
            </div>
          </div>
          <div className="flex-1 lg:border-l lg:border-white/10 lg:pl-10">
            <div className="h-3 w-28 animate-pulse rounded bg-white/10" />
            <div className="mt-4 flex flex-wrap gap-2">
              {[72, 96, 64, 110, 84, 70].map((width, i) => (
                <div
                  key={i}
                  style={{ width }}
                  className="h-7 animate-pulse rounded-full bg-white/10"
                />
              ))}
            </div>
          </div>
        </div>

        <div className="mt-9 grid gap-5 border-t border-white/10 pt-7 sm:grid-cols-3 sm:gap-8">
          {[0, 1, 2].map((i) => (
            <div key={i}>
              <div className="h-4 w-20 animate-pulse rounded bg-white/10" />
              <div className="mt-2.5 h-2 w-full animate-pulse rounded-full bg-white/10" />
            </div>
          ))}
        </div>
      </section>

      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-36" />
          <Skeleton className="mt-1 h-4 w-56" />
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {[0, 1].map((i) => (
            <div key={i}>
              <Skeleton className="h-4 w-40" />
              <Skeleton className="mt-2 h-1.5 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-5 md:grid-cols-2">
        {[0, 1].map((card) => (
          <Card key={card}>
            <CardHeader>
              <Skeleton className="h-5 w-40" />
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {[68, 92, 58, 104, 76].map((width, i) => (
                <Skeleton key={i} style={{ width }} className="h-7 rounded-full" />
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-20" />
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-xl" />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
