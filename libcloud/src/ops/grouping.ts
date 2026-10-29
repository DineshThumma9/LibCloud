import { rowHits } from "./format";
import type { OpsDetailKind, OpsDetailRow } from "./types";

export type GroupedDetailKind = Extract<
  OpsDetailKind,
  "failures" | "unnormalized" | "filtered"
>;

export type DetailGroup = {
  key: string;
  label: string;
  hits: number;
  hasCounts: boolean;
  rowCount: number;
  runs: string[];
  users: string[];
  rawNames: string[];
  reasons: string[];
  languages: string[];
  origins: string[];
  depOrigins: string[];
};

type MutableGroup = Omit<
  DetailGroup,
  "runs" | "users" | "rawNames" | "reasons" | "languages" | "origins" | "depOrigins"
> & {
  runs: Set<string>;
  users: Set<string>;
  rawNames: Set<string>;
  reasons: Set<string>;
  languages: Set<string>;
  origins: Set<string>;
  depOrigins: Set<string>;
};

function labelFor(kind: GroupedDetailKind, row: OpsDetailRow): string {
  if (kind === "failures") {
    return row.norm_name || row.slug_tried || row.raw_name || "Unknown";
  }
  if (kind === "unnormalized") {
    return row.cleaned_name || row.raw_name || "Unknown";
  }
  return row.raw_name || row.cleaned_name || row.norm_name || "Unknown";
}

function keyFor(value: string): string {
  return value.trim().toLowerCase();
}

export function groupDetailRows(
  kind: GroupedDetailKind,
  rows: OpsDetailRow[]
): DetailGroup[] {
  const groups = new Map<string, MutableGroup>();

  for (const row of rows) {
    const label = labelFor(kind, row);
    const key = keyFor(label);
    let group = groups.get(key);
    if (!group) {
      group = {
        key,
        label,
        hits: 0,
        hasCounts: false,
        rowCount: 0,
        runs: new Set(),
        users: new Set(),
        rawNames: new Set(),
        reasons: new Set(),
        languages: new Set(),
        origins: new Set(),
        depOrigins: new Set(),
      };
      groups.set(key, group);
    }

    group.hits += rowHits(row);
    if (row.count !== undefined && row.count !== null) group.hasCounts = true;
    group.rowCount += 1;
    if (row.run_id) group.runs.add(row.run_id);
    if (row.username) group.users.add(row.username);
    if (row.reason) group.reasons.add(row.reason);
    if (row.language) group.languages.add(row.language);
    if (row.origin_path) group.origins.add(row.origin_path);
    if (row.dep_origin) group.depOrigins.add(row.dep_origin);

    if (kind === "failures") {
      if (row.raw_name) group.rawNames.add(row.raw_name);
      if (row.slug_tried) group.rawNames.add(row.slug_tried);
    } else if (kind === "unnormalized") {
      if (row.raw_name) group.rawNames.add(row.raw_name);
    } else if (row.cleaned_name) {
      group.rawNames.add(row.cleaned_name);
    }
  }

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      runs: Array.from(group.runs),
      users: Array.from(group.users),
      rawNames: Array.from(group.rawNames).filter(
        (name) => keyFor(name) !== group.key
      ),
      reasons: Array.from(group.reasons),
      languages: Array.from(group.languages),
      origins: Array.from(group.origins),
      depOrigins: Array.from(group.depOrigins),
    }))
    .sort((a, b) => b.hits - a.hits || a.label.localeCompare(b.label));
}
