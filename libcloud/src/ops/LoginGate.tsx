import { useState } from "react";
import type { FormEvent } from "react";
import {
  AlertCircle,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Lock,
  ShieldCheck,
  User,
} from "lucide-react";
import { OpsApiError, saveCredentials, verifyCredentials } from "./api";
import type { OpsCredentials } from "./types";

export function LoginGate({
  onAuthenticated,
}: {
  onAuthenticated: (credentials: OpsCredentials) => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (checking) return;

    const credentials = { username: username.trim(), password };
    if (!credentials.username || !credentials.password) {
      setError("Enter both the ops username and password.");
      return;
    }

    setChecking(true);
    setError(null);
    try {
      await verifyCredentials(credentials);
      saveCredentials(credentials);
      onAuthenticated(credentials);
    } catch (reason) {
      if (reason instanceof OpsApiError) {
        setError(
          reason.status === 401
            ? "Invalid ops credentials. Check the username and password."
            : reason.message
        );
      } else {
        setError("Could not reach the ops API. Check that the backend is running.");
      }
      setChecking(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-canvas px-4 py-12 text-ink">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(215,255,63,0.09),transparent_55%)]" />
      <div className="relative w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-ink">
            <TerminalGlyph />
          </span>
          <span className="text-sm font-semibold tracking-tight">LibCloud</span>
          <span className="rounded border border-line bg-surface px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted">
            ops
          </span>
        </div>

        <form
          onSubmit={submit}
          className="rounded-2xl border border-line bg-surface p-6 shadow-2xl"
        >
          <div className="mb-5 flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-accent/20 bg-accent/10 text-accent">
              <Lock className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-base font-semibold tracking-tight">Sign in to ops</h1>
              <p className="text-xs text-muted">Read-only run diagnostics.</p>
            </div>
          </div>

          <div className="space-y-3">
            <label className="block">
              <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-muted">
                Username
              </span>
              <span className="relative block">
                <User className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoComplete="username"
                  autoFocus
                  spellCheck={false}
                  className="h-10 w-full rounded-lg border border-line bg-canvas pl-9 pr-3 text-sm text-ink outline-none transition placeholder:text-muted/60 focus:border-accent"
                  placeholder="OPS_USER"
                />
              </span>
            </label>

            <label className="block">
              <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-muted">
                Password
              </span>
              <span className="relative block">
                <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  className="h-10 w-full rounded-lg border border-line bg-canvas pl-9 pr-10 text-sm text-ink outline-none transition placeholder:text-muted/60 focus:border-accent"
                  placeholder="OPS_PASSWORD"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  title={showPassword ? "Hide password" : "Show password"}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 cursor-pointer items-center justify-center rounded text-muted transition hover:text-ink"
                >
                  {showPassword ? (
                    <EyeOff className="h-3.5 w-3.5" />
                  ) : (
                    <Eye className="h-3.5 w-3.5" />
                  )}
                </button>
              </span>
            </label>
          </div>

          {error && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-400/30 bg-red-400/10 px-3 py-2 text-xs leading-5 text-red-200">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={checking}
            className="mt-4 flex h-10 w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent text-sm font-semibold text-accent-ink transition hover:brightness-110 disabled:cursor-wait disabled:opacity-70"
          >
            {checking ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Verifying
              </>
            ) : (
              <>
                <ShieldCheck className="h-4 w-4" />
                Open dashboard
              </>
            )}
          </button>

          <p className="mt-4 flex items-start gap-1.5 text-[11px] leading-4 text-muted">
            <ShieldCheck className="mt-0.5 h-3 w-3 shrink-0" />
            Sent as HTTP Basic auth. Credentials stay in this browser session and
            are cleared when you sign out.
          </p>
        </form>
      </div>
    </div>
  );
}

function TerminalGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path d="m5 7 5 5-5 5" />
      <path d="M13 17h6" />
    </svg>
  );
}
