import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleOff,
  Clock,
  Download,
  ExternalLink,
  Filter,
  FolderGit2,
  Loader2,
  Package,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  User,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { toast } from "sonner";
import { describeError, downloadRunCsv, getRun } from "../api";
import {
  countText,
  DETAIL_LABELS,
  formatBytes,
  formatDate,
  formatDuration,
  formatFullDate,
  formatNumber,
  hostOf,
  humanize,
  humanizeLanguage,
  humanizeMethod,
  isHttpUrl,
  rowName,
} from "../format";
import type { OpsCredentials, OpsDetailKind, OpsDetailRow } from "../types";
import { useOpsResource } from "../useOpsResource";
import {
  EmptyState,
  ErrorState,
  IconButton,
  Loading,
  OpsLink,
  PageHeader,
  Panel,
  StatusPill,
  Td,
  Th,
} from "../ui";

const TABS: Array<{ kind: OpsDetailKind; icon: LucideIcon; tone: string }> = [
  { kind: "resolved", icon: CheckCircle2, tone: "text-accent" },
  { kind: "failures", icon: CircleOff, tone: "text-red-300" },
  { kind: "unnormalized", icon: ShieldAlert, tone: "text-amber-200" },
  { kind: "filtered", icon: Filter, tone: "text-sky-200" },
  { kind: "validation", icon: ShieldCheck, tone: "text-violet-200" },
];

export function RunDetailPage({
  credentials,
  runId,
}: {
  credentials: OpsCredentials;
  runId: string;
}) {
  const [activeTab, setActiveTab] = useState<OpsDetailKind>("resolved");
  const [exporting, setExporting] = useState<OpsDetailKind | null>(null);

  const { data, error, loading, reload } = useOpsResource(`run:${runId}`, () =>
    getRun(credentials, runId)
  );

  const methods = useMemo(() => {
    const entries = Object.entries(data?.run.resolution_methods ?? {});
    return entries.sort((a, b) => b[1] - a[1]);
  }, [data]);

  const exportCsv = async (kind: OpsDetailKind) => {
    setExporting(kind);
    try {
      await downloadRunCsv(credentials, runId, kind);
      toast.success(`${DETAIL_LABELS[kind]} CSV downloaded`);
    } catch (reason) {
      toast.error(describeError(reason));
    } finally {
      setExporting(null);
    }
  };

  const backLink = (
    <OpsLink
      href="/ops/runs"
      className="inline-flex items-center gap-1 text-xs text-muted transition hover:text-ink"
    >
      <ArrowLeft className="h-3.5 w-3.5" />
      All runs
    </OpsLink>
  );

  if (loading && !data) {
    return (
      <div className="space-y-6">
        {backLink}
        <Loading label="Loading run…" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="space-y-6">
        {backLink}
        <ErrorState message={error} onRetry={reload} />
      </div>
    );
  }

  if (!data) return null;

  const { run, details } = data;
  const activeRows = details[activeTab] ?? [];

  return (
    <div className="space-y-6">
      {backLink}

      <PageHeader
        eyebrow="Run detail"
        title={
          <span className="flex flex-wrap items-center gap-2.5">
            <span className="font-mono text-lg sm:text-xl">{run.run_id}</span>
            <StatusPill status={run.status} />
          </span>
        }
        description={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>
              Started{" "}
              <time
                dateTime={formatFullDate(run.started_at) || undefined}
                title={formatFullDate(run.started_at)}
                className="text-ink"
              >
                {formatDate(run.started_at)}
              </time>
            </span>
            <span aria-hidden="true">·</span>
            <span className="inline-flex items-center gap-1">
              <User className="h-3 w-3" />
              <OpsLink
                href={`/ops/runs?username=${encodeURIComponent(run.username)}`}
                className="text-ink transition hover:text-accent"
              >
                {run.username}
              </OpsLink>
            </span>
            {run.finished_at && (
              <>
                <span aria-hidden="true">·</span>
                <span>
                  Finished{" "}
                  <time
                    dateTime={formatFullDate(run.finished_at) || undefined}
                    className="text-ink"
                  >
                    {formatDate(run.finished_at)}
                  </time>
                </span>
              </>
            )}
          </span>
        }
        actions={
          <IconButton
            label="Refresh run"
            icon={RefreshCw}
            onClick={reload}
            spinning={loading}
          />
        }
      />

      {run.error && (
        <div className="rounded-xl border border-red-400/30 bg-red-400/10 p-4 text-red-200">
          <p className="text-xs font-semibold uppercase tracking-wider">Run error</p>
          <p className="mt-1 whitespace-pre-wrap break-words font-mono text-xs leading-5">
            {run.error}
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-8">
        <StatTile
          label="Repositories"
          value={formatNumber(run.repo_count)}
          icon={FolderGit2}
          tone="text-muted"
        />
        <StatTile
          label="Packages"
          value={formatNumber(run.package_count)}
          icon={Package}
          tone="text-muted"
        />
        <StatTile
          label="Resolved"
          value={formatNumber(run.resolved_count)}
          icon={CheckCircle2}
          tone="text-accent"
        />
        <StatTile
          label="Failed"
          value={formatNumber(run.failed_count)}
          icon={CircleOff}
          tone="text-red-300"
        />
        <StatTile
          label="Unnormalized"
          value={formatNumber(run.unnormalized_count)}
          icon={ShieldAlert}
          tone="text-amber-200"
        />
        <StatTile
          label="Filtered"
          value={formatNumber(run.filtered_count)}
          icon={Filter}
          tone="text-sky-200"
        />
        <StatTile
          label="Validation"
          value={formatNumber(run.validation_failure_count)}
          icon={ShieldCheck}
          tone="text-violet-200"
        />
        <StatTile
          label="Duration"
          value={formatDuration(run.duration_ms)}
          icon={Clock}
          tone="text-muted"
        />
      </div>

      {methods.length > 0 && (
        <Panel
          title="Resolution methods"
          description="How resolved icons were matched during this run"
        >
          <div className="flex flex-wrap gap-2 p-4">
            {methods.map(([method, count]) => (
              <span
                key={method}
                className="inline-flex items-center gap-1.5 rounded-full border border-line bg-canvas px-2.5 py-1 text-xs"
              >
                <span className="text-muted">{humanizeMethod(method)}</span>
                <span className="font-medium text-ink tabular-nums">
                  {formatNumber(count)}
                </span>
              </span>
            ))}
          </div>
        </Panel>
      )}

      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-2">
          <div className="flex overflow-x-auto" role="tablist" aria-label="Run details">
            {TABS.map(({ kind, icon: Icon, tone }) => {
              const count = (details[kind] ?? []).length;
              const selected = activeTab === kind;
              return (
                <button
                  key={kind}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  aria-label={DETAIL_LABELS[kind]}
                  title={DETAIL_LABELS[kind]}
                  onClick={() => setActiveTab(kind)}
                  className={`flex shrink-0 cursor-pointer items-center gap-1.5 border-b-2 px-3 py-3 text-xs font-medium transition ${
                    selected
                      ? "border-accent text-ink"
                      : "border-transparent text-muted hover:text-ink"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${tone}`} />
                  <span className="hidden sm:inline">{DETAIL_LABELS[kind]}</span>
                  <span className="rounded-full bg-canvas px-1.5 py-0.5 text-[10px] text-muted tabular-nums">
                    {formatNumber(count)}
                  </span>
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={() => exportCsv(activeTab)}
            disabled={activeRows.length === 0 || exporting !== null}
            title={`Download ${DETAIL_LABELS[activeTab]} CSV`}
            aria-label={`Download ${DETAIL_LABELS[activeTab]} CSV`}
            className="mr-2 inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 text-xs font-medium text-muted transition hover:border-accent/60 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
          >
            {exporting === activeTab ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            CSV
          </button>
        </div>

        <DetailTable kind={activeTab} rows={activeRows} />
      </Panel>
    </div>
  );
}

function StatTile({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  tone: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-[10px] font-semibold uppercase tracking-wider text-muted">
          {label}
        </p>
        <Icon className={`h-3.5 w-3.5 shrink-0 ${tone}`} />
      </div>
      <p className="mt-1 text-xl font-semibold text-ink tabular-nums">{value}</p>
    </div>
  );
}

function DetailTable({
  kind,
  rows,
}: {
  kind: OpsDetailKind;
  rows: OpsDetailRow[];
}) {
  const tab = TABS.find((item) => item.kind === kind);
  if (rows.length === 0) {
    return (
      <EmptyState
        title={`No ${DETAIL_LABELS[kind].toLowerCase()} rows`}
        description="This run did not record any rows for this detail type."
        icon={tab?.icon ?? Package}
      />
    );
  }

  if (kind === "resolved") {
    return (
      <TableFrame minWidth="min-w-[52rem]">
        <thead className="border-b border-line bg-canvas/40">
          <tr>
            <Th>Icon</Th>
            <Th>Slug</Th>
            <Th>Method</Th>
            <Th className="text-right">Hits</Th>
            <Th>Source</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, index) => (
            <tr key={`${row.slug ?? row.norm_name}-${index}`} className="transition hover:bg-canvas/50">
              <Td className="font-medium text-ink">{rowName(row)}</Td>
              <Td className="font-mono text-[11px] text-muted">{row.slug || "—"}</Td>
              <Td>{row.method ? <Tag>{humanizeMethod(row.method)}</Tag> : <Muted />}</Td>
              <Td className="text-right font-medium text-accent tabular-nums">
                {countText(row)}
              </Td>
              <Td>
                <SourceLink url={row.source_url} />
              </Td>
            </tr>
          ))}
        </tbody>
      </TableFrame>
    );
  }

  if (kind === "failures") {
    return (
      <TableFrame minWidth="min-w-[54rem]">
        <thead className="border-b border-line bg-canvas/40">
          <tr>
            <Th>Icon</Th>
            <Th>Raw name</Th>
            <Th>Origin</Th>
            <Th>Reason</Th>
            <Th>Slug tried</Th>
            <Th className="text-right">Hits</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, index) => (
            <tr key={`${row.norm_name ?? row.raw_name}-${index}`} className="transition hover:bg-canvas/50">
              <Td className="font-medium text-ink">{rowName(row)}</Td>
              <Td className="font-mono text-[11px] text-muted">{row.raw_name || "—"}</Td>
              <Td className="text-xs text-muted">{row.dep_origin || "—"}</Td>
              <Td>
                {row.reason ? (
                  <Tag tone="danger">{humanize(row.reason)}</Tag>
                ) : (
                  <Muted />
                )}
              </Td>
              <Td className="font-mono text-[11px] text-muted">{row.slug_tried || "—"}</Td>
              <Td className="text-right font-medium text-red-300 tabular-nums">
                {countText(row)}
              </Td>
            </tr>
          ))}
        </tbody>
      </TableFrame>
    );
  }

  if (kind === "unnormalized") {
    return (
      <TableFrame minWidth="min-w-[56rem]">
        <thead className="border-b border-line bg-canvas/40">
          <tr>
            <Th>Package</Th>
            <Th>Raw name</Th>
            <Th>Language</Th>
            <Th>Dep origin</Th>
            <Th>Origin path</Th>
            <Th className="text-right">Hits</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, index) => (
            <tr key={`${row.cleaned_name ?? row.raw_name}-${index}`} className="transition hover:bg-canvas/50">
              <Td className="font-medium text-ink">{rowName(row)}</Td>
              <Td className="font-mono text-[11px] text-muted">{row.raw_name || "—"}</Td>
              <Td className="text-xs text-muted">{humanizeLanguage(row.language)}</Td>
              <Td className="font-mono text-[11px] text-muted">{row.dep_origin || "—"}</Td>
              <Td className="max-w-[18rem] truncate font-mono text-[11px] text-muted" title={row.origin_path}>
                {row.origin_path || "—"}
              </Td>
              <Td className="text-right font-medium text-amber-200 tabular-nums">
                {countText(row)}
              </Td>
            </tr>
          ))}
        </tbody>
      </TableFrame>
    );
  }

  if (kind === "filtered") {
    return (
      <TableFrame minWidth="min-w-[64rem]">
        <thead className="border-b border-line bg-canvas/40">
          <tr>
            <Th>Package</Th>
            <Th>Raw name</Th>
            <Th>Language</Th>
            <Th>Dep origin</Th>
            <Th>Origin path</Th>
            <Th>Reason</Th>
            <Th className="text-right">Hits</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, index) => (
            <tr key={`${row.raw_name ?? row.cleaned_name}-${index}`} className="transition hover:bg-canvas/50">
              <Td className="font-medium text-ink">{rowName(row)}</Td>
              <Td className="font-mono text-[11px] text-muted">{row.cleaned_name || "—"}</Td>
              <Td className="text-xs text-muted">{humanizeLanguage(row.language)}</Td>
              <Td className="font-mono text-[11px] text-muted">{row.dep_origin || "—"}</Td>
              <Td className="max-w-[16rem] truncate font-mono text-[11px] text-muted" title={row.origin_path}>
                {row.origin_path || "—"}
              </Td>
              <Td>
                {row.reason ? <Tag>{humanize(row.reason)}</Tag> : <Muted />}
              </Td>
              <Td className="text-right font-medium text-sky-200 tabular-nums">
                {countText(row)}
              </Td>
            </tr>
          ))}
        </tbody>
      </TableFrame>
    );
  }

  return (
    <TableFrame minWidth="min-w-[46rem]">
      <thead className="border-b border-line bg-canvas/40">
        <tr>
          <Th>URL</Th>
          <Th>Reason</Th>
          <Th className="text-right">Size</Th>
        </tr>
      </thead>
      <tbody className="divide-y divide-line">
        {rows.map((row, index) => (
          <tr key={`${row.url}-${index}`} className="transition hover:bg-canvas/50">
            <Td className="max-w-[30rem]">
              {isHttpUrl(row.url) ? (
                <a
                  href={row.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  title={row.url}
                  className="flex items-center gap-1 truncate font-mono text-[11px] text-muted transition hover:text-accent"
                >
                  <ExternalLink className="h-3 w-3 shrink-0" />
                  <span className="truncate">{row.url}</span>
                </a>
              ) : (
                <span className="font-mono text-[11px] text-muted">{row.url || "—"}</span>
              )}
            </Td>
            <Td>
              {row.reason ? (
                <Tag tone="violet">{humanize(row.reason)}</Tag>
              ) : (
                <Muted />
              )}
            </Td>
            <Td className="text-right text-xs text-muted tabular-nums">
              {formatBytes(row.size_bytes)}
            </Td>
          </tr>
        ))}
      </tbody>
    </TableFrame>
  );
}

function TableFrame({
  children,
  minWidth,
}: {
  children: ReactNode;
  minWidth: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className={`w-full text-left ${minWidth}`}>{children}</table>
    </div>
  );
}

function SourceLink({ url }: { url?: string }) {
  if (!isHttpUrl(url)) return <Muted />;
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer noopener"
      title={url}
      className="inline-flex items-center gap-1 text-[11px] text-muted transition hover:text-accent"
    >
      <ExternalLink className="h-3 w-3 shrink-0" />
      {hostOf(url)}
    </a>
  );
}

function Tag({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "danger" | "violet";
}) {
  const toneClass =
    tone === "danger"
      ? "border-red-400/25 bg-red-400/10 text-red-200"
      : tone === "violet"
        ? "border-violet-400/25 bg-violet-400/10 text-violet-200"
        : "border-line bg-canvas text-muted";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] ${toneClass}`}
    >
      {children}
    </span>
  );
}

function Muted() {
  return <span className="text-muted">—</span>;
}
