export type OpsRoute =
  | { page: "overview" }
  | { page: "runs" }
  | { page: "run"; runId: string }
  | { page: "failed" }
  | { page: "unnormalized" }
  | { page: "filtered" }
  | { page: "search" }
  | { page: "not-found" };

export function parseOpsRoute(pathname: string): OpsRoute {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/ops") return { page: "overview" };

  const rest = path.replace(/^\/ops\/?/, "");
  const [head, tail] = rest.split("/");

  switch (head) {
    case "runs":
      return tail ? { page: "run", runId: decodeURIComponent(tail) } : { page: "runs" };
    case "failed":
      return { page: "failed" };
    case "unnormalized":
      return { page: "unnormalized" };
    case "filtered":
      return { page: "filtered" };
    case "search":
      return { page: "search" };
    default:
      return { page: "not-found" };
  }
}

export function navigate(href: string): void {
  window.history.pushState({}, "", href);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function replaceQuery(path: string, query: Record<string, string>): void {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  const suffix = params.toString();
  window.history.replaceState({}, "", suffix ? `${path}?${suffix}` : path);
}
