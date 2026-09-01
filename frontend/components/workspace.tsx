"use client";

import { useCallback, useEffect, useState } from "react";

import { AnalyzePanel } from "@/components/analyze-panel";
import { AppHeader } from "@/components/app-header";
import { Results } from "@/components/results/results";
import { ResultsSkeleton } from "@/components/results/results-skeleton";
import { Sidebar } from "@/components/sidebar/sidebar";
import { ApiError, api } from "@/lib/api";
import type { AnalysisDetail, AnalysisListItem, CV, User } from "@/lib/types";

/**
 * Mirrors the backend defaults (MAX_VACANCY_CHARS, MAX_CVS_PER_USER). These are
 * only for pre-flight UI feedback -- the server stays authoritative and returns
 * a typed error either way.
 */
const MAX_VACANCY_CHARS = 15_000;
const MAX_CVS = 10;

export function Workspace({ user }: { user: User }) {
  const [cvs, setCVs] = useState<CV[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [vacancyText, setVacancyText] = useState("");
  const [result, setResult] = useState<AnalysisDetail | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [loadingMode, setLoadingMode] = useState<"analysis" | "history">("analysis");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([api.listCVs(), api.listAnalyses()])
      .then(([loadedCVs, loadedAnalyses]) => {
        if (!active) return;
        setCVs(loadedCVs);
        setAnalyses(loadedAnalyses);
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const titleFor = useCallback(
    (detail: AnalysisDetail) =>
      analyses.find((item) => item.id === detail.analysis_id)?.title ??
      detail.vacancy_text.split("\n").find((line) => line.trim())?.trim() ??
      "Vacancy analysis",
    [analyses],
  );

  async function handleAnalyze() {
    const text = vacancyText.trim();
    setLoadingMode("analysis");
    setAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      const analysis = await api.analyze(text);
      setResult({ ...analysis, vacancy_text: text });
      // Refresh history so the new run appears in the sidebar with its title.
      setAnalyses(await api.listAnalyses());
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "The analysis did not complete. Try again.",
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSelectAnalysis(id: number) {
    setError(null);
    setLoadingMode("history");
    setAnalyzing(true);
    try {
      const detail = await api.getAnalysis(id);
      setResult(detail);
      setVacancyText(detail.vacancy_text);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not load that analysis.",
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleDeleteAnalysis(id: number) {
    setAnalyses((current) => current.filter((item) => item.id !== id));
    if (result?.analysis_id === id) setResult(null);
    await api.deleteAnalysis(id).catch(() => undefined);
  }

  async function handleDeleteCV(id: number) {
    setCVs((current) => current.filter((cv) => cv.id !== id));
    await api.deleteCV(id).catch(() => undefined);
  }

  async function handleUpdateCV(id: number, label: string) {
    const updated = await api.updateCV(id, label);
    setCVs((current) => current.map((cv) => (cv.id === id ? updated : cv)));
  }

  function handleUploaded(cv: CV) {
    setCVs((current) => [cv, ...current]);
  }

  function handleNewAnalysis() {
    setResult(null);
    setVacancyText("");
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleEditVacancy() {
    // Keeps the text so it can be tweaked and re-run.
    setResult(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="min-h-screen">
      <AppHeader user={user} />

      <main className="mx-auto grid max-w-[1400px] gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Sidebar
          cvs={cvs}
          analyses={analyses}
          loading={loading}
          cvLimit={MAX_CVS}
          activeAnalysisId={result?.analysis_id ?? null}
          onUploaded={handleUploaded}
          onDeleteCV={handleDeleteCV}
          onUpdateCV={handleUpdateCV}
          onSelectAnalysis={handleSelectAnalysis}
          onDeleteAnalysis={handleDeleteAnalysis}
        />

        <div className="min-w-0">
          {analyzing ? (
            <ResultsSkeleton mode={loadingMode} />
          ) : result ? (
            <Results
              result={result}
              title={titleFor(result)}
              onNewAnalysis={handleNewAnalysis}
              onEditVacancy={handleEditVacancy}
            />
          ) : (
            <AnalyzePanel
              value={vacancyText}
              onChange={setVacancyText}
              onAnalyze={handleAnalyze}
              pending={analyzing}
              hasCVs={cvs.length > 0}
              maxChars={MAX_VACANCY_CHARS}
              error={error}
            />
          )}
        </div>
      </main>
    </div>
  );
}
