import type { OpsDetailKind, OpsDetailRow } from "./types";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const numberFormatter = new Intl.NumberFormat();

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return dateFormatter.format(date);
}

export function formatFullDate(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString();
}

export function formatNumber(value?: number | null): string {
  return numberFormatter.format(Math.max(0, Number(value) || 0));
}

export function formatPercent(rate?: number | null): string {
  const value = Math.max(0, Math.min(1, Number(rate) || 0));
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDuration(ms?: number | null): string {
  if (ms === null || ms === undefined || Number.isNaN(Number(ms))) return "—";
  const total = Math.max(0, Number(ms));
  if (total < 1000) return `${Math.round(total)}ms`;
  if (total < 60_000) return `${(total / 1000).toFixed(total < 10_000 ? 1 : 0)}s`;
  const minutes = Math.floor(total / 60_000);
  const seconds = Math.round((total % 60_000) / 1000);
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

export function formatBytes(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  const bytes = Math.max(0, Number(value));
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function humanize(value?: string | null): string {
  if (!value) return "Unknown";
  const text = value.replace(/[_-]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const METHOD_LABELS: Record<string, string> = {
  db_cache: "DB cache",
  cdn_catalog: "CDN catalog",
  github_topic: "GitHub topic",
  github_opengraph: "GitHub OpenGraph",
  github_org_avatar: "GitHub org avatar",
  github_repo_tree: "GitHub repo tree",
  homepage_favicon: "Homepage favicon",
  unknown: "Unknown",
};

export function humanizeMethod(value?: string | null): string {
  if (!value) return "Unknown";
  return METHOD_LABELS[value] ?? humanize(value);
}

const LANGUAGE_LABELS: Record<string, string> = {
  py: "Python",
  python: "Python",
  ts: "TypeScript",
  typescript: "TypeScript",
  js: "JavaScript",
  javascript: "JavaScript",
  java: "Java",
  kotlin: "Kotlin",
  go: "Go",
  rust: "Rust",
  ruby: "Ruby",
  php: "PHP",
  actions: "GitHub Actions",
  docker: "Docker",
  unknown: "Unknown",
};

export function humanizeLanguage(value?: string | null): string {
  if (!value) return "—";
  return LANGUAGE_LABELS[value.toLowerCase()] ?? humanize(value);
}

export function countText(row: OpsDetailRow): string {
  return row.count === undefined || row.count === null
    ? "—"
    : formatNumber(rowHits(row));
}

export function rowName(row: OpsDetailRow): string {
  return (
    row.norm_name ||
    row.cleaned_name ||
    row.raw_name ||
    row.slug ||
    row.slug_tried ||
    row.url ||
    "Unknown"
  );
}

export function rowHits(row: OpsDetailRow): number {
  return Math.max(0, Number(row.count) || 0);
}

export function hostOf(url?: string | null): string {
  if (!url) return "";
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export function isHttpUrl(value?: string | null): value is string {
  return Boolean(value && /^https?:\/\//i.test(value));
}

export function mergeUnique(
  values: Array<string | undefined | null>
): string[] {
  return Array.from(
    new Set(values.filter((value): value is string => Boolean(value)))
  );
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${formatNumber(count)} ${count === 1 ? singular : plural}`;
}

export const DETAIL_LABELS: Record<OpsDetailKind, string> = {
  resolved: "Resolved",
  failures: "Failures",
  unnormalized: "Unnormalized",
  filtered: "Filtered",
  validation: "Validation",
};
