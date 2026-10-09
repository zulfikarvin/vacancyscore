"use client";

import { Check, FileText, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import type { CV } from "@/lib/types";
import { cn } from "@/lib/utils";

const MIN_CHARS = 40;

export function AnalyzePanel({
  value,
  onChange,
  onAnalyze,
  pending,
  cvs,
  selectedCVIds,
  onSelectedCVIdsChange,
  maxChars,
  error,
}: {
  value: string;
  onChange: (value: string) => void;
  onAnalyze: () => void;
  pending: boolean;
  cvs: CV[];
  selectedCVIds: number[];
  onSelectedCVIdsChange: (ids: number[]) => void;
  maxChars: number;
  error: string | null;
}) {
  const length = value.trim().length;
  const tooShort = length > 0 && length < MIN_CHARS;
  const tooLong = length > maxChars;
  const hasCVs = cvs.length > 0;
  const hasSelection = selectedCVIds.length > 0;
  const canAnalyze = hasSelection && !pending && length >= MIN_CHARS && !tooLong;

  function toggleCV(id: number) {
    onSelectedCVIdsChange(
      selectedCVIds.includes(id)
        ? selectedCVIds.filter((cvId) => cvId !== id)
        : [...selectedCVIds, id],
    );
  }

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

      <Card className="overflow-hidden shadow-none">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-primary">Sources</h2>
            <p className="mt-0.5 text-xs text-ink-muted">
              {selectedCVIds.length} of {cvs.length} CVs selected
            </p>
          </div>
          {cvs.length > 0 && (
            <button
              type="button"
              disabled={pending}
              onClick={() =>
                onSelectedCVIdsChange(
                  selectedCVIds.length === cvs.length ? [] : cvs.map((cv) => cv.id),
                )
              }
              className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"
            >
              {selectedCVIds.length === cvs.length ? "Clear" : "Select all"}
            </button>
          )}
        </div>

        {cvs.length > 0 ? (
          <div className="scroll-slim grid max-h-52 gap-1 overflow-y-auto p-2 sm:grid-cols-2">
            {cvs.map((cv) => {
              const selected = selectedCVIds.includes(cv.id);
              return (
                <label
                  key={cv.id}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors",
                    selected
                      ? "border-accent/40 bg-violet-100"
                      : "border-transparent hover:bg-canvas",
                    pending && "pointer-events-none opacity-60",
                  )}
                >
                  <input type="checkbox" className="sr-only" checked={selected} disabled={pending} onChange={() => toggleCV(cv.id)} />
                  <span aria-hidden="true" className={cn("flex size-5 shrink-0 items-center justify-center rounded-md border", selected ? "border-accent bg-accent text-white" : "border-hairline bg-surface")}>{selected && <Check className="size-3.5" strokeWidth={3} />}</span>
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-surface text-accent shadow-sm"><FileText className="size-4" /></span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-ink">{cv.label}</span>
                    <span className="block truncate text-xs text-ink-muted">{cv.filename}</span>
                  </span>
                </label>
              );
            })}
          </div>
        ) : (
          <p className="px-4 py-5 text-sm text-ink-muted">Upload a CV to add your first source.</p>
        )}
      </Card>

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
          ) : !hasSelection ? (
            <span className="text-warn">Select at least one CV to analyze.</span>
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
