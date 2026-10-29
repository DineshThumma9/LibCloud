import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { Toaster } from "sonner";
import {
  ArrowUpRight,
  CircleOff,
  Filter,
  LayoutDashboard,
  ListTree,
  LogOut,
  Search,
  ShieldAlert,
  Terminal,
  User,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { clearCredentials, loadCredentials, UNAUTHORIZED_EVENT } from "./api";
import type { OpsCredentials } from "./types";
import { LoginGate } from "./LoginGate";
import { navigate, parseOpsRoute, type OpsRoute } from "./navigation";
import { EmptyState, OpsLink, PageHeader, Panel } from "./ui";
import { OverviewPage } from "./pages/OverviewPage";
import { RunsPage } from "./pages/RunsPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { DetailPage } from "./pages/DetailPage";
import { SearchPage } from "./pages/SearchPage";
import { PRESETS, presetCssVars } from "../lib/presets";

const OPS_THEME = presetCssVars(PRESETS.ink) as CSSProperties;

const NAV: Array<{
  label: string;
  href: string;
  icon: LucideIcon;
  active: (route: OpsRoute) => boolean;
}> = [
  {
    label: "Overview",
    href: "/ops",
    icon: LayoutDashboard,
    active: (route) => route.page === "overview",
  },
  {
    label: "Runs",
    href: "/ops/runs",
    icon: ListTree,
    active: (route) => route.page === "runs" || route.page === "run",
  },
  {
    label: "Failed",
    href: "/ops/failed",
    icon: CircleOff,
    active: (route) => route.page === "failed",
  },
  {
    label: "Unnormalized",
    href: "/ops/unnormalized",
    icon: ShieldAlert,
    active: (route) => route.page === "unnormalized",
  },
  {
    label: "Filtered",
    href: "/ops/filtered",
    icon: Filter,
    active: (route) => route.page === "filtered",
  },
  {
    label: "Search",
    href: "/ops/search",
    icon: Search,
    active: (route) => route.page === "search",
  },
];

export default function OpsApp() {
  const [credentials, setCredentials] = useState<OpsCredentials | null>(() =>
    loadCredentials()
  );
  const [route, setRoute] = useState<OpsRoute>(() =>
    parseOpsRoute(window.location.pathname)
  );
  const [locationKey, setLocationKey] = useState(
    () => `${window.location.pathname}${window.location.search}`
  );

  useEffect(() => {
    document.title = "LibCloud ops";
    let meta = document.querySelector<HTMLMetaElement>('meta[name="robots"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "robots";
      document.head.appendChild(meta);
    }
    meta.content = "noindex, nofollow";
  }, []);

  useEffect(() => {
    const onPopState = () => {
      setRoute(parseOpsRoute(window.location.pathname));
      setLocationKey(`${window.location.pathname}${window.location.search}`);
    };
    const onUnauthorized = () => setCredentials(null);
    window.addEventListener("popstate", onPopState);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => {
      window.removeEventListener("popstate", onPopState);
      window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    };
  }, []);

  const signOut = () => {
    clearCredentials();
    setCredentials(null);
    setRoute({ page: "overview" });
    setLocationKey("/ops");
    window.history.replaceState({}, "", "/ops");
  };

  if (!credentials) {
    return (
      <div data-theme="ink" style={OPS_THEME}>
        <Toaster richColors position="top-right" theme="dark" />
        <LoginGate onAuthenticated={setCredentials} />
      </div>
    );
  }

  return (
    <div data-theme="ink" style={OPS_THEME} className="min-h-screen bg-canvas text-ink">
      <Toaster richColors position="top-right" theme="dark" />

      <header className="sticky top-0 z-30 border-b border-line bg-canvas/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <OpsLink href="/ops" className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-accent-ink">
              <Terminal className="h-4 w-4" />
            </span>
            <span className="text-sm font-semibold tracking-tight">LibCloud</span>
            <span className="rounded border border-line bg-surface px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted">
              ops
            </span>
          </OpsLink>

          <div className="flex items-center gap-2">
            <a
              href="/"
              className="hidden h-8 items-center gap-1 rounded-lg border border-line bg-surface px-2.5 text-xs text-muted transition hover:border-accent/60 hover:text-ink sm:flex"
            >
              Cloud app
              <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
            <span className="hidden items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs text-muted md:flex">
              <User className="h-3.5 w-3.5" />
              {credentials.username}
            </span>
            <button
              type="button"
              onClick={signOut}
              title="Sign out"
              aria-label="Sign out"
              className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg border border-line bg-surface text-muted transition hover:border-red-400/40 hover:text-red-300"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <nav className="mx-auto max-w-7xl overflow-x-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-1 pb-2">
            {NAV.map(({ label, href, icon: Icon, active }) => {
              const isActive = active(route);
              return (
                <OpsLink
                  key={href}
                  href={href}
                  aria-current={isActive ? "page" : undefined}
                  aria-label={label}
                  title={label}
                  className={`flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
                    isActive
                      ? "border-accent/20 bg-accent/10 text-accent"
                      : "border-transparent text-muted hover:bg-surface hover:text-ink"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">{label}</span>
                </OpsLink>
              );
            })}
          </div>
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <OpsPage key={locationKey} route={route} credentials={credentials} />
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-8 text-[11px] text-muted sm:px-6 lg:px-8">
        Read-only dashboard · Mongo-backed run records ·{" "}
        <button
          type="button"
          onClick={() => navigate("/ops")}
          className="cursor-pointer underline decoration-line underline-offset-2 transition hover:text-ink"
        >
          overview
        </button>
      </footer>
    </div>
  );
}

function OpsPage({
  route,
  credentials,
}: {
  route: OpsRoute;
  credentials: OpsCredentials;
}) {
  switch (route.page) {
    case "overview":
      return <OverviewPage credentials={credentials} />;
    case "runs":
      return <RunsPage credentials={credentials} />;
    case "run":
      return <RunDetailPage credentials={credentials} runId={route.runId} />;
    case "failed":
      return <DetailPage credentials={credentials} kind="failures" />;
    case "unnormalized":
      return <DetailPage credentials={credentials} kind="unnormalized" />;
    case "filtered":
      return <DetailPage credentials={credentials} kind="filtered" />;
    case "search":
      return <SearchPage credentials={credentials} />;
    default:
      return (
        <div className="space-y-6">
          <PageHeader
            eyebrow="Not found"
            title="Unknown ops page"
            description="This route does not exist. Use the navigation above to return to the dashboard."
          />
          <Panel>
            <EmptyState
              title="Nothing here"
              description="Check the URL or open the overview."
              icon={Search}
            />
          </Panel>
        </div>
      );
  }
}
