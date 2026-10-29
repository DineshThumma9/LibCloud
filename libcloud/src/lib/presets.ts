export type PresetId = "paper" | "ink" | "graph" | "techy" | "space";
export type SizeId = "web" | "readme" | "social";
export type SortId = "most-used" | "least-used" | "balanced";

export type ThemeTokens = {
  canvas: string;
  surface: string;
  line: string;
  ink: string;
  muted: string;
  accent: string;
  accentInk: string;
};

export type PresetLayout = {
  charge: number;
  xStrength: number;
  yStrength: number;
  /** 0 disables snapping. */
  grid: number;
  radial: boolean;
  hubBias: boolean;
};

export type Preset = {
  id: PresetId;
  label: string;
  description: string;
  dark: boolean;
  tokens: ThemeTokens;
  layout: PresetLayout;
  decorations: "dots" | "none" | "edges" | "techy" | "stars";
  shadowOpacity: number;
};

export type CanvasSize = {
  id: SizeId;
  label: string;
  width: number;
  height: number;
};

export const PRESETS: Record<PresetId, Preset> = {
  paper: {
    id: "paper",
    label: "Paper",
    description: "Warm light canvas with an ink-and-rust palette. Safest for README cards.",
    dark: false,
    tokens: {
      canvas: "#f7f3ea",
      surface: "#fffdf7",
      line: "#d8d2c4",
      ink: "#1c1917",
      muted: "#78716c",
      accent: "#c2410c",
      accentInk: "#fff7ed",
    },
    layout: { charge: -8, xStrength: 0.07, yStrength: 0.07, grid: 0, radial: false, hubBias: false },
    decorations: "dots",
    shadowOpacity: 0.14,
  },
  ink: {
    id: "ink",
    label: "Ink",
    description: "Near-black canvas with high contrast and an acid-lime accent.",
    dark: true,
    tokens: {
      canvas: "#0c0d0f",
      surface: "#14161a",
      line: "#262a31",
      ink: "#e7e5e4",
      muted: "#8b8f98",
      accent: "#d7ff3f",
      accentInk: "#11130a",
    },
    layout: { charge: -8, xStrength: 0.07, yStrength: 0.07, grid: 0, radial: false, hubBias: false },
    decorations: "none",
    shadowOpacity: 0.3,
  },
  graph: {
    id: "graph",
    label: "Graph",
    description: "A technology network: hub-biased layout with curved links between nearby logos.",
    dark: true,
    tokens: {
      canvas: "#0b1220",
      surface: "#101a2e",
      line: "#233250",
      ink: "#e2e8f0",
      muted: "#8190aa",
      accent: "#34d399",
      accentInk: "#06251b",
    },
    layout: { charge: -10, xStrength: 0.06, yStrength: 0.06, grid: 0, radial: false, hubBias: true },
    decorations: "edges",
    shadowOpacity: 0.28,
  },
  techy: {
    id: "techy",
    label: "Techy",
    description: "Loose grid-snapped cloud with corner brackets, ticks, and a terminal feel.",
    dark: true,
    tokens: {
      canvas: "#0f1211",
      surface: "#171b19",
      line: "#2c342f",
      ink: "#dbe4dd",
      muted: "#839089",
      accent: "#f5a524",
      accentInk: "#1a1205",
    },
    layout: { charge: -9, xStrength: 0.08, yStrength: 0.08, grid: 20, radial: false, hubBias: false },
    decorations: "techy",
    shadowOpacity: 0.24,
  },
  space: {
    id: "space",
    label: "Space",
    description: "Orbit-biased radial cloud with sparse stars and faint orbit rings.",
    dark: true,
    tokens: {
      canvas: "#0a0f24",
      surface: "#111a35",
      line: "#253154",
      ink: "#e6e9f5",
      muted: "#8a93b5",
      accent: "#a78bfa",
      accentInk: "#150d2b",
    },
    layout: { charge: -8, xStrength: 0.03, yStrength: 0.03, grid: 0, radial: true, hubBias: false },
    decorations: "stars",
    shadowOpacity: 0.32,
  },
};

export const PRESET_LIST = Object.values(PRESETS);

export const SIZES: Record<SizeId, CanvasSize> = {
  web: { id: "web", label: "Web", width: 1400, height: 900 },
  readme: { id: "readme", label: "README card", width: 920, height: 540 },
  social: { id: "social", label: "Social", width: 1200, height: 630 },
};

export const SIZE_LIST = Object.values(SIZES);

export const SORTS: { id: SortId; label: string; description: string }[] = [
  {
    id: "most-used",
    label: "Most used first",
    description: "The most common technologies get the larger logos.",
  },
  {
    id: "least-used",
    label: "Least used first",
    description: "Rarer technologies get the larger logos so niche picks stand out.",
  },
  {
    id: "balanced",
    label: "Balanced",
    description: "Spreads sizes more evenly so smaller but distinctive tools do not disappear.",
  },
];

export function presetCssVars(preset: Preset): Record<string, string> {
  return {
    "--canvas": preset.tokens.canvas,
    "--surface": preset.tokens.surface,
    "--line": preset.tokens.line,
    "--ink": preset.tokens.ink,
    "--muted": preset.tokens.muted,
    "--accent": preset.tokens.accent,
    "--accent-ink": preset.tokens.accentInk,
  };
}
