import { z } from 'zod';

export const JobAcceptedSchema = z.object({
  username: z.string().default("user"),
  params: z.string().default(""),
  job_taken: z.string().default(""),
});
export type JobAccepted = z.infer<typeof JobAcceptedSchema>;

export const RepoPageSchema = z.object({
  page: z.number().default(1),
  count: z.number().default(0),
  total_so_far: z.number().default(0),
  total_repos: z.number().default(0),
});
export type RepoPage = z.infer<typeof RepoPageSchema>;

export const RepoListedSchema = z.object({
  total: z.number().default(0),
});
export type RepoListed = z.infer<typeof RepoListedSchema>;

export const RepoScanStartSchema = z.object({
  repo: z.string().default(""),
  username: z.string().default(""),
  index: z.number().default(0),
  total: z.number().default(0),
});
export type RepoScanStart = z.infer<typeof RepoScanStartSchema>;

export const RepoScanDoneSchema = z.object({
  repo: z.string().default(""),
  index: z.number().default(0),
  cache_hit: z.boolean().default(false),
  ms: z.union([z.number(), z.string()]).default(0),
  package_count: z.number().default(0),
});
export type RepoScanDone = z.infer<typeof RepoScanDoneSchema>;

export const IconAttemptedSchema = z.object({
  slug: z.string().default(""),
  name: z.string().default(""),
  strategy: z.string().default("strategy"),
  candidate: z.string().default(""),
  result: z.string().default(""),
  reason: z.string().default(""),
});
export type IconAttempted = z.infer<typeof IconAttemptedSchema>;

export const IconResolvedSchema = z.object({
  slug: z.string().default(""),
  name: z.string().default(""),
  strategy: z.string().default(""),
  id: z.string().default(""),
  method: z.string().default(""),
  source: z.string().default(""),
  icon: z.string().default(""),
  icon_meta: z.any().default({}),
});
export type IconResolved = z.infer<typeof IconResolvedSchema>;

export const PackageFoundSchema = z.object({
  repo: z.string().default(""),
  packages: z.union([z.array(z.any()), z.record(z.string(), z.any())]).default([]),
  new_slugs: z.number().default(0),
  total_unknown: z.number().default(0),
});
export type PackageFound = z.infer<typeof PackageFoundSchema>;

export const IconFailedSchema = z.object({
  slug: z.string().default(""),
  name: z.string().default(""),
  tried: z.string().default(""),
  reason: z.string().default(""),
});
export type IconFailed = z.infer<typeof IconFailedSchema>;

export const ProgressSchema = z.object({
  phase: z.string().default("running"),
  done: z.number().default(0),
  total: z.union([z.number(), z.string()]).default(0),
});
export type Progress = z.infer<typeof ProgressSchema>;

export const WarningSchema = z.object({
  code: z.string().default(""),
  message: z.string().default(""),
  repo: z.string().default(""),
});
export type Warning = z.infer<typeof WarningSchema>;

export const DoneSchema = z.object({
  job_id: z.string().default(""),
  scene_url: z.string().default(""),
  stats: z.any().default(""),
});
export type Done = z.infer<typeof DoneSchema>;

export const ErrorEvtSchema = z.object({
  phase: z.string().default("pipeline"),
  message: z.string().default("Unknown error"),
  retryable: z.union([z.string(), z.boolean()]).default(false),
});
export type ErrorEvt = z.infer<typeof ErrorEvtSchema>;

export const EventEnvelopeSchema = z.object({
  job_id: z.string().default(""),
  type: z.string(),
  ts: z.number().default(0),
  seq: z.number().default(0),
  data: z.any().default({}),
});
export type EventEnvelope = z.infer<typeof EventEnvelopeSchema>;

// Lookup mapping supporting both singular and plural event variants
export const eventsLookUp: Record<string, z.ZodTypeAny> = {
  "job.accepted": JobAcceptedSchema,
  "repo.page": RepoPageSchema,
  "repos.page": RepoPageSchema,
  "repo.listed": RepoListedSchema,
  "repos.listed": RepoListedSchema,
  "repo.scan.start": RepoScanStartSchema,
  "repo.scan.done": RepoScanDoneSchema,
  "package.found": PackageFoundSchema,
  "packages.found": PackageFoundSchema,
  "icon.attempt": IconAttemptedSchema,
  "icons.attempted": IconAttemptedSchema,
  "icon.resolved": IconResolvedSchema,
  "icon.failed": IconFailedSchema,
  "progress": ProgressSchema,
  "done": DoneSchema,
  "error": ErrorEvtSchema,
  "warn": WarningSchema,
  "warning": WarningSchema,
};

// Formatter mapping for ticker notifications using clean direct property access
export const eventMessages: Record<string, (d: any) => string> = {
  'job.accepted': (d: JobAccepted) => `Job started for @${d.username}`,
  'repo.page': (d: RepoPage) => `Fetching repos: page ${d.page} (${d.total_so_far} found)`,
  'repos.page': (d: RepoPage) => `Fetching repos: page ${d.page} (${d.total_so_far} found)`,
  'repo.listed': (d: RepoListed) => `Found ${d.total} total repositories to scan`,
  'repos.listed': (d: RepoListed) => `Found ${d.total} total repositories to scan`,
  'repo.scan.start': (d: RepoScanStart) => `Scanning repo: ${d.repo}${d.index ? ` (#${d.index})` : ''}`,
  'package.found': (d: PackageFound) => {
    const count = Array.isArray(d.packages)
      ? d.packages.length
      : Object.keys(d.packages).length;
    return `Found ${count} package(s) in ${d.repo}`;
  },
  'packages.found': (d: PackageFound) => {
    const count = Array.isArray(d.packages)
      ? d.packages.length
      : Object.keys(d.packages).length;
    return `Found ${count} package(s) in ${d.repo}`;
  },
  'repo.scan.done': (d: RepoScanDone) => `Scanned ${d.repo} (${d.package_count} packages${d.cache_hit ? ', cached' : ''})`,
  'icon.attempt': (d: IconAttempted) => `Looking up ${d.name || d.slug} via ${d.strategy}...`,
  'icons.attempted': (d: IconAttempted) => `Looking up ${d.name || d.slug} via ${d.strategy}...`,
  'icon.resolved': (d: IconResolved) => `✓ Resolved icon for ${d.name || d.slug} (${d.strategy || d.method || 'resolved'})`,
  'icon.failed': (d: IconFailed) => `✗ Missing icon for ${d.name || d.slug}`,
  'progress': (d: Progress) => `Progress [${d.phase}]: ${d.done}/${d.total}`,
  'done': (_d: Done) => `✓ Scan complete! Ready to render.`,
  'error': (d: ErrorEvt) => `Error [${d.phase}]: ${d.message}`,
  'warn': (d: Warning) => `Warning: ${d.message}`,
  'warning': (d: Warning) => `Warning: ${d.message}`,
};



export type Logo = {

    id:string
    slug:string 
    name:string 
    count:number
    icon?:string 
    status: "placeholder" | "resolved" | "failed"
}




export type Scene = {

    logos:Map<string,Logo>
    phase:"idle" | "connecting" | "scanning"| "resolving" | "complete" | "error"
    stats:{
        repoDone:number,
        repoTotal:number,
        iconResolved:number
    }
}