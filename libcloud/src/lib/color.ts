const HEX_COLOR = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
const SVG_PAINT =
  /(?:fill|stroke|stop-color|color)\s*[:=]\s*["']?\s*(#[0-9a-fA-F]{3,6}|rgba?\([^)]*\)|white|black|currentColor)/gi;
const DARK_ICON_INK = "#0f172a";
export const PLATE_ON_DARK = "#f1f5f9";
export const PLATE_ON_LIGHT = "#ffffff";
export const PLATE_DARK = "#111827";

function colorChannels(color: string): [number, number, number] | null {
  const value = color.trim();
  const lower = value.toLowerCase();
  if (lower === "white") return [1, 1, 1];
  if (lower === "black") return [0, 0, 0];
  if (lower === "currentcolor") return null;

  if (lower.startsWith("rgb")) {
    const numbers = value.match(/[\d.]+/g);
    if (!numbers || numbers.length < 3) return null;
    return numbers.slice(0, 3).map((n) => Math.min(Number(n), 255) / 255) as [
      number,
      number,
      number,
    ];
  }

  const match = HEX_COLOR.exec(value);
  if (!match) return null;
  let digits = match[1];
  if (digits.length === 3) {
    digits = digits
      .split("")
      .map((c) => c + c)
      .join("");
  }
  return [0, 2, 4].map((i) => parseInt(digits.slice(i, i + 2), 16) / 255) as [
    number,
    number,
    number,
  ];
}

function relativeLuminance(color: string): number | null {
  const channels = colorChannels(color);
  if (!channels) return null;
  const linear = channels.map((c) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  );
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function isAchromaticWhite(color: string): boolean {
  const channels = colorChannels(color);
  if (!channels) return false;
  return Math.min(...channels) >= 0.9 && Math.max(...channels) - Math.min(...channels) <= 0.06;
}

function toBase64Utf8(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

const normalizedIconCache = new Map<string, string | undefined>();
const EMPTY_CLIP_PATH =
  /<clipPath\b[^>]*\bid=["']([^"']+)["'][^>]*>\s*<\/clipPath>/gi;
const CLIP_PATH_REF =
  /\sclip-path\s*=\s*["']url\(#([^)"']+)\)["']/gi;

/**
 * Some cached Simple Icons are stored as a white-only variant, which makes
 * black brand marks (Radix, Next.js, ShadCN, Vercel...) look grey on a dark
 * chip. Recolour those monochrome-white SVGs to near-black instead.
 *
 * This is a display-time safety net for legacy cache entries; the durable fix
 * is to store the original brand-coloured SVG at ingestion time.
 *
 * Also drop references to empty <clipPath> definitions: exported SVGs often
 * contain `clip-path="url(#clip0)"` plus an empty clip path, which hides the
 * entire artwork.
 */
export function normalizeIcon(icon?: string): string | undefined {
  if (!icon?.startsWith("data:image/svg+xml;base64,")) return icon;
  if (normalizedIconCache.has(icon)) return normalizedIconCache.get(icon);

  let normalized = icon;
  try {
    const svg = atob(icon.slice(icon.indexOf(",") + 1));

    const emptyClipIds = new Set<string>();
    for (const match of svg.matchAll(EMPTY_CLIP_PATH)) {
      emptyClipIds.add(match[1]);
    }
    const sanitized =
      emptyClipIds.size > 0
        ? svg.replace(CLIP_PATH_REF, (match, id: string) =>
            emptyClipIds.has(id) ? "" : match
          )
        : svg;

    const paints = Array.from(sanitized.matchAll(SVG_PAINT), (match) => match[1]);
    let result = sanitized;
    if (paints.length > 0 && paints.every(isAchromaticWhite)) {
      result = sanitized.replace(SVG_PAINT, (match, color) =>
        match.replace(color, DARK_ICON_INK)
      );
    }
    if (result !== svg) {
      normalized = `data:image/svg+xml;base64,${toBase64Utf8(result)}`;
    }
  } catch {
    normalized = icon;
  }

  normalizedIconCache.set(icon, normalized);
  return normalized;
}

const lightIconCache = new Map<string, boolean>();

export function isLightSvgIcon(icon?: string): boolean {
  if (!icon) return false;
  const cached = lightIconCache.get(icon);
  if (cached !== undefined) return cached;

  let isLight = false;
  if (icon.startsWith("data:image/svg+xml;base64,")) {
    try {
      const svg = atob(icon.slice(icon.indexOf(",") + 1));
      const luminances: number[] = [];
      for (const match of svg.matchAll(SVG_PAINT)) {
        const luminance = relativeLuminance(match[1]);
        if (luminance !== null) luminances.push(luminance);
      }
      isLight = luminances.length > 0 && Math.min(...luminances) > 0.6;
    } catch {
      isLight = false;
    }
  }

  lightIconCache.set(icon, isLight);
  return isLight;
}

/** Light-on-light icons get a near-black chip; dark/colored icons get a light chip. */
export function getChipFill(
  icon: string | undefined,
  isDark: boolean,
  isMeasuredLight = false
): string {
  if (isMeasuredLight || isLightSvgIcon(icon)) return PLATE_DARK;
  return isDark ? PLATE_ON_DARK : PLATE_ON_LIGHT;
}
