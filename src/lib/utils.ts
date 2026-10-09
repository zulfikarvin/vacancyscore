import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { Severity } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Score bands, used for the fit label, the sub-score bars and history rows.
 * Below 50 reads as a warning, 50-74 as "worth tailoring", 75+ as ready.
 */
export type ScoreBand = "weak" | "fair" | "strong";

export function scoreBand(score: number): ScoreBand {
  if (score >= 75) return "strong";
  if (score >= 50) return "fair";
  return "weak";
}

export const scoreText: Record<ScoreBand, string> = {
  weak: "text-danger",
  fair: "text-warn",
  strong: "text-good",
};

export const scoreBg: Record<ScoreBand, string> = {
  weak: "bg-danger",
  fair: "bg-warn",
  strong: "bg-good",
};

export const scoreChip: Record<ScoreBand, string> = {
  weak: "bg-danger-soft text-danger",
  fair: "bg-warn-soft text-warn",
  strong: "bg-good-soft text-good",
};

/** On the dark hero card the soft tints have no contrast, so tint the ink instead. */
export const scoreOnDark: Record<ScoreBand, string> = {
  weak: "text-[#ff9aa8]",
  fair: "text-[#f0be7a]",
  strong: "text-[#8fdcb0]",
};

export const severityRank: Record<Severity, number> = {
  high: 3,
  medium: 2,
  low: 1,
};

export const severityChip: Record<Severity, string> = {
  high: "bg-danger-soft text-danger ring-danger/15",
  medium: "bg-warn-soft text-warn ring-warn/15",
  low: "bg-good-soft text-good ring-good/15",
};

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
