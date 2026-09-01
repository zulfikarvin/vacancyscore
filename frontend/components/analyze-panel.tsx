"use client";

import { Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const MIN_CHARS = 40;

export function AnalyzePanel({
  value,
  onChange,
  onAnalyze,
  pending,
  hasCVs,
  maxChars,
  error,
}: {
  value: string;
  onChange: (value: string) => void;
  onAnalyze: () => void;
  pending: boolean;
  hasCVs: boolean;
  maxChars: number;
  error: string | null;
}) {
  const length = value.trim().length;
  const tooShort = length > 0 && length < MIN_CHARS;
  const tooLong = length > maxChars;
  const canAnalyze = hasCVs && !pending && length >= MIN_CHARS && !tooLong;

  return (
    <section className="flex flex-col gap-4">
      {/* The button sits above the textarea: the action comes first. */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-primary">
            Score a vacancy
          </h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Paste the full job description. We pick your best CV and grade it
            honestly.
          </p>
        </div>

        <Button
          size="lg"
          variant="cta"
          onClick={onAnalyze}
          disabled={!canAnalyze}
          className="min-w-40"
        >
          {pending ? <Loader2 className="animate-spin" /> : <Sparkles />}
          {pending ? "Analyzing" : "Analyze"}
        </Button>
      </div>

      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={pending}
        rows={16}
        placeholder={
          "Paste the vacancy here — title, responsibilities, requirements, the lot.\n\nThe more of the original posting you include, the sharper the gap analysis."
        }
        className="min-h-[22rem]"
      />

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="text-ink-muted">
          {!hasCVs ? (
            <span className="text-warn">
              Upload a CV first — VacancyScore needs something to score.
            </span>
          ) : tooShort ? (
            <span>At least {MIN_CHARS} characters, please.</span>
          ) : (
            <span />
          )}
        </div>
        <span
          className={cn(
            "tabular",
            tooLong ? "font-medium text-danger" : "text-ink-muted",
          )}
        >
          {length.toLocaleString()} / {maxChars.toLocaleString()}
        </span>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger"
        >
          {error}
        </p>
      )}
    </section>
  );
}
