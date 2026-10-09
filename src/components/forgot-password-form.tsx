"use client";

import Link from "next/link";
import { useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api } from "@/lib/api";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send the reset email. Try again.");
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
        {sent ? (
          <div role="status" className="text-center">
            <CheckCircle2 className="mx-auto size-10 text-good" />
            <h1 className="mt-4 text-2xl font-semibold tracking-tight text-primary">Check your email</h1>
            <p className="mt-2 text-sm leading-6 text-ink-muted">
              If an account exists for <span className="font-medium text-ink">{email}</span>,
              Supabase has sent a password reset link. Check your spam folder too.
            </p>
            <Button variant="outline" className="mt-6 w-full" onClick={() => setSent(false)}>
              Send another link
            </Button>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-semibold tracking-tight text-primary">Reset your password</h1>
            <p className="mt-1.5 text-sm text-ink-muted">
              Enter your account email and we will send you a secure recovery link.
            </p>
            <form onSubmit={onSubmit} className="mt-7 flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                />
              </div>
              {error ? (
                <p role="alert" className="rounded-xl bg-danger-soft px-3.5 py-2.5 text-sm text-danger">
                  {error}
                </p>
              ) : null}
              <Button type="submit" size="lg" variant="cta" disabled={pending} className="w-full">
                {pending ? <Loader2 className="animate-spin" /> : null}
                {pending ? "Sending link" : "Send reset link"}
              </Button>
            </form>
          </>
        )}
      </div>

      <Link href="/login" className="mt-6 rounded text-sm font-medium text-accent outline-none hover:underline focus-visible:ring-2 focus-visible:ring-accent">
        Back to sign in
      </Link>
    </main>
  );
}
