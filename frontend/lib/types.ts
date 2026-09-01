/**
 * Mirrors backend/app/schemas.py exactly.
 *
 * If you change a Pydantic model there, change it here in the same commit --
 * these two files are the contract between the two deploys.
 */

export type Severity = "low" | "medium" | "high";

export interface MatchedKeyword {
  keyword: string;
  /** CV section where the evidence was found: "Projects", "Skills", ... */
  location: string;
}

export interface GapRow {
  requirement: string;
  /** "" when nothing in the CV supports the requirement. */
  cv_evidence: string;
  severity: Severity;
  suggested_fix: string;
}

export interface VacancyAnalysis {
  fit_score: number;
  fit_label: string;
  summary: string;
  matched_keywords: MatchedKeyword[];
  missing_keywords: string[];
  gaps: GapRow[];
  tips: string[];
}

export interface SubScores {
  profile: number;
  skills: number;
  summary: number;
}

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface CV {
  id: number;
  label: string;
  filename: string;
  char_count: number;
  created_at: string;
}

export interface CVScore {
  cv_id: number;
  label: string;
  /** 0-100. */
  similarity: number;
  strength_score?: number;
  selection_score?: number;
}

export interface AnalysisResult {
  analysis_id: number;
  /** null when the winning CV was deleted after the analysis was saved. */
  recommended_cv: CV | null;
  recommended_cv_label: string;
  cv_scores: CVScore[];
  analysis: VacancyAnalysis;
  sub_scores: SubScores;
  created_at: string;
}

export interface AnalysisDetail extends AnalysisResult {
  vacancy_text: string;
}

export interface AnalysisListItem {
  id: number;
  title: string;
  fit_score: number;
  fit_label: string;
  recommended_cv_label: string;
  created_at: string;
}

export type ErrorCode =
  | "invalid_request"
  | "unauthorized"
  | "not_found"
  | "email_taken"
  | "invalid_credentials"
  | "no_cvs"
  | "cv_limit_reached"
  | "vacancy_too_long"
  | "file_too_large"
  | "unsupported_file_type"
  | "unreadable_file"
  | "rate_limited"
  | "llm_unavailable";

export interface ErrorResponse {
  code: ErrorCode;
  message: string;
  detail?: Record<string, string | number> | null;
}
