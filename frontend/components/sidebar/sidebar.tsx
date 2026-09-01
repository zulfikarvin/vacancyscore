"use client";

import { FileText, History, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CVUploadDialog } from "@/components/sidebar/cv-upload-dialog";
import { CVThumbnail, CVViewerDialog } from "@/components/sidebar/cv-viewer-dialog";
import { CVRenameDialog } from "@/components/sidebar/cv-rename-dialog";
import type { AnalysisListItem, CV } from "@/lib/types";
import { cn, formatDate, scoreBand, scoreChip } from "@/lib/utils";

interface SidebarProps {
  cvs: CV[];
  analyses: AnalysisListItem[];
  loading: boolean;
  cvLimit: number;
  activeAnalysisId: number | null;
  onUploaded: (cv: CV) => void;
  onDeleteCV: (id: number) => void;
  onUpdateCV: (id: number, label: string) => Promise<void>;
  onSelectAnalysis: (id: number) => void;
  onDeleteAnalysis: (id: number) => void;
}

export function Sidebar({
  cvs,
  analyses,
  loading,
  cvLimit,
  activeAnalysisId,
  onUploaded,
  onDeleteCV,
  onUpdateCV,
  onSelectAnalysis,
  onDeleteAnalysis,
}: SidebarProps) {
  return (
    <aside className="lg:sticky lg:top-24 lg:h-[calc(100vh-8rem)]">
      <Tabs defaultValue="cvs" className="flex h-full flex-col gap-4">
        <TabsList>
          <TabsTrigger value="cvs">My CVs</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="cvs" className="flex min-h-0 flex-1 flex-col gap-3">
          <CVUploadDialog onUploaded={onUploaded} disabled={cvs.length >= cvLimit} />
          {cvs.length >= cvLimit && (
            <p className="text-xs text-ink-muted">
              You have reached the limit of {cvLimit} CVs. Delete one to add another.
            </p>
          )}

          <div className="scroll-slim -mr-1 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
            {loading ? (
              <SidebarSkeleton rows={3} />
            ) : cvs.length === 0 ? (
              <EmptyState
                icon={<FileText className="size-5" />}
                title="No CVs yet"
                body="Upload your first CV to get started. Add a few versions and VacancyScore will pick the best one per vacancy."
              />
            ) : (
              cvs.map((cv) => (
                <div
                  key={cv.id}
                  className="group rounded-2xl border border-hairline bg-surface p-3.5 shadow-card transition-colors hover:border-accent-light"
                >
                  <div className="flex gap-3">
                  <CVThumbnail cv={cv} />
                  <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium leading-snug text-ink">
                      {cv.label}
                    </p>
                    <div className="flex shrink-0">
                    <CVRenameDialog cv={cv} onRename={onUpdateCV} />
                    <Button
                      variant="danger"
                      size="icon"
                      aria-label={`Delete ${cv.label}`}
                      className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
                      onClick={() => onDeleteCV(cv.id)}
                    >
                      <Trash2 />
                    </Button>
                    </div>
                  </div>
                  <p className="mt-1 truncate text-xs text-ink-muted" title={cv.filename}>
                    {cv.filename}
                  </p>
                  <p className="mt-2 text-xs text-ink-muted">
                    {formatDate(cv.created_at)} · {cv.char_count.toLocaleString()} chars
                  </p>
                  <div className="mt-1.5">
                    <CVViewerDialog cv={cv} />
                  </div>
                  </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="history" className="flex min-h-0 flex-1 flex-col">
          <div className="scroll-slim -mr-1 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
            {loading ? (
              <SidebarSkeleton rows={4} />
            ) : analyses.length === 0 ? (
              <EmptyState
                icon={<History className="size-5" />}
                title="No analyses yet"
                body="Paste a vacancy and hit Analyze. Every result is saved here so you can come back to it."
              />
            ) : (
              analyses.map((item) => {
                const band = scoreBand(item.fit_score);
                const active = item.id === activeAnalysisId;
                return (
                  <div
                    key={item.id}
                    className={cn(
                      "group relative rounded-2xl border bg-surface shadow-card transition-colors",
                      active
                        ? "border-accent ring-1 ring-accent/20"
                        : "border-hairline hover:border-accent-light",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelectAnalysis(item.id)}
                      className="w-full rounded-2xl p-3.5 pr-10 text-left outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="line-clamp-2 text-sm font-medium leading-snug text-ink">
                          {item.title}
                        </p>
                        <Badge className={cn("tabular shrink-0", scoreChip[band])}>
                          {item.fit_score}
                        </Badge>
                      </div>
                      <p className="mt-2 text-xs text-ink-muted">
                        {formatDate(item.created_at)} · {item.recommended_cv_label}
                      </p>
                    </button>
                    <Button
                      variant="danger"
                      size="icon"
                      aria-label={`Delete analysis ${item.title}`}
                      className="absolute right-2.5 top-9 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
                      onClick={() => onDeleteAnalysis(item.id)}
                    >
                      <Trash2 />
                    </Button>
                  </div>
                );
              })
            )}
          </div>
        </TabsContent>
      </Tabs>
    </aside>
  );
}

function SidebarSkeleton({ rows }: { rows: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="rounded-2xl border border-hairline bg-surface p-3.5">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="mt-2.5 h-3 w-1/2" />
          <Skeleton className="mt-2 h-3 w-2/5" />
        </div>
      ))}
    </>
  );
}

function EmptyState({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-hairline bg-surface/60 p-6 text-center">
      <span className="mx-auto flex size-10 items-center justify-center rounded-full bg-violet-100 text-accent">
        {icon}
      </span>
      <p className="mt-3 text-sm font-medium text-primary">{title}</p>
      <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">{body}</p>
    </div>
  );
}
