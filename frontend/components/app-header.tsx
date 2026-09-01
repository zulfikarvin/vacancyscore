"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export function AppHeader({ user }: { user: User }) {
  const router = useRouter();

  async function logout() {
    await api.logout().catch(() => undefined);
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-canvas/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between px-4 sm:px-6">
        <Logo />
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-ink-muted sm:inline">
            {user.email}
          </span>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut />
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
