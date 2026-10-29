import { useCallback } from "react";
import type { RefObject } from "react";
import { toast } from "sonner";
import { createShare } from "../api";
import type { CanvasSize, Preset } from "../lib/presets";
import { buildSvgString, svgToPngDataUrl } from "../lib/svgExport";

export type ShareAction = "link" | "readme" | "svg" | "png";

type UseShareArgs = {
  graphRef: RefObject<SVGSVGElement | null>;
  username: string;
  preset: Preset;
  size: CanvasSize;
  hasLogos: boolean;
};

function downloadUrl(url: string, filename: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
}

export function useShare({
  graphRef,
  username,
  preset,
  size,
  hasLogos,
}: UseShareArgs) {
  const share = useCallback(
    async (action: ShareAction) => {
      if (!hasLogos || !graphRef.current) {
        toast.error("No logos to export yet", {
          description: "Generate your cloud first.",
        });
        return;
      }

      const svg = buildSvgString(graphRef.current, preset, size);
      const displayName = username.trim() || "user";
      const baseName = `libcloud-${username.trim() || "stack"}-${preset.id}-${size.id}`;

      if (action === "svg") {
        const blob = new Blob([svg], { type: "image/svg+xml" });
        const url = URL.createObjectURL(blob);
        downloadUrl(url, `${baseName}.svg`);
        URL.revokeObjectURL(url);
        toast.success("SVG downloaded");
        return;
      }

      if (action === "png") {
        try {
          const png = await svgToPngDataUrl(svg, size.width, size.height);
          downloadUrl(png, `${baseName}.png`);
          toast.success("PNG downloaded");
        } catch (e: any) {
          toast.error("Could not create PNG", {
            description: e?.message || "Rasterizing the cloud failed",
          });
        }
        return;
      }

      try {
        toast.loading("Creating share link...", { id: "share-toast" });
        let pngBase64 = "";
        try {
          pngBase64 = await svgToPngDataUrl(svg, size.width, size.height);
        } catch (e) {
          console.warn("Could not rasterize cloud image for social preview:", e);
        }

        const res = await createShare({
          username: displayName,
          svg_data: svg,
          png_base64: pngBase64,
          title: `@${displayName}'s Tech Stack`,
        });

        if (action === "readme") {
          await navigator.clipboard.writeText(res.markdown);
          toast.success("README Markdown copied", {
            id: "share-toast",
            description: "Paste it directly into your GitHub README.",
          });
        } else {
          await navigator.clipboard.writeText(res.page_url);
          toast.success("Link copied", {
            id: "share-toast",
            description: res.page_url,
          });
        }
      } catch (e: any) {
        toast.error("Failed to create share", {
          id: "share-toast",
          description: e.message || "Could not save share",
        });
      }
    },
    [graphRef, hasLogos, preset, size, username]
  );

  return { share };
}
