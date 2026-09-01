"use client";

import { useState } from "react";
import { Check, ClipboardCopy, Download, LoaderCircle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { GapTable } from "@/components/results/gap-table";
import { HeroCard } from "@/components/results/hero-card";
import { KeywordChips } from "@/components/results/keyword-chips";
import { RecommendedCVCard } from "@/components/results/recommended-cv-card";
import { TipsList } from "@/components/results/tips-list";
import { VacancyCard } from "@/components/results/vacancy-card";
import { analysisToMarkdown } from "@/lib/markdown";
import { ApiError, api } from "@/lib/api";
import type { AnalysisDetail } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

export function Results({
  result,
  title,
  onNewAnalysis,
  onEditVacancy,
}: {
  result: AnalysisDetail;
  title: string;
  onNewAnalysis: () => void;
  onEditVacancy: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [downloadingPDF, setDownloadingPDF] = useState(false);
  const [pdfError, setPDFError] = useState<string | null>(null);

  async function copyMarkdown() {
    try {
      await navigator.clipboard.writeText(analysisToMarkdown(result, title));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked (insecure context or denied permission) -- the button
      // simply does not confirm; nothing to recover from.
    }
  }

  async function downloadPDF() {
    setDownloadingPDF(true);
    setPDFError(null);
    try {
      const blob = await api.getAnalysisPDF(result.analysis_id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `VacancyScore-${title.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "analysis"}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setPDFError(error instanceof ApiError ? error.message : "Could not download the PDF report.");
    } finally {
      setDownloadingPDF(false);
    }
  }

  function scrollToTips() {
    document.getElementById("tips")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tracking-tight text-primary">
            {title}
          </h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Analysed {formatDateTime(result.created_at)}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Button variant="outline" size="sm" onClick={downloadPDF} disabled={downloadingPDF}>
            {downloadingPDF ? <LoaderCircle className="animate-spin" /> : <Download />}
            {downloadingPDF ? "Creating PDF" : "Download PDF"}
          </Button>
          <Button variant="outline" size="sm" onClick={copyMarkdown}>
            {copied ? <Check /> : <ClipboardCopy />}
            {copied ? "Copied" : "Copy as Markdown"}
          </Button>
          <Button variant="ghost" size="sm" onClick={onNewAnalysis}>
            <RotateCcw />
            New analysis
          </Button>
        </div>
      </div>

      {pdfError ? <p className="text-sm text-danger" role="alert">{pdfError}</p> : null}

      <HeroCard
        analysis={result.analysis}
        subScores={result.sub_scores}
        onViewSuggestions={scrollToTips}
      />

      <RecommendedCVCard
        scores={result.cv_scores}
        recommendedId={result.recommended_cv?.id ?? null}
        recommendedLabel={result.recommended_cv_label}
      />

      <KeywordChips
        matched={result.analysis.matched_keywords}
        missing={result.analysis.missing_keywords}
      />

      <GapTable gaps={result.analysis.gaps} />

      <TipsList tips={result.analysis.tips} />

      <VacancyCard text={result.vacancy_text} onEdit={onEditVacancy} />
    </div>
  );
}
