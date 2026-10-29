import type { AnchorHTMLAttributes, ReactNode } from "react";
import {
  AlertTriangle,
  Loader2,
  RefreshCw,
  Search,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { DETAIL_LABELS } from "./format";
import type { OpsDetailKind } from "./types";
import { navigate } from "./navigation";

export const surfaceClass = "rounded-xl border border-line bg-surface";
export const inputClass =
  "h-9 rounded-lg border border-line bg-canvas px-3 text-sm text-ink placeholder:text-muted/60 outline-none transition focus:border-accent";

type OpsLinkProps = AnchorHTMLAttributes<HTMLAnchorElement>;

export function OpsLink({ href, onClick, children, ...rest }: OpsLinkProps) {
  return (
    <a
      href={href}
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented || !href) return;
        if (
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        ) {
          return;
        }
        event.preventDefault();
        navigate(href);
      }}
      {...rest}
    >
      {children}
    </a>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">
            {eyebrow}
          </p>
        )}
        <h1 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
          {title}
        </h1>
        {description && (
          <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      )}
    </div>
  );
}

export function IconButton({
  label,
  icon: Icon,
  onClick,
  disabled,
  spinning,
}: {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
  disabled?: boolean;
  spinning?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg border border-line bg-surface text-muted transition hover:border-accent/60 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
    >
      <Icon className={`h-4 w-4 ${spinning ? "animate-spin" : ""}`} />
    </button>
  );
}

export function Metric({
  label,
  value,
  hint,
  icon: Icon,
  tone = "accent",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: LucideIcon;
  tone?: "accent" | "danger" | "muted";
}) {
  const toneClass =
    tone === "danger"
      ? "text-red-300"
      : tone === "muted"
        ? "text-muted"
        : "text-accent";

  return (
    <div className={`${surfaceClass} p-4`}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">
          {label}
        </p>
        {Icon && <Icon className={`h-3.5 w-3.5 shrink-0 ${toneClass}`} />}
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-ink tabular-nums">
        {value}
      </p>
      {hint && <p className="mt-1 text-[11px] leading-4 text-muted">{hint}</p>}
    </div>
  );
}

export function Panel({
  title,
  description,
  actions,
  children,
  className = "",
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`${surfaceClass} ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
            {description && (
              <p className="mt-0.5 text-[11px] text-muted">{description}</p>
            )}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function ProgressBar({
  value,
  tone = "accent",
}: {
  value: number;
  tone?: "accent" | "danger";
}) {
  const width = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-canvas">
      <div
        className={`h-full rounded-full ${tone === "danger" ? "bg-red-400" : "bg-accent"}`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
      <Loader2 className="h-4 w-4 animate-spin text-accent" />
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className={`${surfaceClass} flex flex-col items-center gap-3 px-6 py-14 text-center`}>
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-red-400/10 text-red-300">
        <AlertTriangle className="h-5 w-5" />
      </span>
      <div>
        <p className="text-sm font-semibold text-ink">Could not load ops data</p>
        <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-muted">{message}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg border border-line bg-canvas px-3 text-xs font-medium text-ink transition hover:border-accent/60"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  icon: Icon = AlertTriangle,
}: {
  title: string;
  description?: string;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-14 text-center">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-canvas text-muted">
        <Icon className="h-4 w-4" />
      </span>
      <p className="text-sm font-medium text-ink">{title}</p>
      {description && <p className="max-w-md text-xs text-muted">{description}</p>}
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  completed: "border-accent/30 bg-accent/10 text-accent",
  failed: "border-red-400/30 bg-red-400/10 text-red-300",
  running: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  cancelled: "border-line bg-canvas text-muted",
};

export function StatusPill({ status }: { status?: string | null }) {
  const value = (status || "unknown").toLowerCase();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
        STATUS_STYLES[value] ?? "border-line bg-canvas text-muted"
      }`}
    >
      {value}
    </span>
  );
}

const KIND_STYLES: Record<OpsDetailKind, string> = {
  resolved: "border-accent/30 bg-accent/10 text-accent",
  failures: "border-red-400/30 bg-red-400/10 text-red-300",
  unnormalized: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  filtered: "border-sky-400/30 bg-sky-400/10 text-sky-200",
  validation: "border-violet-400/30 bg-violet-400/10 text-violet-200",
};

export function KindPill({ kind }: { kind: OpsDetailKind }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${KIND_STYLES[kind]}`}
    >
      {DETAIL_LABELS[kind]}
    </span>
  );
}

export function Th({
  children,
  className = "",
}: {
  children?: ReactNode;
  className?: string;
}) {
  return (
    <th
      scope="col"
      className={`whitespace-nowrap px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-muted ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  className = "",
  title,
}: {
  children?: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <td title={title} className={`px-4 py-3 align-middle text-sm ${className}`}>
      {children}
    </td>
  );
}

export function FilterForm({
  value,
  onChange,
  onSubmit,
  onClear,
  placeholder = "Username",
  label = "Apply filter",
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  placeholder?: string;
  label?: string;
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      className="flex items-center gap-1.5"
    >
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
          className={`${inputClass} w-36 pl-8 pr-7 sm:w-44`}
        />
        {value && (
          <button
            type="button"
            onClick={onClear}
            title="Clear filter"
            aria-label="Clear filter"
            className="absolute right-1.5 top-1/2 flex h-5 w-5 -translate-y-1/2 cursor-pointer items-center justify-center rounded text-muted transition hover:text-ink"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
      <button
        type="submit"
        title={label}
        aria-label={label}
        className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg border border-line bg-surface text-muted transition hover:border-accent/60 hover:text-ink"
      >
        <Search className="h-4 w-4" />
      </button>
    </form>
  );
}
