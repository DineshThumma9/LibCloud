import { type Logo } from "./schemas";
import { create } from "zustand";

interface CloudState {
  logos: Map<string, Logo>;
  phase: "idle" | "connecting" | "scanning" | "resolving" | "complete" | "error";
  statusText: string;
  stats: {
    reposDone: number;
    reposTotal: number;
    packageFound: number;
    iconsResolved: number;
  };
  error?: string;

  reset: () => void;
  setPhase: (phase: CloudState['phase'], text?: string) => void;
  handleEvent: (eventType: string, data: any) => void;
}

export const useCloudStore = create<CloudState>((set, get) => ({
  logos: new Map(),
  phase: "idle",
  statusText: "Nothing Yet",
  stats: {
    reposDone: 0,
    reposTotal: 0,
    packageFound: 0,
    iconsResolved: 0,
  },

  reset: () =>
    set({
      logos: new Map(),
      phase: "idle",
      statusText: "Nothing Yet",
      stats: {
        reposDone: 0,
        reposTotal: 0,
        packageFound: 0,
        iconsResolved: 0,
      },
      error: undefined,
    }),

  setPhase: (phase, text) =>
    set((s) => ({
      phase,
      statusText: text !== undefined ? text : s.statusText,
    })),

  handleEvent: (eventType, data) => {
    const { logos, stats } = get();

    if (eventType === "package.found" || eventType === "packages.found") {
      const nextLogos = new Map(logos);
      const pkgs = Array.isArray(data.packages)
        ? data.packages
        : Object.values(data.packages || {});
      let newCount = 0;

      for (const pkg of pkgs) {
        const slug = (pkg.slug || pkg.name || "").toLowerCase();
        if (!slug) continue;

        const doesExist = nextLogos.get(slug);
        if (doesExist) {
          nextLogos.set(slug, { ...doesExist, count: doesExist.count + (pkg.count || 1) });
        } else {
          nextLogos.set(slug, {
            id: `logo-${slug.replace(/[^a-z0-9]/g, "-")}`,
            slug,
            name: pkg.name || pkg.slug,
            count: pkg.count || 1,
            status: "placeholder",
          });
          newCount++;
        }
      }

      set({
        phase: "resolving",
        logos: nextLogos,
        stats: { ...stats, packageFound: stats.packageFound + newCount },
      });
    } else if (eventType === "icon.resolved") {
      const nextLogos = new Map(logos);
      const slug = (data.slug || data.name || "").toLowerCase();
      if (!slug) return;
      const existing = nextLogos.get(slug);
      if (existing) {
        nextLogos.set(slug, { ...existing, icon: data.icon, status: "resolved" });
      } else {
        // Safety net: a resolution can arrive before (or without) its
        // package.found event. Still show the logo instead of dropping it.
        nextLogos.set(slug, {
          id: `logo-${slug.replace(/[^a-z0-9]/g, "-")}`,
          slug,
          name: data.name || data.slug,
          count: 1,
          icon: data.icon,
          status: "resolved",
        });
      }
      set({
        logos: nextLogos,
        stats: { ...stats, iconsResolved: stats.iconsResolved + 1 },
      });
    } else if (eventType === "icon.failed") {
      const nextLogos = new Map(logos);
      const slug = (data.slug || data.name || "").toLowerCase();
      const existing = nextLogos.get(slug);
      if (existing && existing.status !== "resolved") {
        nextLogos.set(slug, { ...existing, status: "failed" });
        set({ logos: nextLogos });
      }
    } else if (eventType === "repo.scan.done") {
      set({ stats: { ...stats, reposDone: stats.reposDone + 1 } });
    } else if (eventType === "done") {
      set({ phase: "complete", statusText: "Generation complete!" });
    }
  },
}));
