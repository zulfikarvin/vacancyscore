"use client";

import { useRef, useState } from "react";
import { FileText, Loader2, Plus, UploadCloud, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api";
import type { CV } from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

export function CVUploadDialog({
  onUploaded,
  disabled,
}: {
  onUploaded: (cv: CV) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function reset() {
    setLabel("");
    setFile(null);
    setError(null);
    setPending(false);
    if (fileInput.current) fileInput.current.value = "";
  }

  function chooseFile(next: File | null) {
    if (!next) return;
    const extension = next.name.split(".").pop()?.toLowerCase();
    if (extension !== "pdf" && extension !== "docx") {
      setError("Drop a PDF or DOCX file.");
      return;
    }
    if (next.size > MAX_FILE_BYTES) {
      setError("That file is larger than 5MB.");
      return;
    }
    setFile(next);
    setError(null);
    if (!label.trim()) setLabel(next.name.replace(/\.(pdf|docx)$/i, ""));
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Choose a PDF or DOCX file.");
      return;
    }
    setError(null);
    setPending(true);
    try {
      const cv = await api.uploadCV(label.trim() || file.name, file);
      onUploaded(cv);
      setOpen(false);
      reset();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "That upload did not go through.",
      );
      setPending(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>
        <div
          role="button"
          tabIndex={disabled ? -1 : 0}
          aria-disabled={disabled}
          aria-label="Add a CV by dragging and dropping or browsing"
          onKeyDown={(event) => {
            if (!disabled && (event.key === "Enter" || event.key === " ")) setOpen(true);
          }}
          onDragEnter={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }}
          onDragOver={(event) => { event.preventDefault(); if (!disabled) { event.dataTransfer.dropEffect = "copy"; setDragging(true); } }}
          onDragLeave={(event) => {
            event.preventDefault();
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);
          }}
          onDrop={(event) => {
            event.preventDefault();
            if (disabled) return;
            setDragging(false);
            chooseFile(event.dataTransfer.files?.[0] ?? null);
            setOpen(true);
          }}
          className={cn(
            "group/drop flex min-h-24 w-full cursor-pointer items-center gap-3 rounded-2xl border-2 border-dashed px-4 py-3 text-left outline-none transition-all",
            "focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
            dragging
              ? "scale-[1.01] border-accent bg-violet-100 shadow-card"
              : "border-violet-200 bg-violet-100/35 hover:border-accent hover:bg-violet-100",
            disabled && "pointer-events-none cursor-not-allowed opacity-50",
          )}
        >
          <span className={cn("flex size-11 shrink-0 items-center justify-center rounded-xl bg-white text-accent shadow-sm transition-transform", dragging && "scale-110")}>
            {dragging ? <UploadCloud className="size-5" /> : <Plus className="size-5" />}
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-medium text-primary">
              {dragging ? "Drop your CV here" : "Drag & drop your CV"}
            </span>
            <span className="mt-0.5 block text-xs text-ink-muted">
              or click to browse · PDF or DOCX
            </span>
          </span>
        </div>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload a CV</DialogTitle>
          <DialogDescription>
            PDF or DOCX, up to 5MB. Give it a label you will recognise later,
            like “Backend, quantified” or “Data role”.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="cv-label">Label</Label>
            <Input
              id="cv-label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Backend engineer, v3"
              maxLength={120}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="cv-file">File</Label>
            <input
              id="cv-file"
              ref={fileInput}
              type="file"
              accept=".pdf,.docx"
              className="sr-only"
              onChange={(e) => chooseFile(e.target.files?.[0] ?? null)}
            />
            <div
              role="button"
              tabIndex={0}
              aria-label="Drop a CV here or choose a file"
              onClick={() => !pending && fileInput.current?.click()}
              onKeyDown={(event) => {
                if ((event.key === "Enter" || event.key === " ") && !pending) fileInput.current?.click();
              }}
              onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
              onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; setDragging(true); }}
              onDragLeave={(event) => {
                event.preventDefault();
                if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);
              }}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                chooseFile(event.dataTransfer.files?.[0] ?? null);
              }}
              className={cn(
                "flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-5 py-6 text-center outline-none transition-all",
                "focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
                dragging ? "scale-[1.01] border-accent bg-violet-100 shadow-card" : "border-hairline bg-canvas hover:border-accent-light hover:bg-violet-100/50",
                pending && "pointer-events-none opacity-60",
              )}
            >
              {file ? (
                <>
                  <span className="flex size-11 items-center justify-center rounded-xl bg-violet-100 text-accent"><FileText className="size-5" /></span>
                  <p className="mt-3 max-w-full truncate text-sm font-medium text-primary">{file.name}</p>
                  <p className="mt-1 text-xs text-ink-muted">{(file.size / 1024).toFixed(0)} KB · Ready to upload</p>
                  <button
                    type="button"
                    className="mt-3 inline-flex items-center gap-1 text-xs text-danger hover:underline"
                    onClick={(event) => { event.stopPropagation(); setFile(null); if (fileInput.current) fileInput.current.value = ""; }}
                  ><X className="size-3.5" /> Remove</button>
                </>
              ) : (
                <>
                  <span className={cn("flex size-12 items-center justify-center rounded-full bg-violet-100 text-accent transition-transform", dragging && "scale-110")}><UploadCloud className="size-6" /></span>
                  <p className="mt-3 text-sm font-medium text-primary">{dragging ? "Drop your CV here" : "Drag and drop your CV"}</p>
                  <p className="mt-1 text-xs text-ink-muted">or click to browse · PDF or DOCX · up to 5MB</p>
                </>
              )}
            </div>
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-xl bg-danger-soft px-3.5 py-2.5 text-sm text-danger"
            >
              {error}
            </p>
          )}

          <Button type="submit" variant="cta" disabled={pending} className="mt-1">
            {pending ? <Loader2 className="animate-spin" /> : <UploadCloud />}
            {pending ? "Reading your CV" : "Upload"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
