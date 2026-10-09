"use client";

import Link from "next/link";
import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/logo";
import { ApiError, api } from "@/lib/api";

type Mode = "login" | "signup";

const COPY: Record<Mode, { title: string; blurb: string; cta: string }> = {
  login: {
    title: "Welcome back",
    blurb: "Sign in to your CVs and analysis history.",
    cta: "Sign in",
  },
  signup: {
    title: "Create your account",
    blurb: "Create your account securely with Supabase Auth.",
    cta: "Create account",
  },
};

export function AuthForm({ mode }: { mode: Mode }) {
  const copy = COPY[mode];

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (mode === "signup") {
      if (password.length < 8) {
        setError("Use at least 8 characters.");
        return;
      }
      if (password !== confirm) {
        setError("Those passwords do not match.");
        return;
      }
    }

    setPending(true);
    try {
      if (mode === "signup") {
        await api.signup(email, password);
      } else {
        await api.login(email, password);
      }
      // A full navigation guarantees the new session cookie is used by the
      // home-page bootstrap and cannot stall in a pending router transition.
      window.location.replace("/");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Something went wrong. Try again.",
      );
      setPending(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <Link href="/" className="mb-8 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-accent">
        <Logo />
      </Link>

      <div className="w-full max-w-sm rounded-2xl border border-hairline bg-surface p-8 shadow-card">
        <h1 className="text-2xl font-semibold tracking-tight text-primary">
          {copy.title}
        </h1>
        <p className="mt-1.5 text-sm text-ink-muted">{copy.blurb}</p>

        <form onSubmit={onSubmit} className="mt-7 flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="password">Password</Label>
              {mode === "login" ? (
                <Link
                  href="/forgot-password"
                  className="rounded text-xs font-medium text-accent outline-none hover:underline focus-visible:ring-2 focus-visible:ring-accent"
                >
                  Forgot password?
                </Link>
              ) : null}
            </div>
            <Input
              id="password"
              type="password"
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              required
              minLength={mode === "signup" ? 8 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "signup" ? "At least 8 characters" : "Your password"}
            />
          </div>

          {mode === "signup" && (
            <div className="flex flex-col gap-2">
              <Label htmlFor="confirm">Confirm password</Label>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Type it again"
              />
            </div>
          )}

          {error && (
            <p
              role="alert"
              className="rounded-xl bg-danger-soft px-3.5 py-2.5 text-sm text-danger"
            >
              {error}
            </p>
          )}

          <Button type="submit" size="lg" variant="cta" disabled={pending} className="mt-1 w-full">
            {pending && <Loader2 className="animate-spin" />}
            {pending ? "One moment" : copy.cta}
          </Button>
        </form>
      </div>

      <p className="mt-6 text-sm text-ink-muted">
        {mode === "login" ? "New here? " : "Already have an account? "}
        <Link
          href={mode === "login" ? "/signup" : "/login"}
          className="rounded font-medium text-accent underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-accent"
        >
          {mode === "login" ? "Create an account" : "Sign in"}
        </Link>
      </p>
    </main>
  );
}
