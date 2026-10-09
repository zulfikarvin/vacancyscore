"use client";

import { useEffect, useState } from "react";
import { Download, Eye, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import type { CV } from "@/lib/types";

export function CVViewerDialog({ cv }: { cv: CV }) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState<string | null>(null);
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    let active = true;
    let objectUrl: string | null = null;
    setLoading(true);
    setError("");
    api.getCVFile(cv.id)
      .then(async (blob) => {
        if (!active) return;
        if (blob.type.includes("pdf")) {
          objectUrl = URL.createObjectURL(blob);
          setUrl(objectUrl);
          setText(null);
        } else {
          setText(await blob.text());
          setUrl(null);
        }
      })
      .catch((reason: Error) => active && setError(reason.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setUrl(null);
      setText(null);
    };
  }, [open, cv.id]);

  async function download() {
    try {
      const blob = await api.getCVFile(cv.id, true);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = blob.type.includes("text/plain")
        ? `${cv.filename.replace(/\.[^.]+$/, "")}.txt`
        : cv.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not download this CV.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 px-2 text-xs">
          <Eye className="size-3.5" /> See my CV
        </Button>
      </DialogTrigger>
      <DialogContent className="flex h-[90vh] max-w-4xl flex-col overflow-hidden p-0">
        <DialogHeader className="mb-0 border-b border-hairline px-6 py-4 pr-14">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <DialogTitle className="truncate">{cv.label}</DialogTitle>
              <DialogDescription className="truncate">{cv.filename}</DialogDescription>
            </div>
            <Button onClick={download} size="sm" className="shrink-0">
              <Download className="size-4" /> Download
            </Button>
          </div>
        </DialogHeader>
        <div className="scroll-slim flex min-h-0 flex-1 items-stretch justify-center overflow-auto bg-slate-100 p-4 sm:p-6">
          {loading && <Loader2 className="m-auto size-6 animate-spin text-accent" />}
          {error && <p className="m-auto text-sm text-red-600">{error}</p>}
          {url && (
            <iframe
              src={url}
              title={cv.label}
              className="h-full min-h-[600px] w-full rounded-lg bg-white shadow-card"
            />
          )}
          {text !== null && (
            <article className="min-h-full w-full max-w-3xl whitespace-pre-wrap rounded-lg bg-white p-8 text-sm leading-7 text-ink shadow-card sm:p-12">
              {text}
            </article>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function CVThumbnail({ cv }: { cv: CV }) {
  const [url, setUrl] = useState<string | null>(null);
  const [text, setText] = useState("");

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    api.getCVFile(cv.id).then(async (blob) => {
      if (!active) return;
      if (blob.type.includes("pdf")) {
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } else {
        setText(await blob.text());
      }
    }).catch(() => undefined);
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [cv.id]);

  return (
    <div className="pointer-events-none relative h-24 w-20 shrink-0 overflow-hidden rounded-md border border-hairline bg-white shadow-sm">
      <span className="absolute left-0 top-0 z-10 h-full w-1 bg-gradient-to-b from-blue-500 to-fuchsia-500" />
      {url ? (
        <iframe
          src={`${url}#toolbar=0&navpanes=0&scrollbar=0`}
          title={`Preview of ${cv.label}`}
          tabIndex={-1}
          className="h-[300px] w-[250px] origin-top-left scale-[0.32] border-0 bg-white"
        />
      ) : text ? (
        <p className="h-full overflow-hidden whitespace-pre-wrap p-2 pl-3 text-[3.5px] leading-[5px] text-slate-700">
          {text.slice(0, 1200)}
        </p>
      ) : (
        <div className="m-auto mt-9 h-4 w-4 animate-pulse rounded bg-slate-200" />
      )}
    </div>
  );
}
