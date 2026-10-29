import { useState } from "react";
import { ChevronRight, ListTree, RefreshCw } from "lucide-react";
import { getRuns } from "../api";
import {
  formatDate,
  formatDuration,
  formatFullDate,
  formatNumber,
} from "../format";
import type { OpsCredentials, OpsRun } from "../types";
import { useOpsResource } from "../useOpsResource";
import { replaceQuery } from "../navigation";
import {
  EmptyState,
  ErrorState,
  FilterForm,
  IconButton,
  Loading,
  OpsLink,
  PageHeader,
  Panel,
  StatusPill,
  Td,
  Th,
} from "../ui";

export function RunsPage({ credentials }: { credentials: OpsCredentials }) {
  const initialUsername =
    new URLSearchParams(window.location.search).get("username") ?? "";
  const [input, setInput] = useState(initialUsername);
  const [filter, setFilter] = useState(initialUsername.trim().toLowerCase());

  const { data, error, loading, reload } = useOpsResource(`runs:${filter}`, () =>
    getRuns(credentials, { username: filter || undefined, limit: 200 })
  );

  const applyFilter = (value: string) => {
    const next = value.trim().toLowerCase();
    setFilter(next);
    replaceQuery("/ops/runs", { username: next });
    reload();
  };

  const clearFilter = () => {
    setInput("");
    applyFilter("");
  };

  const description = data
    ? `${formatNumber(data.count)} run${data.count === 1 ? "" : "s"} returned${
        filter ? ` for ${filter}` : ""
      }, newest first.`
    : "Every recorded scan run, newest first.";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Run history"
        title="Runs"
        description={description}
        actions={
          <>
            <FilterForm
              value={input}
              onChange={setInput}
              onSubmit={() => applyFilter(input)}
              onClear={clearFilter}
            />
            <IconButton
              label="Refresh runs"
              icon={RefreshCw}
              onClick={reload}
              spinning={loading}
            />
          </>
        }
      />

      {loading && !data ? (
        <Loading label="Loading runs…" />
      ) : error && !data ? (
        <ErrorState message={error} onRetry={reload} />
      ) : data ? (
        <Panel>
          {data.runs.length === 0 ? (
            <EmptyState
              title="No runs match this filter"
              description={
                filter
                  ? `Nothing recorded for “${filter}”. Clear the filter to see all runs.`
                  : "Scan a GitHub user from the cloud app to record a run."
              }
              icon={ListTree}
            />
          ) : (
            <>
              <div className="divide-y divide-line md:hidden">
                {data.runs.map((run) => (
                  <RunCard key={run.run_id} run={run} />
                ))}
              </div>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[68rem] text-left">
                  <thead className="border-b border-line bg-canvas/40">
                    <tr>
                      <Th>Run</Th>
                      <Th>User</Th>
                      <Th>Status</Th>
                      <Th>Started</Th>
                      <Th className="text-right">Repos</Th>
                      <Th className="text-right">Packages</Th>
                      <Th className="text-right">Resolved</Th>
                      <Th className="text-right">Failed</Th>
                      <Th className="text-right">Unnorm.</Th>
                      <Th className="text-right">Filtered</Th>
                      <Th className="text-right">Duration</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {data.runs.map((run) => (
                      <RunRow key={run.run_id} run={run} />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Panel>
      ) : null}
    </div>
  );
}

function RunCard({ run }: { run: OpsRun }) {
  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <OpsLink
          href={`/ops/runs/${encodeURIComponent(run.run_id)}`}
          className="min-w-0 truncate font-mono text-xs text-ink transition hover:text-accent"
        >
          {run.run_id}
        </OpsLink>
        <StatusPill status={run.status} />
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted">
        <span>{run.username}</span>
        <span>{formatDate(run.started_at)}</span>
        <span>{formatDuration(run.duration_ms)}</span>
        <span>
          {formatNumber(run.repo_count)} repos · {formatNumber(run.package_count)} packages
        </span>
      </div>

      <div className="mt-2 grid grid-cols-4 gap-1.5">
        <RunCount label="Resolved" value={run.resolved_count} tone="text-accent" />
        <RunCount label="Failed" value={run.failed_count} tone="text-red-300" />
        <RunCount label="Unnorm." value={run.unnormalized_count} tone="text-amber-200" />
        <RunCount label="Filtered" value={run.filtered_count} tone="text-sky-200" />
      </div>
    </div>
  );
}

function RunCount({
  label,
  value,
  tone,
}: {
  label: string;
  value?: number;
  tone: string;
}) {
  return (
    <div className="rounded-lg bg-canvas/70 px-2 py-1.5">
      <p className="truncate text-[9px] font-semibold uppercase tracking-wider text-muted">
        {label}
      </p>
      <p className={`mt-0.5 text-sm font-semibold tabular-nums ${tone}`}>
        {formatNumber(value)}
      </p>
    </div>
  );
}

function RunRow({ run }: { run: OpsRun }) {
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
      <Td className="text-right text-muted tabular-nums">
        {formatNumber(run.repo_count)}
      </Td>
      <Td className="text-right text-muted tabular-nums">
        {formatNumber(run.package_count)}
      </Td>
      <Td className="text-right font-medium text-accent tabular-nums">
        {formatNumber(run.resolved_count)}
      </Td>
      <Td className="text-right font-medium text-red-300 tabular-nums">
        {formatNumber(run.failed_count)}
      </Td>
      <Td className="text-right font-medium text-amber-200 tabular-nums">
        {formatNumber(run.unnormalized_count)}
      </Td>
      <Td className="text-right font-medium text-sky-200 tabular-nums">
        {formatNumber(run.filtered_count)}
      </Td>
      <Td className="whitespace-nowrap text-right text-xs text-muted tabular-nums">
        {formatDuration(run.duration_ms)}
      </Td>
    </tr>
  );
}
