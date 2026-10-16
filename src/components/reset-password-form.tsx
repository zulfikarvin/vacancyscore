"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api";

type RecoveryState = "checking" | "ready" | "invalid" | "complete";

export function ResetPasswordForm() {
  const [state, setState] = useState<RecoveryState>("checking");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recoveryPreparation = useRef<Promise<void> | null>(null);

  useEffect(() => {
    let active = true;

    async function prepareRecovery() {
      const url = new URL(window.location.href);
      const fragment = new URLSearchParams(url.hash.slice(1));
      const accessToken = fragment.get("access_token");
      const refreshToken = fragment.get("refresh_token");
      const parsedExpiry = Number(fragment.get("expires_in") || 3600);
      const expiresIn = Number.isFinite(parsedExpiry) && parsedExpiry > 0 ? parsedExpiry : 3600;
      const linkError = fragment.get("error_description") || url.searchParams.get("error_description");

      // Remove credentials from the address bar as soon as they are captured.
      if (url.hash || url.search) {
        window.history.replaceState({}, "", window.location.pathname);
      }

      if (linkError) throw new Error(linkError);
      if (accessToken && refreshToken) {
        await api.acceptRecoverySession(accessToken, refreshToken, expiresIn);
      } else {
        // Supports refreshing this page after the link session was accepted.
        await api.me();
      }
    }

    // Strict Mode replays effects. Reuse the in-flight exchange after the
    // credentials have been removed from the URL, rather than racing api.me().
    recoveryPreparation.current ??= prepareRecovery();
    void recoveryPreparation.current.then(
      () => {
        if (active) setState("ready");
      },
      (err: unknown) => {
        if (!active) return;
        const missingSession = err instanceof ApiError && err.code === "unauthorized";
        setError(
          missingSession
            ? "No recovery session was found. Open the newest reset link from your email."
            : err instanceof Error ? err.message : "Could not verify your recovery link. Please try again.",
        );
        setState("invalid");
      },
    );
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Use at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Those passwords do not match.");
      return;
    }

    setPending(true);
    try {
      await api.updatePassword(password);
      setState("complete");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update your password.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <Link href="/" className="mb-8 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-accent">
        <Logo />
      </Link>
      <div className="w-full max-w-sm rounded-2xl border border-hairline bg-surface p-8 shadow-card">
        {state === "checking" ? (
          <div role="status" className="flex flex-col items-center py-8 text-center">
            <Loader2 className="size-8 animate-spin text-accent" />
            <h1 className="mt-4 text-xl font-semibold text-primary">Checking your recovery link</h1>
          </div>
        ) : null}

        {state === "invalid" ? (
          <div className="text-center">
            <h1 className="text-2xl font-semibold text-primary">Could not open password reset</h1>
            <p className="mt-2 text-sm leading-6 text-ink-muted">
              {error || "Request a new password reset link to continue."}
            </p>
            <Button asChild variant="cta" className="mt-6 w-full">
              <Link href="/forgot-password">Request a new link</Link>
            </Button>
          </div>
        ) : null}

        {state === "ready" ? (
          <>
            <h1 className="text-2xl font-semibold tracking-tight text-primary">Choose a new password</h1>
            <p className="mt-1.5 text-sm text-ink-muted">Use at least 8 characters.</p>
            <form onSubmit={onSubmit} className="mt-7 flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="password">New password</Label>
                <PasswordInput id="password" autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="confirm">Confirm new password</Label>
                <PasswordInput id="confirm" autoComplete="new-password" minLength={8} required value={confirm} onChange={(event) => setConfirm(event.target.value)} />
              </div>
              {error ? <p role="alert" className="rounded-xl bg-danger-soft px-3.5 py-2.5 text-sm text-danger">{error}</p> : null}
              <Button type="submit" size="lg" variant="cta" disabled={pending} className="w-full">
                {pending ? <Loader2 className="animate-spin" /> : null}
                {pending ? "Updating password" : "Update password"}
              </Button>
            </form>
          </>
        ) : null}

        {state === "complete" ? (
          <div role="status" className="text-center">
            <CheckCircle2 className="mx-auto size-10 text-good" />
            <h1 className="mt-4 text-2xl font-semibold text-primary">Password updated</h1>
            <p className="mt-2 text-sm text-ink-muted">You can now sign in with your new password.</p>
            <Button asChild variant="cta" className="mt-6 w-full">
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        ) : null}
      </div>
    </main>
  );
}
