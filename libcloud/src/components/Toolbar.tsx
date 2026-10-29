import type { ReactNode } from "react";
import { useState } from "react";
import {
  ArrowDownWideNarrow,
  ArrowUpNarrowWide,
  Circle,
  CircleOff,
  Download,
  FileText,
  Hash,
  Image,
  ImageOff,
  Link as LinkIcon,
  Lock,
  Scale,
  SlidersHorizontal,
  Share2,
} from "lucide-react";
import type { ShareAction } from "../hooks/useShare";
import {
  PRESETS,
  PRESET_LIST,
  SIZES,
  SIZE_LIST,
  SORTS,
  type CanvasSize,
  type Preset,
  type PresetId,
  type SizeId,
  type SortId,
} from "../lib/presets";
import { Dropdown, type DropdownOption } from "./Dropdown";
import { GithubIcon } from "./GithubIcon";
import { Popover } from "./Popover";

type ToolbarProps = {
  username: string;
  token: string;
  maxCount: string;
  presetId: PresetId;
  sizeId: SizeId;
  sort: SortId;
  isLoading: boolean;
  showMissingLogos: boolean;
  transparentChips: boolean;
  onUsernameChange: (value: string) => void;
  onTokenChange: (value: string) => void;
  onMaxCountChange: (value: string) => void;
  onPresetChange: (value: PresetId) => void;
  onSizeChange: (value: SizeId) => void;
  onSortChange: (value: SortId) => void;
  onToggleMissingLogos: () => void;
  onToggleTransparentChips: () => void;
  onGenerate: () => void;
  onAbort: () => void;
  onShare: (action: ShareAction) => void;
};

const inputClass =
  "w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink placeholder:text-muted/70 outline-none transition focus:border-accent";

const fieldClass =
  "h-9 rounded-lg border border-line bg-canvas px-2.5 text-sm text-ink outline-none transition focus:border-accent";

function PresetSwatch({ preset }: { preset: Preset }) {
  return (
    <span
      className="relative flex h-4 w-4 items-center justify-center overflow-hidden rounded-[4px] border border-line"
      style={{ background: preset.tokens.canvas }}
    >
      <span
        className="h-2 w-2 rounded-full"
        style={{ background: preset.tokens.accent }}
      />
    </span>
  );
}

function SizeGlyph({ size }: { size: CanvasSize }) {
  const width = 15;
  const height = Math.max(5, Math.round((width * size.height) / size.width));
  return (
    <span className="flex h-4 w-4 items-center justify-center">
      <span
        className="rounded-[2px] border border-current"
        style={{ width, height }}
      />
    </span>
  );
}

const PRESET_OPTIONS: DropdownOption<PresetId>[] = PRESET_LIST.map((preset) => ({
  value: preset.id,
  label: preset.label,
  description: preset.description,
  icon: <PresetSwatch preset={preset} />,
}));

const SIZE_OPTIONS: DropdownOption<SizeId>[] = SIZE_LIST.map((size) => ({
  value: size.id,
  label: `${size.label} · ${size.width}×${size.height}`,
  description: `Export at ${size.width}×${size.height}`,
  icon: <SizeGlyph size={size} />,
}));

const SORT_ICONS: Record<SortId, ReactNode> = {
  "most-used": <ArrowDownWideNarrow className="h-3.5 w-3.5" />,
  "least-used": <ArrowUpNarrowWide className="h-3.5 w-3.5" />,
  balanced: <Scale className="h-3.5 w-3.5" />,
};

const SORT_OPTIONS: DropdownOption<SortId>[] = SORTS.map((sort) => ({
  value: sort.id,
  label: sort.label,
  description: sort.description,
  icon: SORT_ICONS[sort.id],
}));

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted">
          {label}
        </span>
        {hint && <span className="text-[10px] text-muted">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

export function Toolbar({
  username,
  token,
  maxCount,
  presetId,
  sizeId,
  sort,
  isLoading,
  showMissingLogos,
  transparentChips,
  onUsernameChange,
  onTokenChange,
  onMaxCountChange,
  onPresetChange,
  onSizeChange,
  onSortChange,
  onToggleMissingLogos,
  onToggleTransparentChips,
  onGenerate,
  onAbort,
  onShare,
}: ToolbarProps) {
  const [openSettings, setOpenSettings] = useState(false);
  const [openExport, setOpenExport] = useState(false);

  const closeAll = () => {
    setOpenSettings(false);
    setOpenExport(false);
  };

  const toggleSettings = () => {
    setOpenSettings(!openSettings);
    setOpenExport(false);
  };

  const toggleExport = () => {
    setOpenExport(!openExport);
    setOpenSettings(false);
  };

  const preset = PRESETS[presetId];
  const size = SIZES[sizeId];

  const runShare = (action: ShareAction) => {
    setOpenExport(false);
    onShare(action);
  };

  return (
    <section className="flex flex-col items-center gap-1.5 p-3">
      <div className="flex w-full flex-wrap items-center justify-center gap-2">
        <div className="relative flex w-56 items-center">
          <GithubIcon className="pointer-events-none absolute left-3 h-4 w-4 text-muted" />
          <input
            className={`${inputClass} h-9 pl-9`}
            placeholder="GitHub username"
            value={username}
            onChange={(e) => onUsernameChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onGenerate()}
            aria-label="GitHub username"
          />
        </div>

        <button
          type="button"
          className={`h-9 min-w-[120px] rounded-lg px-4 font-semibold shadow-sm transition cursor-pointer ${
            isLoading
              ? "bg-rose-600 text-white hover:bg-rose-500"
              : "bg-accent text-accent-ink hover:opacity-90"
          }`}
          onClick={isLoading ? onAbort : onGenerate}
        >
          {isLoading ? "Stop" : "Generate cloud"}
        </button>

        <span className="mx-1 hidden h-6 w-px bg-line sm:block" aria-hidden="true" />

        <Dropdown
          label="Preset"
          value={presetId}
          options={PRESET_OPTIONS}
          onChange={onPresetChange}
          menuWidth="w-60"
        />

        <Dropdown
          label="Size"
          value={sizeId}
          options={SIZE_OPTIONS}
          onChange={onSizeChange}
          menuWidth="w-64"
        />

        <Dropdown
          label="Sort"
          value={sort}
          options={SORT_OPTIONS}
          onChange={onSortChange}
          align="right"
          menuWidth="w-64"
        />

        <div className="relative flex items-center">
          <Hash className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-muted" />
          <input
            type="number"
            min={1}
            max={500}
            className={`${fieldClass} w-24 pl-8 text-center font-mono`}
            placeholder="100"
            title="Max logos (1–500)"
            value={maxCount}
            onChange={(e) => onMaxCountChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onGenerate()}
            aria-label="Max logos"
          />
        </div>

        <div className="flex items-center gap-2">
          <Popover
            title="Advanced"
            trigger={<SlidersHorizontal className="h-4 w-4" />}
            open={openSettings}
            onToggle={toggleSettings}
            onClose={closeAll}
            width="w-80"
          >
            <div className="space-y-4">
              <Field label="GitHub token" hint="Optional">
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                  <input
                    type="password"
                    className={`${inputClass} pl-9`}
                    placeholder="Avoids API rate limits"
                    value={token}
                    onChange={(e) => onTokenChange(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && onGenerate()}
                    aria-label="GitHub token"
                  />
                </div>
              </Field>

              <Field label="Display">
                <div className="grid grid-cols-1 gap-1.5">
                  <button
                    type="button"
                    onClick={onToggleMissingLogos}
                    className={`flex items-center justify-between rounded-md border px-2.5 py-2 text-xs transition cursor-pointer ${
                      showMissingLogos
                        ? "border-accent bg-accent/10 text-ink"
                        : "border-line bg-canvas/60 text-muted hover:text-ink"
                    }`}
                    title="Show packages that did not resolve to an icon."
                  >
                    <span className="flex items-center gap-2">
                      {showMissingLogos ? (
                        <Image className="h-4 w-4" />
                      ) : (
                        <ImageOff className="h-4 w-4" />
                      )}
                      Packages without logos
                    </span>
                    <span className="font-mono text-[10px] uppercase">
                      {showMissingLogos ? "Shown" : "Hidden"}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={onToggleTransparentChips}
                    className={`flex items-center justify-between rounded-md border px-2.5 py-2 text-xs transition cursor-pointer ${
                      transparentChips
                        ? "border-accent bg-accent/10 text-ink"
                        : "border-line bg-canvas/60 text-muted hover:text-ink"
                    }`}
                    title="Remove the plate behind each logo."
                  >
                    <span className="flex items-center gap-2">
                      {transparentChips ? (
                        <CircleOff className="h-4 w-4" />
                      ) : (
                        <Circle className="h-4 w-4" />
                      )}
                      Transparent plates
                    </span>
                    <span className="font-mono text-[10px] uppercase">
                      {transparentChips ? "On" : "Off"}
                    </span>
                  </button>
                </div>
              </Field>
            </div>
          </Popover>

          <Popover
            title="Export & share"
            trigger={<Share2 className="h-4 w-4" />}
            open={openExport}
            onToggle={toggleExport}
            onClose={closeAll}
            width="w-72"
          >
            <div className="space-y-3">
              <div className="rounded-md border border-line bg-canvas/60 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-ink">
                    {preset.label} · {size.label}
                  </p>
                  <div className="flex items-center gap-1" aria-hidden="true">
                    {[preset.tokens.canvas, preset.tokens.surface, preset.tokens.accent].map(
                      (color) => (
                        <span
                          key={color}
                          className="h-3 w-3 rounded-full border border-line"
                          style={{ background: color }}
                        />
                      )
                    )}
                  </div>
                </div>
                <p className="mt-0.5 font-mono text-[11px] text-muted">
                  {size.width}×{size.height}
                </p>
              </div>

              <button
                type="button"
                onClick={() => runShare("readme")}
                className="flex w-full items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-accent-ink transition hover:opacity-90 cursor-pointer"
              >
                <FileText className="h-4 w-4" />
                Copy README Markdown
              </button>
              <button
                type="button"
                onClick={() => runShare("link")}
                className="flex w-full items-center gap-2 rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink transition hover:border-accent/60 cursor-pointer"
              >
                <LinkIcon className="h-4 w-4" />
                Copy link
              </button>

              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => runShare("svg")}
                  className="flex items-center justify-center gap-1.5 rounded-lg border border-line bg-canvas px-2 py-2 text-xs text-ink transition hover:border-accent/60 cursor-pointer"
                >
                  <Download className="h-3.5 w-3.5" />
                  Download SVG
                </button>
                <button
                  type="button"
                  onClick={() => runShare("png")}
                  className="flex items-center justify-center gap-1.5 rounded-lg border border-line bg-canvas px-2 py-2 text-xs text-ink transition hover:border-accent/60 cursor-pointer"
                >
                  <Image className="h-3.5 w-3.5" />
                  Download PNG
                </button>
              </div>

              <div className="rounded-md border border-line bg-canvas/60 px-2.5 py-2">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">
                  README Markdown
                </p>
                <code className="block break-all font-mono text-[10px] leading-snug text-ink/80">
                  [![My Tech Stack](https://your-app/s/abc123/cloud.svg)](https://your-app/s/abc123)
                </code>
              </div>

              <p className="text-[10px] leading-snug text-muted">
                Copy link and README create a snapshot of this cloud. Downloads use the
                selected preset and size.
              </p>
            </div>
          </Popover>
        </div>
      </div>
    </section>
  );
}
