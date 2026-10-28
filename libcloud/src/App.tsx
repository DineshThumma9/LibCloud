import { useEffect, useState, useRef, useMemo } from 'react'
import './App.css'
import { ArrowDownWideNarrow, Palette, Share2, Hash, Lock, Sun, Moon, Image, ImageOff, Circle, CircleOff } from 'lucide-react'
import { toast, Toaster } from 'sonner'
import { startLibCloudStream, createShare } from './api'
import { useCloudStore } from './state'
import { useForceLayout, getLogoRadius } from './useForceLayout'
import { useLogoMotion } from './useLogoMotion'

export function GithubIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

async function svgToPngDataUrl(svg: string): Promise<string> {
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
    canvas.width = 1600;
    canvas.height = 900;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas is not supported");
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } finally {
    URL.revokeObjectURL(url);
  }
}

const HEX_COLOR = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
const SVG_PAINT = /(?:fill|stroke|stop-color|color)\s*[:=]\s*["']?\s*(#[0-9a-fA-F]{3,6}|rgba?\([^)]*\)|white|black|currentColor)/gi;
const DARK_ICON_INK = "#0f172a";
const PLATE_ON_DARK = "#f1f5f9";
const PLATE_ON_LIGHT = "#ffffff";
const PLATE_DARK = "#111827";

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
function normalizeIcon(icon?: string): string | undefined {
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

function isLightSvgIcon(icon?: string): boolean {
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
function getChipFill(
  icon: string | undefined,
  isDark: boolean,
  isMeasuredLight = false
): string {
  if (isMeasuredLight || isLightSvgIcon(icon)) return PLATE_DARK;
  return isDark ? PLATE_ON_DARK : PLATE_ON_LIGHT;
}

type IconAppearance = { isLight: boolean; isBlank: boolean };

function setsEqual(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const value of a) {
    if (!b.has(value)) return false;
  }
  return true;
}

const measuredIconCache = new Map<string, IconAppearance>();
const measuredIconPromises = new Map<string, Promise<IconAppearance>>();

/**
 * Sample an icon's rendered pixels. Mostly-white marks (including raster
 * PNG/JPEG/ICO logos) need a dark chip so they do not disappear into the
 * light one. Icons that render nothing (empty clip paths, sprite sheets,
 * broken SVG) are flagged as blank so the UI can show an initial instead.
 * Results are cached per data URI.
 */
function measureIconAppearance(icon: string): Promise<IconAppearance> {
  const cached = measuredIconCache.get(icon);
  if (cached !== undefined) return Promise.resolve(cached);
  const inFlight = measuredIconPromises.get(icon);
  if (inFlight) return inFlight;

  const promise = new Promise<IconAppearance>((resolve) => {
    const image = document.createElement("img");
    image.onload = () => {
      try {
        const size = 32;
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        if (!ctx) return resolve({ isLight: false, isBlank: false });
        ctx.drawImage(image, 0, 0, size, size);
        const data = ctx.getImageData(0, 0, size, size).data;
        let visible = 0;
        let dark = 0;
        let pale = 0;
        let saturated = 0;
        let luminanceSum = 0;
        for (let i = 0; i < data.length; i += 4) {
          if (data[i + 3] < 32) continue;
          visible++;
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];
          const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
          luminanceSum += luminance;
          if (luminance < 60) dark++;
          if (luminance > 200) pale++;
          if (Math.max(r, g, b) - Math.min(r, g, b) > 30) saturated++;
        }
        if (visible < 20) {
          const blank = { isLight: false, isBlank: true };
          measuredIconCache.set(icon, blank);
          return resolve(blank);
        }
        const average = luminanceSum / visible;
        const isLight =
          (dark / visible < 0.12 && average >= 170) ||
          (pale / visible > 0.6 && dark / visible < 0.2) ||
          (saturated / visible < 0.2 && average > 130 && dark / visible < 0.05);
        const appearance = { isLight, isBlank: false };
        measuredIconCache.set(icon, appearance);
        resolve(appearance);
      } catch {
        resolve({ isLight: false, isBlank: false });
      }
    };
    image.onerror = () => {
      const blank = { isLight: false, isBlank: true };
      measuredIconCache.set(icon, blank);
      resolve(blank);
    };
    image.src = icon;
  }).finally(() => {
    measuredIconPromises.delete(icon);
  });

  measuredIconPromises.set(icon, promise);
  return promise;
}

function App() {
  const [maxCount, setMaxCount] = useState<string>("");
  const [username, setUsername] = useState<string>("");
  const [order, setOrder] = useState<string>("max-frequency");
  const [shareVia, setShareVia] = useState<string>("");
  const [theme, setTheme] = useState<string>("Minimal");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [statusText, setStatusText] = useState<string>("");
  const [isDark, setIsDark] = useState<boolean>(true);
  const [showMissingLogos, setShowMissingLogos] = useState<boolean>(false);
  const [transparentChips, setTransparentChips] = useState<boolean>(false);

  // Dropdown open states
  const [openOrder, setOpenOrder] = useState<boolean>(false);
  const [openTheme, setOpenTheme] = useState<boolean>(false);
  const [openShare, setOpenShare] = useState<boolean>(false);
  const [token, setToken] = useState<string>("");

  const logosMap = useCloudStore((s) => s.logos);
  const logos = useMemo(() => Array.from(logosMap.values()), [logosMap]);
  const resetStore = useCloudStore((s) => s.reset);
  const abortControllerRef = useRef<AbortController | null>(null);
  const graphRef = useRef<SVGSVGElement | null>(null);
  const tooltipRef = useRef<SVGGElement | null>(null);
  const tooltipRectRef = useRef<SVGRectElement | null>(null);
  const tooltipTextRef = useRef<SVGTextElement | null>(null);

  const visibleLogos = useMemo(() => {
    if (showMissingLogos) return logos;
    return logos.filter((l) => Boolean(l.icon));
  }, [logos, showMissingLogos]);

  const renderedIcons = useMemo(() => {
    const icons = new Map<string, string>();
    for (const logo of visibleLogos) {
      if (logo.icon) icons.set(logo.id, normalizeIcon(logo.icon) ?? logo.icon);
    }
    return icons;
  }, [visibleLogos]);

  const [measuredLightIds, setMeasuredLightIds] = useState<Set<string>>(
    () => new Set()
  );
  const [blankIconIds, setBlankIconIds] = useState<Set<string>>(
    () => new Set()
  );

  useEffect(() => {
    let cancelled = false;
    const entries: { id: string; icon: string }[] = [];
    for (const logo of visibleLogos) {
      const icon = renderedIcons.get(logo.id) ?? logo.icon;
      if (icon) entries.push({ id: logo.id, icon });
    }
    if (entries.length === 0) return;

    (async () => {
      const lightIds = new Set<string>();
      const blankIds = new Set<string>();
      await Promise.all(
        entries.map(async ({ id, icon }) => {
          const appearance = await measureIconAppearance(icon);
          if (appearance.isLight) lightIds.add(id);
          if (appearance.isBlank) blankIds.add(id);
        })
      );
      if (!cancelled) {
        setMeasuredLightIds((previous) =>
          setsEqual(previous, lightIds) ? previous : lightIds
        );
        setBlankIconIds((previous) =>
          setsEqual(previous, blankIds) ? previous : blankIds
        );
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [visibleLogos, renderedIcons]);

  const chipFills = useMemo(() => {
    const fills = new Map<string, string>();
    for (const logo of visibleLogos) {
      fills.set(
        logo.id,
        getChipFill(
          renderedIcons.get(logo.id),
          isDark,
          measuredLightIds.has(logo.id)
        )
      );
    }
    return fills;
  }, [visibleLogos, renderedIcons, isDark, measuredLightIds]);

  const { setNodeRef } = useForceLayout(visibleLogos, { width: 1600, height: 900 });
  const { setMotionRef, handlePointerEnter, handlePointerLeave } = useLogoMotion(visibleLogos);

  const counts = useMemo(() => visibleLogos.map((l) => l.count), [visibleLogos]);
  const minC = counts.length ? Math.min(...counts) : 1;
  const maxC = counts.length ? Math.max(...counts) : 1;

  const getRadius = (count: number) =>
    getLogoRadius(count, minC, maxC, visibleLogos.length);

  /**
   * One tooltip for the whole cloud, painted after every node so it is never
   * covered by a neighbouring chip. Position is read from D3's transform.
   */
  const showTooltip = (
    node: SVGGElement,
    name: string,
    count: number,
    radius: number
  ) => {
    const tip = tooltipRef.current;
    const rect = tooltipRectRef.current;
    const text = tooltipTextRef.current;
    if (!tip || !rect || !text) return;

    const match = /translate\(([-\d.]+),\s*([-\d.]+)\)/.exec(
      node.getAttribute("transform") || ""
    );
    const x = match ? Number(match[1]) : 0;
    const y = match ? Number(match[2]) : 0;

    text.textContent = `${name} (×${count})`;
    const width = Math.max(Math.ceil(text.getComputedTextLength()) + 22, 68);
    const height = 27;
    const gap = 10;

    const aboveTop = y - radius - gap - height;
    const belowTop = y + radius + gap;
    let rectY: number;
    if (aboveTop >= 4) {
      rectY = -radius - gap - height;
    } else if (belowTop + height <= 896) {
      rectY = radius + gap;
    } else {
      rectY = Math.max(4 - y, Math.min(896 - height - y, aboveTop));
    }

    const clampedX = Math.max(
      width / 2 + 4,
      Math.min(1600 - width / 2 - 4, x)
    );

    tip.setAttribute("transform", `translate(${clampedX}, ${y})`);
    rect.setAttribute("x", String(-width / 2));
    rect.setAttribute("y", String(rectY));
    rect.setAttribute("width", String(width));
    rect.setAttribute("height", String(height));
    text.setAttribute("x", "0");
    text.setAttribute("y", String(rectY + height / 2));
    tip.dataset.visible = "true";
  };

  const hideTooltip = () => {
    if (tooltipRef.current) tooltipRef.current.dataset.visible = "false";
  };

  const orderOptions = [
    { label: "Max frequency", value: "max-frequency" },
    { label: "Min frequency", value: "min-frequency" },
    { label: "tf-idf", value: "tf-idf" },
  ];

  const themeOptions = ["Minimal", "Futuristic", "ReadME", "Neon"];
  const shareOptions = [
    { label: "Share Via Link", value: "link" },
    { label: "Embed in ReadMe", value: "readme" },
    { label: "Image for Portfolio", value: "portfolio" },
    { label: "Share in Social Media", value: "social" },
  ];

  const closeAllDropdowns = () => {
    setOpenOrder(false);
    setOpenTheme(false);
    setOpenShare(false);
  };

  const getSvgString = () => {
    if (graphRef.current) {
      const clone = graphRef.current.cloneNode(true) as SVGSVGElement;
      clone.setAttribute("width", "1600");
      clone.setAttribute("height", "900");
      const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      bgRect.setAttribute("width", "100%");
      bgRect.setAttribute("height", "100%");
      bgRect.setAttribute("fill", isDark ? "#090d16" : "#ffffff");
      clone.insertBefore(bgRect, clone.firstChild);
      return new XMLSerializer().serializeToString(clone);
    }
    return '';
  };

  const handleShareOption = async (option: string) => {
    setShareVia(option);
    setOpenShare(false);

    if (visibleLogos.length === 0) {
      toast.error("No logos to share yet", {
        description: "Generate your cloud first before sharing.",
      });
      return;
    }

    const svg = getSvgString();

    if (option === 'portfolio') {
      const blob = new Blob([svg], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `libcloud-${username || 'stack'}.svg`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Downloaded SVG for portfolio!");
      return;
    }

    try {
      toast.loading("Generating share link...", { id: "share-toast" });
      let pngBase64 = "";
      try {
        pngBase64 = await svgToPngDataUrl(svg);
      } catch (e) {
        console.warn("Could not rasterize cloud image for social preview:", e);
      }
      const res = await createShare({
        username: username.trim() || 'user',
        svg_data: svg,
        png_base64: pngBase64,
        title: `@${username}'s Tech Stack`,
      });

      if (option === 'readme') {
        await navigator.clipboard.writeText(res.markdown);
        toast.success("Copied README Markdown!", {
          id: "share-toast",
          description: "Paste it directly into your GitHub README.md",
        });
      } else {
        await navigator.clipboard.writeText(res.page_url);
        toast.success("Copied share link to clipboard!", {
          id: "share-toast",
          description: res.page_url,
        });
      }
    } catch (e: any) {
      toast.error("Failed to share", {
        id: "share-toast",
        description: e.message || "Could not save share",
      });
    }
  };

  const abortStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  };

  const handleGenerate = () => {
    if (!username.trim()) {
      alert("Please enter a valid GitHub username");
      return;
    }
    const count = maxCount.trim() === "" ? 100 : parseInt(maxCount, 10);
    if (isNaN(count) || count < 1 || count > 500) {
      alert("Please enter a valid max icons number (between 1 and 500)");
      return;
    }
    streamResponse();
  };

  useEffect(() => {
    return () => {
      abortStream();
    };
  }, []);

  const streamResponse = async () => {
    abortStream();
    resetStore();

    abortControllerRef.current = new AbortController();
    setIsLoading(true);
    setStatusText("Connecting to server...");

    try {
      const maxLogos = maxCount.trim() === "" ? 100 : parseInt(maxCount, 10);
      await startLibCloudStream(
        {
          username: username.trim(),
          max_logos: maxLogos,
          order_by: order,
          theme,
          token: token.trim() || undefined,
        },
        {
          signal: abortControllerRef.current.signal,
          onStatusChange: (text) => setStatusText(text),
          onEvent: (type, data) => useCloudStore.getState().handleEvent(type, data),
          onError: (err) => {
            setIsLoading(false);
            toast.error("Stream Error", {
              description: err.message || "Pipeline error occurred",
            });
          },
          onDone: () => {
            setIsLoading(false);
          },
        }
      );
    } catch (e: any) {
      if (e?.name === "AbortError") {
        setStatusText("Stream cancelled");
      } else {
        console.error("Stream error:", e);
        setStatusText(`Connection failed: ${e?.message || e}`);
        toast.error("Stream connection failed", {
          description: e?.message || "Could not reach backend",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`min-h-screen transition-colors duration-200 flex flex-col ${isDark ? 'bg-[#090d16] text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      <Toaster richColors position="top-right" theme={isDark ? "dark" : "light"} />

      <section className="mt-4 flex flex-col m-2 p-4 justify-center items-center">
        <div className="flex flex-wrap justify-center items-center gap-3">
          {/* username input */}
          <div className="relative flex items-center">
            <GithubIcon className={`absolute left-3 w-4 h-4 pointer-events-none ${isDark ? 'text-slate-400' : 'text-black'}`} />
            <input
              className={`pl-9 pr-3 py-2 border-2 rounded-lg text-sm transition outline-none ${
                isDark
                  ? 'border-slate-700 bg-slate-900/90 text-white placeholder-slate-500 focus:border-sky-500'
                  : 'border-black bg-white text-black placeholder-zinc-400 focus:border-zinc-700'
              }`}
              placeholder="Enter username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            />
          </div> 
          
          {/* token input */}
          <div className="relative flex items-center">
            <Lock className={`absolute left-3 w-4 h-4 pointer-events-none ${isDark ? 'text-slate-400' : 'text-black'}`} />
            <input
              type="password"
              className={`pl-9 pr-3 py-2 border-2 rounded-lg text-sm transition outline-none ${
                isDark
                  ? 'border-slate-700 bg-slate-900/90 text-white placeholder-slate-500 focus:border-sky-500'
                  : 'border-black bg-white text-black placeholder-zinc-400 focus:border-zinc-700'
              }`}
              placeholder="Enter token (optional)"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            />
          </div>

          {/* max-icons input */}
          <div className="relative flex items-center">
            <Hash className={`absolute left-2.5 w-4 h-4 pointer-events-none ${isDark ? 'text-slate-400' : 'text-black'}`} />
            <input
              className={`pl-8 pr-2 py-2 border-2 rounded-lg text-sm transition text-center w-20 outline-none ${
                isDark
                  ? 'border-slate-700 bg-slate-900/90 text-white placeholder-slate-500 focus:border-sky-500'
                  : 'border-black bg-white text-black placeholder-zinc-400 focus:border-zinc-700'
              }`}
              placeholder="100"
              value={maxCount}
              onChange={(e) => setMaxCount(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            />
          </div>

          {/* order by dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setOpenOrder(!openOrder);
                setOpenTheme(false);
                setOpenShare(false);
              }}
              className={`flex items-center justify-center w-10 h-10 border-2 rounded-lg transition cursor-pointer ${
                isDark
                  ? 'border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800'
                  : 'border-black bg-white text-black hover:bg-zinc-100'
              }`}
              title={`Order: ${orderOptions.find((o) => o.value === order)?.label || order}`}
            >
              <ArrowDownWideNarrow className="w-4 h-4" />
            </button>

            {openOrder && (
              <>
                <div className="fixed inset-0 z-10" onClick={closeAllDropdowns} />
                <div
                  className={`absolute left-0 top-full mt-2.5 w-40 border-2 rounded-lg shadow-2xl z-20 py-1 ${
                    isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-black text-black'
                  }`}
                >
                  {orderOptions.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`w-full text-left px-3 py-1.5 text-sm transition cursor-pointer flex items-center justify-between ${
                        isDark ? 'hover:bg-slate-800' : 'hover:bg-zinc-100'
                      } ${order === opt.value ? (isDark ? "font-bold bg-slate-800/60" : "font-bold bg-zinc-50") : ""}`}
                      onClick={() => {
                        setOrder(opt.value);
                        setOpenOrder(false);
                      }}
                    >
                      {opt.label}
                      {order === opt.value && <span className="text-xs">✓</span>}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* theme dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setOpenTheme(!openTheme);
                setOpenOrder(false);
                setOpenShare(false);
              }}
              className={`flex items-center justify-center w-10 h-10 border-2 rounded-lg transition cursor-pointer ${
                isDark
                  ? 'border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800'
                  : 'border-black bg-white text-black hover:bg-zinc-100'
              }`}
              title={`Theme: ${theme}`}
            >
              <Palette className="w-4 h-4" />
            </button>

            {openTheme && (
              <>
                <div className="fixed inset-0 z-10" onClick={closeAllDropdowns} />
                <div
                  className={`absolute left-0 top-full mt-2.5 w-36 border-2 rounded-lg shadow-2xl z-20 py-1 ${
                    isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-black text-black'
                  }`}
                >
                  {themeOptions.map((t) => (
                    <button
                      key={t}
                      type="button"
                      className={`w-full text-left px-3 py-1.5 text-sm transition cursor-pointer flex items-center justify-between ${
                        isDark ? 'hover:bg-slate-800' : 'hover:bg-zinc-100'
                      } ${theme === t ? (isDark ? "font-bold bg-slate-800/60" : "font-bold bg-zinc-50") : ""}`}
                      onClick={() => {
                        setTheme(t);
                        setOpenTheme(false);
                      }}
                    >
                      {t}
                      {theme === t && <span className="text-xs">✓</span>}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* share dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setOpenShare(!openShare);
                setOpenOrder(false);
                setOpenTheme(false);
              }}
              className={`flex items-center justify-center w-10 h-10 border-2 rounded-lg transition cursor-pointer ${
                isDark
                  ? 'border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800'
                  : 'border-black bg-white text-black hover:bg-zinc-100'
              }`}
              title={`Share: ${shareVia || 'Choose option'}`}
            >
              <Share2 className="w-4 h-4" />
            </button>

            {openShare && (
              <>
                <div className="fixed inset-0 z-10" onClick={closeAllDropdowns} />
                <div
                  className={`absolute right-0 top-full mt-2.5 w-52 border-2 rounded-lg shadow-2xl z-20 py-1 ${
                    isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-black text-black'
                  }`}
                >
                  {shareOptions.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`w-full text-left px-3 py-1.5 text-sm transition cursor-pointer flex items-center justify-between ${
                        isDark ? 'hover:bg-slate-800' : 'hover:bg-zinc-100'
                      } ${shareVia === opt.value ? (isDark ? "font-bold bg-slate-800/60" : "font-bold bg-zinc-50") : ""}`}
                      onClick={() => {
                        handleShareOption(opt.value);
                      }}
                    >
                      {opt.label}
                      {shareVia === opt.value && <span className="text-xs">✓</span>}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Toggle packages without logos (Default: false) */}
          <button
            type="button"
            onClick={() => setShowMissingLogos(!showMissingLogos)}
            className={`flex items-center justify-center w-10 h-10 border-2 rounded-lg transition cursor-pointer ${
              showMissingLogos
                ? isDark
                  ? 'border-sky-500 bg-sky-500/20 text-sky-400'
                  : 'border-black bg-zinc-200 text-black font-semibold'
                : isDark
                ? 'border-slate-700 bg-slate-900 text-slate-400 hover:bg-slate-800'
                : 'border-black bg-white text-zinc-400 hover:bg-zinc-100'
            }`}
            title={
              showMissingLogos
                ? "Showing all packages (including text-only). Click to hide packages without logos."
                : "Hiding packages without logos (showing logos only). Click to show all packages."
            }
          >
            {showMissingLogos ? <Image className="w-4 h-4" /> : <ImageOff className="w-4 h-4" />}
          </button>

          {/* Transparent chips experiment toggle */}
          <button
            type="button"
            onClick={() => setTransparentChips(!transparentChips)}
            className={`flex items-center justify-center w-10 h-10 border-2 rounded-lg transition cursor-pointer ${
              transparentChips
                ? isDark
                  ? 'border-sky-500 bg-sky-500/20 text-sky-400'
                  : 'border-black bg-zinc-200 text-black font-semibold'
                : isDark
                ? 'border-slate-700 bg-slate-900 text-slate-400 hover:bg-slate-800'
                : 'border-black bg-white text-zinc-400 hover:bg-zinc-100'
            }`}
            title={
              transparentChips
                ? "Chips are transparent (experiment). Click to restore solid plates."
                : "Solid chips are on. Click to make chips transparent (experiment)."
            }
          >
            {transparentChips ? <CircleOff className="w-4 h-4" /> : <Circle className="w-4 h-4" />}
          </button>

          {/* Dark / Light Mode Toggle Button */}
          <button
            type="button"
            onClick={() => setIsDark(!isDark)}
            className={`flex items-center justify-center w-10 h-10 border-2 rounded-lg transition cursor-pointer ${
              isDark
                ? 'border-slate-700 bg-slate-900 text-amber-400 hover:bg-slate-800'
                : 'border-black bg-white text-slate-700 hover:bg-zinc-100'
            }`}
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* generate / stop button */}
          <button
            type="button"
            className={`px-4 py-2 rounded-lg transition cursor-pointer font-medium min-w-[90px] shadow-sm ${
              isLoading
                ? 'bg-rose-500 hover:bg-rose-600 text-white'
                : isDark
                ? 'bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold'
                : 'bg-black text-white hover:bg-zinc-800'
            }`}
            onClick={isLoading ? abortStream : handleGenerate}
          >
            {isLoading ? "Stop" : "Generate"}
          </button>
        </div>
      </section>

      {/* Full-bleed Logos Viewport */}
      <div className="relative flex-grow w-full h-[calc(100vh-130px)] overflow-hidden flex items-center justify-center">
        {visibleLogos.length === 0 ? (
          isLoading && statusText ? (
            /* Sharp, cohesive status box in center while initially scanning */
            <div
              className={`px-6 py-3.5 border shadow-sm flex items-center gap-3 select-none ${
                isDark
                  ? 'bg-slate-900/90 border-slate-800 text-slate-300'
                  : 'bg-white border-zinc-200 text-zinc-700'
              }`}
              style={{ borderRadius: '0px' }}
            >
              <span className={`inline-block w-2 h-2 rounded-none animate-pulse ${isDark ? 'bg-slate-400' : 'bg-zinc-500'}`} />
              <span className="text-xs font-mono tracking-tight">{statusText}</span>
            </div>
          ) : (
            /* Empty state prompt */
            <div className={`text-xs font-mono flex flex-col items-center gap-2 select-none ${isDark ? 'text-slate-600' : 'text-zinc-400'}`}>
              <span className="text-3xl opacity-20">☁️</span>
              <span>Enter a GitHub username above to build your cloud</span>
            </div>
          )
        ) : (
          <>
            <svg
              ref={graphRef}
              viewBox="0 0 1600 900"
              className="w-full h-full select-none"
              style={{ display: "block" }}
            >
              <defs>
                <filter id="logo-shadow" x="-30%" y="-30%" width="160%" height="160%">
                  <feDropShadow dx="0" dy="4" stdDeviation="5" floodOpacity={isDark ? "0.3" : "0.15"} />
                </filter>
              </defs>

              <style>{`
                .logo-node { cursor: pointer; }
                .cloud-tip-layer { opacity: 0; pointer-events: none; transition: opacity 0.12s ease; }
                .cloud-tip-layer[data-visible="true"] { opacity: 1; }
              `}</style>

              {visibleLogos.map((item) => {
                const radius = getRadius(item.count);
                const imgSize = radius * 1.35;
                const icon = renderedIcons.get(item.id) ?? item.icon;
                const iconIsBlank = blankIconIds.has(item.id);
                const chipFill = transparentChips
                  ? "transparent"
                  : chipFills.get(item.id) ??
                    (isDark ? PLATE_ON_DARK : PLATE_ON_LIGHT);
                const darkChip = !transparentChips && chipFill === PLATE_DARK;

                return (
                  /* OUTER GROUP: D3 owns translate(x, y) */
                  <g
                    key={item.id}
                    ref={(el) => setNodeRef(item.id, el)}
                    className="logo-node"
                    onPointerEnter={(event) => {
                      handlePointerEnter(item.id);
                      showTooltip(event.currentTarget, item.name, item.count, radius);
                    }}
                    onPointerLeave={() => {
                      handlePointerLeave(item.id);
                      hideTooltip();
                    }}
                  >
                    {/* INNER GROUP: GSAP owns entrance & hover scale/opacity */}
                    <g
                      ref={(el) => setMotionRef(item.id, el)}
                      className="logo-motion"
                      style={{ transformOrigin: "0 0" }}
                    >
                      {/* Circular Badge Centered at (0, 0) */}
                      <circle
                        cx={0}
                        cy={0}
                        r={radius}
                        fill={chipFill}
                        stroke={
                          transparentChips
                            ? "transparent"
                            : darkChip
                            ? "#64748b"
                            : isDark
                            ? "#38bdf833"
                            : "#e2e8f0"
                        }
                        strokeWidth={transparentChips ? 0 : isDark ? 2.5 : 2}
                        filter="url(#logo-shadow)"
                      />

                      {/* Logo Image or Fallback Letter */}
                      {icon && !iconIsBlank ? (
                        <image
                          href={icon}
                          x={-imgSize / 2}
                          y={-imgSize / 2}
                          width={imgSize}
                          height={imgSize}
                          preserveAspectRatio="xMidYMid meet"
                        >
                          <title>{item.name}</title>
                        </image>
                      ) : (
                        <text
                          x={0}
                          y={radius * 0.28}
                          fontFamily="system-ui, -apple-system, sans-serif"
                          fontWeight="bold"
                          fontSize={radius * 0.72}
                          textAnchor="middle"
                          fill={
                            transparentChips
                              ? isDark
                                ? "#e2e8f0"
                                : "#334155"
                              : darkChip
                              ? "#f8fafc"
                              : "#64748b"
                          }
                        >
                          {item.name[0]?.toUpperCase() || "?"}
                        </text>
                      )}
                    </g>
                  </g>
                );
              })}

              {/* Global hover label — always painted above every logo node */}
              <g
                ref={tooltipRef}
                className="cloud-tip-layer"
                data-visible="false"
              >
                <rect
                  ref={tooltipRectRef}
                  rx={7}
                  fill="#0f172a"
                  stroke="#38bdf8"
                  strokeWidth={1.3}
                  filter="url(#logo-shadow)"
                />
                <text
                  ref={tooltipTextRef}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#ffffff"
                  fontSize={13}
                  fontFamily="system-ui, -apple-system, sans-serif"
                  fontWeight={600}
                />
              </g>
            </svg>

            {/* Quiet, sharp bottom status badge while remaining stream is completing */}
            {isLoading && statusText && (
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
                <div
                  className={`px-4 py-2 border shadow-md flex items-center gap-2.5 backdrop-blur-md ${
                    isDark
                      ? 'bg-slate-900/90 border-slate-800 text-slate-300'
                      : 'bg-white/90 border-zinc-200 text-zinc-700'
                  }`}
                  style={{ borderRadius: '0px' }}
                >
                  <span className={`inline-block w-1.5 h-1.5 rounded-none animate-pulse ${isDark ? 'bg-slate-400' : 'bg-zinc-500'}`} />
                  <span className="text-xs font-mono tracking-tight">{statusText}</span>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <section id="spacer" className="border-t border-slate-800/40"></section>
    </div>
  );
}

export default App;
