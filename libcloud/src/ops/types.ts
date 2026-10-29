export type OpsCredentials = {
  username: string;
  password: string;
};

export type OpsDetailKind =
  | "resolved"
  | "failures"
  | "unnormalized"
  | "filtered"
  | "validation";

export type OpsRun = {
  run_id: string;
  username: string;
  started_at: string | null;
  finished_at?: string | null;
  status: string;
  duration_ms?: number | null;
  repo_count?: number;
  package_count?: number;
  resolved_count?: number;
  failed_count?: number;
  unnormalized_count?: number;
  filtered_count?: number;
  validation_failure_count?: number;
  resolution_methods?: Record<string, number>;
  error?: string | null;
};

export type OpsTotals = {
  repo_count: number;
  package_count: number;
  resolved_count: number;
  failed_count: number;
  unnormalized_count: number;
  filtered_count: number;
  validation_failure_count: number;
};

export type OpsSummary = {
  generated_at: string;
  runs: {
    total: number;
    completed: number;
    failed: number;
    cancelled: number;
    running: number;
  };
  totals: OpsTotals;
  rates: { resolved: number; failed: number };
  users: Array<{
    username: string;
    runs: number;
    last_started_at: string | null;
  }>;
  recent: OpsRun[];
};

export type OpsDetailRow = {
  kind?: OpsDetailKind;
  run_id?: string;
  username?: string;
  count?: number;
  norm_name?: string;
  raw_name?: string;
  cleaned_name?: string;
  slug?: string;
  slug_tried?: string;
  method?: string;
  source_url?: string;
  reason?: string;
  dep_origin?: string;
  language?: string;
  origin_path?: string;
  url?: string;
  size_bytes?: number;
};

export type OpsDetails = Record<OpsDetailKind, OpsDetailRow[]>;

export type OpsRunsResponse = {
  runs: OpsRun[];
  count: number;
};

export type OpsRunDetailResponse = {
  run: OpsRun;
  details: OpsDetails;
};

export type OpsDetailsResponse = {
  kind: OpsDetailKind;
  rows: OpsDetailRow[];
  count: number;
};

export type OpsSearchResponse = {
  query: string;
  results: OpsDetailRow[];
  count: number;
};
