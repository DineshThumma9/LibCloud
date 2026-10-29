import { presetCssVars, type CanvasSize, type Preset } from "./presets";

export async function svgToPngDataUrl(
  svg: string,
  width = 1600,
  height = 900
): Promise<string> {
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  try {
    const image = document.createElement("img");
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error("Could not rasterize SVG"));
      image.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas is not supported");
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** Clone the rendered cloud and flatten it into a standalone SVG string. */
export function buildSvgString(
  source: SVGSVGElement,
  preset: Preset,
  size: CanvasSize
): string {
  const clone = source.cloneNode(true) as SVGSVGElement;
  clone.querySelector(".cloud-tip-layer")?.remove();
  clone.setAttribute("width", String(size.width));
  clone.setAttribute("height", String(size.height));
  clone.setAttribute("viewBox", `0 0 ${size.width} ${size.height}`);
  for (const [name, value] of Object.entries(presetCssVars(preset))) {
    clone.style.setProperty(name, value);
  }
  return new XMLSerializer().serializeToString(clone);
}
