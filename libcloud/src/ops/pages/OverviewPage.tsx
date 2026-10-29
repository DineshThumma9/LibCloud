import {
  Activity,
  CheckCircle2,
  ChevronRight,
  CircleOff,
  Database,
  Filter,
  FolderGit2,
  Package,
  RefreshCw,
  ShieldAlert,
  User,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { getSummary } from "../api";
import {
  formatDate,
  formatDuration,
  formatFullDate,
  formatNumber,
  formatPercent,
} from "../format";
import type { OpsCredentials, OpsRun } from "../types";
import { useOpsResource } from "../useOpsResource";
import {
  EmptyState,
  ErrorState,
  IconButton,
  Loading,
  Metric,
  OpsLink,
  PageHeader,
  Panel,
  ProgressBar,
  StatusPill,
  Td,
  Th,
} from "../ui";

export function OverviewPage({ credentials }: { credentials: OpsCredentials }) {
  const { data, error, loading, reload } = useOpsResource("summary", () =>
    getSummary(credentials)
  );

  const header = (
    <PageHeader
      eyebrow="Run overview"
      title="Scan operations"
      description={
        data
          ? `Aggregate health across ${formatNumber(data.runs.total)} stored runs. Generated ${formatDate(data.generated_at)}.`
          : "Aggregate health across every stored scan run."
      }
      actions={
        <IconButton
          label="Refresh overview"
          icon={RefreshCw}
          onClick={reload}
          spinning={loading}
        />
      }
    />
  );

  if (loading && !data) {
    return (
      <div className="space-y-6">
        {header}
        <Loading label="Loading overview…" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState message={error} onRetry={reload} />
      </div>
    );
  }

  if (!data) return null;

  const { runs, totals, rates, users, recent } = data;

  return (
    <div className="space-y-6">
      {header}

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Metric
          label="Total runs"
          value={formatNumber(runs.total)}
          hint={`${formatNumber(runs.completed)} completed · ${formatNumber(runs.failed)} failed`}
          icon={Activity}
        />
        <Metric
          label="Resolved rate"
          value={formatPercent(rates.resolved)}
          hint={`${formatNumber(totals.resolved_count)} resolved icon hits`}
          icon={CheckCircle2}
        />
        <Metric
          label="Failed rate"
          value={formatPercent(rates.failed)}
          hint={`${formatNumber(totals.failed_count)} unresolved icon hits`}
          icon={CircleOff}
          tone="danger"
        />
        <Metric
          label="Repositories"
          value={formatNumber(totals.repo_count)}
          hint={`${formatNumber(totals.package_count)} dependency packages parsed`}
          icon={FolderGit2}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Panel
          title="Recent runs"
          description="Latest 15 recorded scans"
          actions={
            <OpsLink
              href="/ops/runs"
              className="inline-flex items-center gap-1 text-xs text-muted transition hover:text-accent"
            >
              All runs
              <ChevronRight className="h-3 w-3 shrink-0" />
            </OpsLink>
          }
        >
          {recent.length === 0 ? (
            <EmptyState
              title="No runs recorded"
              description="Scan a GitHub user from the cloud app and the run will appear here."
              icon={Database}
            />
          ) : (
            <>
              <div className="divide-y divide-line sm:hidden">
                {recent.map((run) => (
                  <RecentRunCard key={run.run_id} run={run} />
                ))}
              </div>
              <div className="hidden overflow-x-auto sm:block">
                <table className="w-full text-left">
                  <thead className="border-b border-line bg-canvas/40">
                    <tr>
                      <Th>Run</Th>
                      <Th>User</Th>
                      <Th>Status</Th>
                      <Th>Started</Th>
                      <Th className="text-right">Resolved</Th>
                      <Th className="text-right">Failed</Th>
                      <Th className="text-right">Duration</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {recent.map((run) => (
                      <RecentRunRow key={run.run_id} run={run} />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel title="Resolution health" description="Across all attempts">
            <div className="space-y-4 p-4">
              <div>
                <div className="mb-1.5 flex items-center justify-between text-xs">
                  <span className="text-muted">Resolved</span>
                  <span className="font-semibold text-accent tabular-nums">
                    {formatPercent(rates.resolved)}
                  </span>
                </div>
                <ProgressBar value={rates.resolved} />
              </div>
              <div>
                <div className="mb-1.5 flex items-center justify-between text-xs">
                  <span className="text-muted">Failed</span>
                  <span className="font-semibold text-red-300 tabular-nums">
                    {formatPercent(rates.failed)}
                  </span>
                </div>
                <ProgressBar value={rates.failed} tone="danger" />
              </div>

              <div className="grid grid-cols-2 gap-2 border-t border-line pt-3">
                <StatusCount label="Completed" value={runs.completed} tone="text-accent" />
                <StatusCount label="Failed" value={runs.failed} tone="text-red-300" />
                <StatusCount label="Running" value={runs.running} tone="text-amber-200" />
                <StatusCount label="Cancelled" value={runs.cancelled} tone="text-muted" />
              </div>
            </div>
          </Panel>

          <Panel
            title="Users"
            description={`${formatNumber(users.length)} distinct users`}
          >
            {users.length === 0 ? (
              <EmptyState title="No users yet" icon={User} />
            ) : (
              <ul className="divide-y divide-line">
                {users.slice(0, 8).map((user) => (
                  <li key={user.username}>
                    <OpsLink
                      href={`/ops/runs?username=${encodeURIComponent(user.username)}`}
                      className="flex items-center justify-between gap-3 px-4 py-2.5 transition hover:bg-canvas/60"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <User className="h-3.5 w-3.5 shrink-0 text-muted" />
                        <span className="truncate text-sm text-ink">
                          {user.username}
                        </span>
                      </span>
                      <span className="shrink-0 text-[11px] text-muted tabular-nums">
                        {formatNumber(user.runs)} {user.runs === 1 ? "run" : "runs"}
                      </span>
                    </OpsLink>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      <Panel
        title="Run totals"
        description="Aggregated counts across every stored detail row"
      >
        <div className="grid grid-cols-2 gap-px bg-line sm:grid-cols-3 lg:grid-cols-6">
          <TotalTile
            label="Resolved"
            value={totals.resolved_count}
            icon={CheckCircle2}
            tone="text-accent"
          />
          <TotalTile
            label="Failed"
            value={totals.failed_count}
            icon={CircleOff}
            tone="text-red-300"
          />
          <TotalTile
            label="Unnormalized"
            value={totals.unnormalized_count}
            icon={ShieldAlert}
            tone="text-amber-200"
          />
          <TotalTile
            label="Filtered"
            value={totals.filtered_count}
            icon={Filter}
            tone="text-sky-200"
          />
          <TotalTile
            label="Validation"
            value={totals.validation_failure_count}
            icon={ShieldAlert}
            tone="text-violet-200"
          />
          <TotalTile
            label="Packages"
            value={totals.package_count}
            icon={Package}
            tone="text-muted"
          />
        </div>
      </Panel>
    </div>
  );
}

function RecentRunCard({ run }: { run: OpsRun }) {
  return (
    <OpsLink
      href={`/ops/runs/${encodeURIComponent(run.run_id)}`}
      className="block px-4 py-3 transition hover:bg-canvas/50"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="min-w-0 truncate font-mono text-xs text-ink">
          {run.run_id}
        </span>
        <StatusPill status={run.status} />
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted">
        <span>{run.username}</span>
        <span>{formatDate(run.started_at)}</span>
        <span>{formatDuration(run.duration_ms)}</span>
      </div>
      <div className="mt-2 flex items-center gap-4 text-[11px]">
        <span>
          <span className="font-medium text-accent tabular-nums">
            {formatNumber(run.resolved_count)}
          </span>{" "}
          resolved
        </span>
        <span>
          <span className="font-medium text-red-300 tabular-nums">
            {formatNumber(run.failed_count)}
          </span>{" "}
          failed
        </span>
      </div>
    </OpsLink>
  );
}

function RecentRunRow({ run }: { run: OpsRun }) {
  return (
    <tr className="transition hover:bg-canvas/50">
      <Td>
        <OpsLink
          href={`/ops/runs/${encodeURIComponent(run.run_id)}`}
          className="inline-flex items-center gap-1 font-mono text-xs text-ink transition hover:text-accent"
        >
          {run.run_id}
          <ChevronRight className="h-3 w-3 shrink-0" />
        </OpsLink>
      </Td>
      <Td className="text-muted">{run.username}</Td>
      <Td>
        <StatusPill status={run.status} />
      </Td>
      <Td className="whitespace-nowrap text-xs text-muted">
        <time
          dateTime={formatFullDate(run.started_at) || undefined}
          title={formatFullDate(run.started_at)}
        >
          {formatDate(run.started_at)}
        </time>
      </Td>
      <Td className="text-right font-medium text-accent tabular-nums">
        {formatNumber(run.resolved_count)}
      </Td>
      <Td className="text-right font-medium text-red-300 tabular-nums">
        {formatNumber(run.failed_count)}
      </Td>
      <Td className="whitespace-nowrap text-right text-xs text-muted tabular-nums">
        {formatDuration(run.duration_ms)}
      </Td>
    </tr>
  );
}

function StatusCount({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: string;
}) {
  return (
    <div className="rounded-lg bg-canvas/70 px-2 py-1.5">
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className={`mt-0.5 text-base font-semibold tabular-nums ${tone}`}>
        {formatNumber(value)}
      </p>
    </div>
  );
}

function TotalTile({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  tone: string;
}) {
  return (
    <div className="flex items-center gap-3 bg-surface p-4">
      <Icon className={`h-4 w-4 shrink-0 ${tone}`} />
      <div className="min-w-0">
        <p className="truncate text-[10px] font-semibold uppercase tracking-wider text-muted">
          {label}
        </p>
        <p className="mt-0.5 text-lg font-semibold text-ink tabular-nums">
          {formatNumber(value)}
        </p>
      </div>
    </div>
  );
}
