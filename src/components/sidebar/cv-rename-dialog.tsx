"use client";

import { useEffect, useState } from "react";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { CV } from "@/lib/types";

export function CVRenameDialog({ cv, onRename }: { cv: CV; onRename: (id: number, label: string) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState(cv.label);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => setLabel(cv.label), [cv.label]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const next = label.trim();
    if (!next || next === cv.label) { setOpen(false); return; }
    setPending(true); setError("");
    try { await onRename(cv.id, next); setOpen(false); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not rename this CV."); }
    finally { setPending(false); }
  }

  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild>
      <Button variant="ghost" size="icon" aria-label={`Rename ${cv.label}`} className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"><Pencil /></Button>
    </DialogTrigger>
    <DialogContent>
      <DialogHeader><DialogTitle>Rename CV</DialogTitle><DialogDescription>Change the name shown in your CV list. The uploaded filename stays unchanged.</DialogDescription></DialogHeader>
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-2"><Label htmlFor={`cv-name-${cv.id}`}>CV name</Label><Input id={`cv-name-${cv.id}`} value={label} onChange={(e) => setLabel(e.target.value)} maxLength={120} autoFocus /></div>
        {error && <p className="text-sm text-danger">{error}</p>}
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={pending || !label.trim()}>{pending ? "Saving" : "Save changes"}</Button></div>
      </form>
    </DialogContent>
  </Dialog>;
}
