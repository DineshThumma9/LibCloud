import { type Logo } from "./schemas";
import { create } from "zustand";

interface CloudState {
  logos: Map<string, Logo>;

  reset: () => void;
  handleEvent: (eventType: string, data: any) => void;
}

export const useCloudStore = create<CloudState>((set, get) => ({
  logos: new Map(),

  reset: () => set({ logos: new Map() }),

  handleEvent: (eventType, data) => {
    const { logos } = get();

    if (eventType === "package.found" || eventType === "packages.found") {
      const nextLogos = new Map(logos);
      const pkgs = Array.isArray(data.packages)
        ? data.packages
        : Object.values(data.packages || {});

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
        }
      }

      set({ logos: nextLogos });
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
      set({ logos: nextLogos });
    } else if (eventType === "icon.failed") {
      const nextLogos = new Map(logos);
      const slug = (data.slug || data.name || "").toLowerCase();
      const existing = nextLogos.get(slug);
      if (existing && existing.status !== "resolved") {
        nextLogos.set(slug, { ...existing, status: "failed" });
        set({ logos: nextLogos });
      }
    }
  },
}));
