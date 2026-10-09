import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { login, registerAccount } from "../lib/accountApi";
import type { User } from "../lib/accountApi";

export function LoginPage({
  go,
  onAuthenticated,
  register = false,
}: {
  go: (path: string) => void;
  onAuthenticated: (user: User) => void;
  register?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState(false);
  const next = new URLSearchParams(window.location.search).get("next");
  const switchPage = (path: string) =>
    go(`${path}${next ? `?next=${encodeURIComponent(next)}` : ""}`);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    const fields = new FormData(event.currentTarget);
    const email = String(fields.get("email") ?? "").trim();
    const password = String(fields.get("password") ?? "");
    const name = String(fields.get("name") ?? "").trim();
    if ((register && !created && !name) || !email || !password) {
      setError("Complete all required fields.");
      return;
    }
    if (register && !created && !fields.get("terms")) {
      setError("You must agree to the Terms of Service.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (register && !created) {
        await registerAccount(name, email, password);
        setCreated(true);
      }
      const user = await login(email, password);
      onAuthenticated(user);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to sign in. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="container py-10 sm:py-16">
      <div className="mx-auto max-w-md">
        <div className="text-center">
          <span className="badge badge-red">
            <ShieldCheck size={16} /> Organizer accounts
          </span>
          <h1 className="mt-5 text-3xl font-extrabold tracking-tight sm:text-4xl">
            {register ? "Create your account" : "Sign in to PanataanPH"}
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted">
            {register
              ? "Submit fundraisers and track their review. Administrators verify organizer accounts before campaigns can be published."
              : "Manage your fundraisers or access your assigned review dashboard."}
          </p>
        </div>
        <form onSubmit={submit} noValidate className="report-card mt-8 space-y-5">
          {error && (
            <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-brand">
              {error}
            </p>
          )}
          {created && (
            <p role="status" className="rounded-xl bg-green-50 p-3 text-sm text-green-800">
              Account created. Sign in with your email and password.
            </p>
          )}
          {register && (
            <label className="block text-sm font-semibold">
              Full name
              <input
                name="name"
                required
                autoComplete="name"
                maxLength={120}
                disabled={busy || created}
                className="mt-2 w-full rounded-xl border border-line p-3"
              />
            </label>
          )}
          <label className="block text-sm font-semibold">
            Email
            <input
              name="email"
              type="email"
              required
              autoComplete="email"
              maxLength={254}
              disabled={busy}
              className="mt-2 w-full rounded-xl border border-line p-3"
            />
          </label>
          <label className="block text-sm font-semibold">
            Password
            <input
              name="password"
              type="password"
              aria-label="Password"
              required
              minLength={register ? 10 : undefined}
              maxLength={128}
              autoComplete={register ? "new-password" : "current-password"}
              disabled={busy}
              aria-describedby={register ? "password-help" : undefined}
              className="mt-2 w-full rounded-xl border border-line p-3"
            />
            {register && (
              <span id="password-help" className="mt-2 block text-xs font-normal text-muted">
                Use 10–128 characters.
              </span>
            )}
          </label>
          {register && !created && (
            <label className="flex items-start gap-3 text-sm leading-6">
              <input name="terms" type="checkbox" disabled={busy} className="mt-1" />
              <span>
                I agree to the{" "}
                <button
                  type="button"
                  className="font-semibold text-brand underline underline-offset-4"
                  onClick={() => switchPage("/terms")}
                >
                  Terms of Service
                </button>
              </span>
            </label>
          )}
          <button className="button button-primary w-full" type="submit" disabled={busy}>
            {busy ? "Signing in…" : register && !created ? "Create account" : "Sign in"}
            <ArrowRight size={16} />
          </button>
        </form>
        <p className="mt-5 text-center text-sm text-muted">
          {register ? "Already have an account? " : "Need an organizer account? "}
          <button
            className="font-semibold text-brand underline underline-offset-4"
            onClick={() => switchPage(register ? "/login" : "/register")}
          >
            {register ? "Sign in" : "Create account"}
          </button>
        </p>
      </div>
    </main>
  );
}
