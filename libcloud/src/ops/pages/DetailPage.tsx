import { useMemo, useState } from "react";
import { CircleOff, Filter, RefreshCw, ShieldAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { getDetails } from "../api";
import {
  formatNumber,
  humanize,
  humanizeLanguage,
  mergeUnique,
} from "../format";
import {
  groupDetailRows,
  type DetailGroup,
  type GroupedDetailKind,
} from "../grouping";
import type { OpsCredentials } from "../types";
import { useOpsResource } from "../useOpsResource";
import {
  EmptyState,
  ErrorState,
  FilterForm,
  IconButton,
  Loading,
  PageHeader,
  Panel,
  Td,
  Th,
} from "../ui";

type DetailConfig = {
  eyebrow: string;
  title: string;
  description: string;
  emptyTitle: string;
  emptyDescription: string;
  icon: LucideIcon;
};

const CONFIG: Record<GroupedDetailKind, DetailConfig> = {
  failures: {
    eyebrow: "Resolution gaps",
    title: "Failed icons",
    description:
      "Dependencies the resolver could not map to an icon, grouped by canonical name.",
    emptyTitle: "No failed icons",
    emptyDescription: "Every resolved attempt found an icon in the stored runs.",
    icon: CircleOff,
  },
  unnormalized: {
    eyebrow: "Normalization gaps",
    title: "Unnormalized packages",
    description:
      "Package names that bypassed normalization and may need a new naming rule.",
    emptyTitle: "No unnormalized packages",
    emptyDescription: "All parsed packages matched a normalization rule.",
    icon: ShieldAlert,
  },
  filtered: {
    eyebrow: "Noise control",
    title: "Filtered / noise",
    description:
      "Packages removed by the noise blocklist or unsupported manifest detection.",
    emptyTitle: "No filtered packages",
    emptyDescription: "The noise blocklist did not remove anything in stored runs.",
    icon: Filter,
  },
};

export function DetailPage({
  credentials,
  kind,
}: {
  credentials: OpsCredentials;
  kind: GroupedDetailKind;
}) {
  const config = CONFIG[kind];
  const [input, setInput] = useState("");
  const [filter, setFilter] = useState("");

  const { data, error, loading, reload } = useOpsResource(
    `details:${kind}:${filter}`,
    () =>
      getDetails(credentials, kind, {
        username: filter || undefined,
        limit: 2000,
      })
  );

  const groups = useMemo(
    () => groupDetailRows(kind, data?.rows ?? []),
    [kind, data]
  );

  const applyFilter = (value: string) => {
    const next = value.trim().toLowerCase();
    setFilter(next);
    reload();
  };

  const clearFilter = () => {
    setInput("");
    applyFilter("");
  };

  const description = data
    ? `${formatNumber(groups.length)} group${
        groups.length === 1 ? "" : "s"
      } across ${formatNumber(data.rows.length)} detail row${
        data.rows.length === 1 ? "" : "s"
      }${filter ? ` for ${filter}` : ""}.`
    : config.description;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={config.eyebrow}
        title={config.title}
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
              label={`Refresh ${config.title.toLowerCase()}`}
              icon={RefreshCw}
              onClick={reload}
              spinning={loading}
            />
          </>
        }
      />

      {loading && !data ? (
        <Loading label={`Loading ${config.title.toLowerCase()}…`} />
      ) : error && !data ? (
        <ErrorState message={error} onRetry={reload} />
      ) : data ? (
        <Panel
          title={`${formatNumber(groups.length)} grouped ${
            groups.length === 1 ? "entry" : "entries"
          }`}
          description={`Aggregated by canonical package or icon name${
            filter ? ` · filtered to ${filter}` : ""
          }`}
        >
          {groups.length === 0 ? (
            <EmptyState
              title={config.emptyTitle}
              description={filter ? `No records for “${filter}”.` : config.emptyDescription}
              icon={config.icon}
            />
          ) : (
            <>
              <div className="divide-y divide-line md:hidden">
                {groups.map((group) => (
                  <GroupCard key={group.key} kind={kind} group={group} />
                ))}
              </div>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[62rem] text-left">
                <thead className="border-b border-line bg-canvas/40">
                  <tr>
                    <Th>Name</Th>
                    <Th>Raw names</Th>
                    <Th>{kind === "failures" ? "Reason" : kind === "filtered" ? "Reason" : "Language"}</Th>
                    <Th>Origins</Th>
                    <Th className="text-right">Hits</Th>
                    <Th className="text-right">Runs</Th>
                    <Th className="text-right">Users</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {groups.map((group) => {
                    const origins = mergeUnique([
                      ...group.origins,
                      ...group.depOrigins,
                    ]);
                    return (
                      <tr key={group.key} className="transition hover:bg-canvas/50">
                        <Td className="font-medium text-ink">{group.label}</Td>
                        <Td className="max-w-[16rem] font-mono text-[11px] text-muted">
                          <LimitedList
                            values={group.rawNames}
                            empty="—"
                            mono
                          />
                        </Td>
                        <Td>
                          {kind === "unnormalized" ? (
                            <LimitedList
                              values={group.languages.map(humanizeLanguage)}
                              empty="—"
                            />
                          ) : (
                            <LimitedList
                              values={group.reasons.map(humanize)}
                              empty="—"
                              pill={kind === "failures" ? "danger" : "neutral"}
                            />
                          )}
                        </Td>
                        <Td className="max-w-[16rem] text-[11px] text-muted">
                          <LimitedList values={origins} empty="—" mono />
                        </Td>
                        <Td
                          className="text-right font-medium text-ink tabular-nums"
                          title={
                            group.hasCounts
                              ? undefined
                              : "Counts were not recorded for these rows"
                          }
                        >
                          {group.hasCounts ? formatNumber(group.hits) : "—"}
                        </Td>
                        <Td className="text-right text-muted tabular-nums">
                          {formatNumber(group.runs.length)}
                        </Td>
                        <Td
                          className="text-right text-muted tabular-nums"
                          title={group.users.join(", ")}
                        >
                          {formatNumber(group.users.length)}
                        </Td>
                      </tr>
                    );
                  })}
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

function GroupCard({
  kind,
  group,
}: {
  kind: GroupedDetailKind;
  group: DetailGroup;
}) {
  const origins = mergeUnique([...group.origins, ...group.depOrigins]);
  return (
    <div className="px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="break-words text-sm font-medium text-ink">{group.label}</p>
          <div className="mt-0.5 text-[10px] text-muted">
            <LimitedList values={group.rawNames} empty="" mono />
          </div>
        </div>
        <span className="shrink-0 text-right">
          <span className="block text-sm font-semibold text-ink tabular-nums">
            {group.hasCounts ? formatNumber(group.hits) : "—"}
          </span>
          <span className="block text-[10px] uppercase tracking-wider text-muted">
            hits
          </span>
        </span>
      </div>

      <div className="mt-2">
        {kind === "unnormalized" ? (
          <LimitedList
            values={group.languages.map(humanizeLanguage)}
            empty="—"
            pill="neutral"
          />
        ) : (
          <LimitedList
            values={group.reasons.map(humanize)}
            empty="—"
            pill={kind === "failures" ? "danger" : "neutral"}
          />
        )}
      </div>

      {origins.length > 0 && (
        <p
          className="mt-2 truncate font-mono text-[10px] text-muted"
          title={origins.join(", ")}
        >
          {origins.join(" · ")}
        </p>
      )}

      <div className="mt-2 flex items-center gap-3 text-[10px] text-muted">
        <span>
          {formatNumber(group.runs.length)}{" "}
          {group.runs.length === 1 ? "run" : "runs"}
        </span>
        <span>
          {formatNumber(group.users.length)}{" "}
          {group.users.length === 1 ? "user" : "users"}
        </span>
      </div>
    </div>
  );
}

function LimitedList({
  values,
  empty,
  mono,
  pill,
}: {
  values: string[];
  empty: string;
  mono?: boolean;
  pill?: "danger" | "neutral";
}) {
  if (values.length === 0) {
    return <span className="text-muted">{empty}</span>;
  }

  const visible = values.slice(0, 2);
  const remaining = values.length - visible.length;

  return (
    <span className="flex flex-wrap items-center gap-1" title={values.join(", ")}>
      {visible.map((value) => (
        <span
          key={value}
          className={
            pill
              ? `inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] ${
                  pill === "danger"
                    ? "border-red-400/25 bg-red-400/10 text-red-200"
                    : "border-line bg-canvas text-muted"
                }`
              : mono
                ? "break-all font-mono"
                : ""
          }
        >
          {value}
        </span>
      ))}
      {remaining > 0 && (
        <span className="text-[10px] text-muted">+{remaining}</span>
      )}
    </span>
  );
}
