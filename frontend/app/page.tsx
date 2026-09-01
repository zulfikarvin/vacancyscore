"use client";

import { useEffect, useState } from "react";

import { Workspace } from "@/components/workspace";
import { Logo } from "@/components/logo";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export default function HomePage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    let active = true;
    api
      .me()
      .then((me) => {
        if (active) setUser(me);
      })
      .catch(() => {
        if (active) window.location.replace("/login");
      });
    return () => {
      active = false;
    };
  }, []);

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center" role="status" aria-live="polite">
        <div className="flex flex-col items-center">
          <div className="relative flex h-28 w-72 items-center justify-center">
            <span className="absolute size-20 animate-ping rounded-full border border-violet-200 opacity-50 motion-reduce:animate-none" />
            <span
              className="absolute size-14 animate-ping rounded-full bg-violet-100 opacity-70 motion-reduce:animate-none"
              style={{ animationDelay: "450ms" }}
            />
            <span className="relative rounded-2xl bg-white/80 px-5 py-3 shadow-card backdrop-blur-sm">
              <Logo className="animate-pulse motion-reduce:animate-none" />
            </span>
          </div>
          <p className="mt-2 animate-pulse text-sm text-ink-muted motion-reduce:animate-none">
            Loading your workspace…
          </p>
        </div>
      </div>
    );
  }

  return <Workspace user={user} />;
}
