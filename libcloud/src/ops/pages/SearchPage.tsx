import { useState } from "react";
import { ChevronRight, ScanSearch } from "lucide-react";
import { searchRunDetails } from "../api";
import {
  countText,
  formatNumber,
  humanize,
  humanizeLanguage,
  humanizeMethod,
  isHttpUrl,
  rowName,
} from "../format";
import { replaceQuery } from "../navigation";
import type { OpsCredentials, OpsDetailRow } from "../types";
import { useOpsResource } from "../useOpsResource";
import {
  EmptyState,
  ErrorState,
  KindPill,
  Loading,
  OpsLink,
  PageHeader,
  Panel,
  Td,
  Th,
} from "../ui";

const EMPTY_RESPONSE = { query: "", results: [], count: 0 };

export function SearchPage({ credentials }: { credentials: OpsCredentials }) {
  const initialQuery = new URLSearchParams(window.location.search).get("q") ?? "";
  const [input, setInput] = useState(initialQuery);
  const [submitted, setSubmitted] = useState(initialQuery.trim());

  const { data, error, loading, reload } = useOpsResource(
    `search:${submitted}`,
    () =>
      submitted
        ? searchRunDetails(credentials, submitted)
        : Promise.resolve(EMPTY_RESPONSE)
  );

  const runSearch = () => {
    const term = input.trim();
    setSubmitted(term);
    replaceQuery("/ops/search", { q: term });
    reload();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Stored details"
        title="Search"
        description="Search icon names, slugs, package names, filter reasons, and validation URLs across stored runs."
      />

      <form
        onSubmit={(event) => {
          event.preventDefault();
          runSearch();
        }}
        className="flex flex-col gap-2 sm:flex-row"
      >
        <div className="relative flex-1">
          <ScanSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Search React, typing-extensions, no_icon_found…"
            aria-label="Search stored run details"
            maxLength={100}
            spellCheck={false}
            className="h-10 w-full rounded-lg border border-line bg-canvas pl-9 pr-3 text-sm text-ink outline-none transition placeholder:text-muted/60 focus:border-accent"
          />
        </div>
        <button
          type="submit"
          className="flex h-10 cursor-pointer items-center justify-center gap-1.5 rounded-lg bg-accent px-4 text-sm font-semibold text-accent-ink transition hover:brightness-110"
        >
          <ScanSearch className="h-4 w-4" />
          Search
        </button>
      </form>

      {!submitted ? (
        <Panel>
          <EmptyState
            title="Search stored runs"
            description="Try an icon name like React, a raw package like typing-extensions, or a failure reason like no_icon_found."
            icon={ScanSearch}
          />
        </Panel>
      ) : loading && !data ? (
        <Loading label="Searching stored runs…" />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : data ? (
        <Panel
          title={`${formatNumber(data.count)} match${
            data.count === 1 ? "" : "es"
          } for “${data.query}”`}
          description="Matches across resolved, failed, unnormalized, filtered, and validation rows"
        >
          {data.results.length === 0 ? (
            <EmptyState
              title="No matches"
              description={`Nothing stored matches “${data.query}”. Try a shorter term or a different spelling.`}
              icon={ScanSearch}
            />
          ) : (
            <>
              <div className="divide-y divide-line md:hidden">
                {data.results.map((row, index) => (
                  <SearchCard key={`${row.kind}-${row.run_id}-${index}`} row={row} />
                ))}
              </div>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[64rem] text-left">
                  <thead className="border-b border-line bg-canvas/40">
                    <tr>
                      <Th>Kind</Th>
                      <Th>Result</Th>
                      <Th>Context</Th>
                      <Th className="text-right">Hits</Th>
                      <Th>User</Th>
                      <Th>Run</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {data.results.map((row, index) => (
                      <SearchRow key={`${row.kind}-${row.run_id}-${index}`} row={row} />
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

function SearchCard({ row }: { row: OpsDetailRow }) {
  const kind = row.kind ?? "resolved";
  const name = rowName(row);
  const secondary = secondaryFor(row, name);
  const contexts = contextFor(row);
  const hits = countText(row);

  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <KindPill kind={kind} />
        <span className="text-[11px] text-muted tabular-nums">
          {hits === "—" ? "—" : `${hits} hits`}
        </span>
      </div>

      <p className="mt-1.5 break-words font-medium text-ink">{name}</p>
      {secondary && (
        <p className="mt-0.5 break-all font-mono text-[10px] text-muted" title={secondary}>
          {secondary}
        </p>
      )}

      {contexts.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {contexts.map((context) => (
            <span
              key={context}
              className="inline-flex items-center rounded-full border border-line bg-canvas px-1.5 py-0.5 text-[10px] text-muted"
            >
              {context}
            </span>
          ))}
        </div>
      )}

      <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-muted">
        <span>{row.username || "—"}</span>
        {row.run_id ? (
          <OpsLink
            href={`/ops/runs/${encodeURIComponent(row.run_id)}`}
            className="inline-flex min-w-0 items-center gap-1 font-mono text-[10px] transition hover:text-accent"
          >
            <span className="truncate">{row.run_id}</span>
            <ChevronRight className="h-3 w-3 shrink-0" />
          </OpsLink>
        ) : (
          <span>—</span>
        )}
      </div>
    </div>
  );
}

function SearchRow({ row }: { row: OpsDetailRow }) {
  const kind = row.kind ?? "resolved";
  const name = rowName(row);
  const secondary = secondaryFor(row, name);
  const contexts = contextFor(row);

  return (
    <tr className="transition hover:bg-canvas/50">
      <Td>
        <KindPill kind={kind} />
      </Td>
      <Td className="max-w-[18rem]">
        <p className="truncate font-medium text-ink" title={name}>
          {name}
        </p>
        {secondary && (
          <p
            className="mt-0.5 truncate font-mono text-[10px] text-muted"
            title={secondary}
          >
            {secondary}
          </p>
        )}
      </Td>
      <Td className="max-w-[22rem]">
        {contexts.length === 0 ? (
          <span className="text-muted">—</span>
        ) : (
          <span className="flex flex-wrap gap-1">
            {contexts.map((context) => (
              <span
                key={context}
                className="inline-flex items-center rounded-full border border-line bg-canvas px-1.5 py-0.5 text-[10px] text-muted"
              >
                {context}
              </span>
            ))}
          </span>
        )}
      </Td>
      <Td className="text-right font-medium text-ink tabular-nums">
        {countText(row)}
      </Td>
      <Td className="text-xs text-muted">{row.username || "—"}</Td>
      <Td>
        {row.run_id ? (
          <OpsLink
            href={`/ops/runs/${encodeURIComponent(row.run_id)}`}
            className="inline-flex items-center gap-1 font-mono text-[11px] text-muted transition hover:text-accent"
          >
            {row.run_id}
            <ChevronRight className="h-3 w-3 shrink-0" />
          </OpsLink>
        ) : (
          <span className="text-muted">—</span>
        )}
      </Td>
    </tr>
  );
}

function secondaryFor(row: OpsDetailRow, primary: string): string | null {
  const candidates = [row.raw_name, row.slug, row.slug_tried, row.url];
  for (const candidate of candidates) {
    if (candidate && candidate !== primary) return candidate;
  }
  return null;
}

function contextFor(row: OpsDetailRow): string[] {
  const kind = row.kind ?? "resolved";
  const values: Array<string | undefined> = [];

  if (kind === "resolved") values.push(row.method && humanizeMethod(row.method));
  if (kind === "failures" || kind === "filtered" || kind === "validation") {
    values.push(row.reason && humanize(row.reason));
  }
  if (kind === "unnormalized") values.push(row.language && humanizeLanguage(row.language));
  if (kind === "unnormalized" || kind === "filtered") {
    values.push(row.dep_origin);
  }
  if (kind === "validation" && row.url && isHttpUrl(row.url)) {
    values.push(row.url);
  }

  return Array.from(
    new Set(values.filter((value): value is string => Boolean(value)))
  );
}
