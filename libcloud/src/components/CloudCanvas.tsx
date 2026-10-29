import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, RefObject } from "react";
import { Cloud } from "lucide-react";
import { PLATE_ON_DARK, PLATE_ON_LIGHT } from "../lib/color";
import {
  presetCssVars,
  type CanvasSize,
  type Preset,
  type SortId,
} from "../lib/presets";
import type { Logo } from "../schemas";
import { getLogoRadius, useForceLayout, type SimNode } from "../useForceLayout";
import { useLogoMotion } from "../useLogoMotion";
import { CloudTooltip } from "./CloudTooltip";
import { LogoNode } from "./LogoNode";
import { StatusBadge } from "./StatusBadge";

type CloudCanvasProps = {
  logos: Logo[];
  renderedIcons: Map<string, string>;
  blankIconIds: Set<string>;
  chipFills: Map<string, string>;
  preset: Preset;
  size: CanvasSize;
  sort: SortId;
  transparentChips: boolean;
  isLoading: boolean;
  statusText: string;
  seed: string;
  graphRef: RefObject<SVGSVGElement | null>;
};

type Edge = { key: string; a: string; b: string };

function edgeKey(a: string, b: string) {
  return a < b ? `${a}|${b}` : `${b}|${a}`;
}

/** Connect each logo to its two nearest neighbours, capped at 3 links each. */
function buildEdges(nodes: SimNode[]): Edge[] {
  const positioned = nodes.filter(
    (node) => typeof node.x === "number" && typeof node.y === "number"
  );
  if (positioned.length < 2) return [];

  const degree = new Map<string, number>();
  const seen = new Set<string>();
  const edges: Edge[] = [];

  for (const node of positioned) {
    const nearest = positioned
      .filter((other) => other.id !== node.id)
      .sort(
        (a, b) =>
          Math.hypot((node.x ?? 0) - (a.x ?? 0), (node.y ?? 0) - (a.y ?? 0)) -
          Math.hypot((node.x ?? 0) - (b.x ?? 0), (node.y ?? 0) - (b.y ?? 0))
      )
      .slice(0, 2);

    for (const other of nearest) {
      const key = edgeKey(node.id, other.id);
      if (seen.has(key)) continue;
      if ((degree.get(node.id) ?? 0) >= 3 || (degree.get(other.id) ?? 0) >= 3) {
        continue;
      }
      seen.add(key);
      degree.set(node.id, (degree.get(node.id) ?? 0) + 1);
      degree.set(other.id, (degree.get(other.id) ?? 0) + 1);
      edges.push({ key, a: node.id, b: other.id });
    }
  }

  return edges;
}

function hashSeed(value: string): number {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function SpaceDecor({ width, height, seed }: { width: number; height: number; seed: string }) {
  const stars = useMemo(() => {
    const random = mulberry32(hashSeed(seed));
    return Array.from({ length: 70 }, () => ({
      x: random() * width,
      y: random() * height,
      r: 0.6 + random() * 1.2,
      opacity: 0.15 + random() * 0.45,
    }));
  }, [width, height, seed]);

  const radius = Math.min(width, height);

  return (
    <g aria-hidden="true">
      {stars.map((star, index) => (
        <circle
          key={index}
          cx={star.x}
          cy={star.y}
          r={star.r}
          fill="var(--ink)"
          opacity={star.opacity}
        />
      ))}
      <circle
        cx={width / 2}
        cy={height / 2}
        r={radius * 0.28}
        fill="none"
        stroke="var(--line)"
        strokeWidth={1}
        opacity={0.5}
      />
      <circle
        cx={width / 2}
        cy={height / 2}
        r={radius * 0.42}
        fill="none"
        stroke="var(--line)"
        strokeWidth={1}
        opacity={0.3}
      />
    </g>
  );
}

function TechyDecor({ width, height }: { width: number; height: number }) {
  const inset = 22;
  const arm = 30;
  const brackets = [
    `M ${inset} ${inset + arm} V ${inset} H ${inset + arm}`,
    `M ${width - inset - arm} ${inset} H ${width - inset} V ${inset + arm}`,
    `M ${inset} ${height - inset - arm} V ${height - inset} H ${inset + arm}`,
    `M ${width - inset - arm} ${height - inset} H ${width - inset} V ${height - inset - arm}`,
  ];
  const lines = Array.from(
    { length: Math.max(0, Math.floor((height - 80) / 72)) },
    (_, index) => 56 + index * 72
  );
  const ticks = Array.from(
    { length: Math.max(0, Math.floor((width - 80) / 96)) },
    (_, index) => 64 + index * 96
  );

  return (
    <g aria-hidden="true">
      {lines.map((y) => (
        <line
          key={`line-${y}`}
          x1={inset}
          x2={width - inset}
          y1={y}
          y2={y}
          stroke="var(--line)"
          strokeWidth={1}
          opacity={0.22}
        />
      ))}
      {ticks.map((x) => (
        <line
          key={`tick-${x}`}
          x1={x}
          x2={x}
          y1={inset}
          y2={inset + 5}
          stroke="var(--line)"
          strokeWidth={1}
          opacity={0.7}
        />
      ))}
      {brackets.map((d) => (
        <path
          key={d}
          d={d}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={1}
          opacity={0.55}
        />
      ))}
    </g>
  );
}

function DotsDecor({ width, height }: { width: number; height: number }) {
  return (
    <g aria-hidden="true">
      <defs>
        <pattern
          id="cloud-dots"
          width={28}
          height={28}
          patternUnits="userSpaceOnUse"
        >
          <circle cx={1.5} cy={1.5} r={1.1} fill="var(--line)" opacity={0.7} />
        </pattern>
      </defs>
      <rect width={width} height={height} fill="url(#cloud-dots)" />
    </g>
  );
}

export function CloudCanvas({
  logos,
  renderedIcons,
  blankIconIds,
  chipFills,
  preset,
  size,
  sort,
  transparentChips,
  isLoading,
  statusText,
  seed,
  graphRef,
}: CloudCanvasProps) {
  const { width, height } = size;
  const tooltipRef = useRef<SVGGElement | null>(null);
  const tooltipRectRef = useRef<SVGRectElement | null>(null);
  const tooltipTextRef = useRef<SVGTextElement | null>(null);
  const tickHandlerRef = useRef<() => void>(() => {});
  const edgeElsRef = useRef<Map<string, SVGPathElement>>(new Map());
  const [edges, setEdges] = useState<Edge[]>([]);

  const { setNodeRef, simNodesRef } = useForceLayout(logos, {
    width,
    height,
    layout: preset.layout,
    sort,
    onTick: () => tickHandlerRef.current(),
  });
  const { setMotionRef, handlePointerEnter, handlePointerLeave } =
    useLogoMotion(logos);

  const counts = useMemo(() => logos.map((l) => l.count), [logos]);
  const minC = counts.length ? Math.min(...counts) : 1;
  const maxC = counts.length ? Math.max(...counts) : 1;

  const getRadius = (count: number) =>
    getLogoRadius(count, minC, maxC, logos.length, sort);

  const updateEdges = useCallback(() => {
    if (edges.length === 0) return;
    const nodes = simNodesRef.current;
    for (const edge of edges) {
      const a = nodes.get(edge.a);
      const b = nodes.get(edge.b);
      const el = edgeElsRef.current.get(edge.key);
      if (
        !el ||
        !a ||
        !b ||
        typeof a.x !== "number" ||
        typeof a.y !== "number" ||
        typeof b.x !== "number" ||
        typeof b.y !== "number"
      ) {
        continue;
      }
      const midX = (a.x + b.x) / 2;
      const midY = (a.y + b.y) / 2;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      el.setAttribute(
        "d",
        `M ${a.x} ${a.y} Q ${midX - dy * 0.12} ${midY + dx * 0.12} ${b.x} ${b.y}`
      );
    }
  }, [edges, simNodesRef]);

  useEffect(() => {
    tickHandlerRef.current = updateEdges;
  }, [updateEdges]);

  useEffect(() => {
    updateEdges();
  }, [updateEdges]);

  useEffect(() => {
    if (preset.decorations !== "edges" || logos.length < 2) {
      return;
    }
    const timer = window.setTimeout(() => {
      setEdges(buildEdges(Array.from(simNodesRef.current.values())));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [logos, preset.decorations, simNodesRef]);

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
    const tooltipWidth = Math.max(Math.ceil(text.getComputedTextLength()) + 22, 68);
    const tooltipHeight = 27;
    const gap = 10;

    const aboveTop = y - radius - gap - tooltipHeight;
    const belowTop = y + radius + gap;
    let rectY: number;
    if (aboveTop >= 4) {
      rectY = -radius - gap - tooltipHeight;
    } else if (belowTop + tooltipHeight <= height - 4) {
      rectY = radius + gap;
    } else {
      rectY = Math.max(4 - y, Math.min(height - tooltipHeight - 4 - y, aboveTop));
    }

    const clampedX = Math.max(
      tooltipWidth / 2 + 4,
      Math.min(width - tooltipWidth / 2 - 4, x)
    );

    tip.setAttribute("transform", `translate(${clampedX}, ${y})`);
    rect.setAttribute("x", String(-tooltipWidth / 2));
    rect.setAttribute("y", String(rectY));
    rect.setAttribute("width", String(tooltipWidth));
    rect.setAttribute("height", String(tooltipHeight));
    text.setAttribute("x", "0");
    text.setAttribute("y", String(rectY + tooltipHeight / 2));
    tip.dataset.visible = "true";
  };

  const hideTooltip = () => {
    if (tooltipRef.current) tooltipRef.current.dataset.visible = "false";
  };

  return (
    <div className="relative flex w-full flex-grow items-center justify-center overflow-hidden h-[calc(100vh-130px)]">
      {logos.length === 0 ? (
        isLoading && statusText ? (
          <StatusBadge text={statusText} variant="center" />
        ) : (
          <div className="flex select-none flex-col items-center gap-3 text-muted">
            <Cloud className="h-8 w-8 opacity-50" />
            <span className="text-sm">Enter a GitHub username to build your stack</span>
          </div>
        )
      ) : (
        <>
          <svg
            ref={graphRef}
            viewBox={`0 0 ${width} ${height}`}
            className="h-full w-full select-none"
            style={{ display: "block", ...presetCssVars(preset) } as CSSProperties}
          >
            <defs>
              <filter
                id="logo-shadow"
                x="-30%"
                y="-30%"
                width="160%"
                height="160%"
              >
                <feDropShadow
                  dx="0"
                  dy="4"
                  stdDeviation="5"
                  floodOpacity={preset.shadowOpacity}
                />
              </filter>
            </defs>

            <style>{`
              .logo-node { cursor: pointer; }
              .cloud-tip-layer { opacity: 0; pointer-events: none; transition: opacity 0.12s ease; }
              .cloud-tip-layer[data-visible="true"] { opacity: 1; }
            `}</style>

            <rect width={width} height={height} fill="var(--canvas)" />

            {preset.decorations === "dots" && (
              <DotsDecor width={width} height={height} />
            )}
            {preset.decorations === "techy" && (
              <TechyDecor width={width} height={height} />
            )}
            {preset.decorations === "stars" && (
              <SpaceDecor width={width} height={height} seed={seed} />
            )}
            {preset.decorations === "edges" && logos.length >= 2 && (
              <g aria-hidden="true">
                {edges.map((edge) => (
                  <path
                    key={edge.key}
                    ref={(el) => {
                      if (el) edgeElsRef.current.set(edge.key, el);
                      else edgeElsRef.current.delete(edge.key);
                    }}
                    fill="none"
                    stroke="var(--muted)"
                    strokeWidth={1}
                    opacity={0.32}
                  />
                ))}
              </g>
            )}

            {logos.map((item) => {
              const radius = getRadius(item.count);
              const icon = renderedIcons.get(item.id) ?? item.icon;
              const chipFill = transparentChips
                ? "transparent"
                : chipFills.get(item.id) ??
                  (preset.dark ? PLATE_ON_DARK : PLATE_ON_LIGHT);

              return (
                <LogoNode
                  key={item.id}
                  item={item}
                  radius={radius}
                  icon={icon}
                  iconIsBlank={blankIconIds.has(item.id)}
                  chipFill={chipFill}
                  transparentChips={transparentChips}
                  setNodeRef={setNodeRef}
                  setMotionRef={setMotionRef}
                  onPointerEnter={(node) => {
                    handlePointerEnter(item.id);
                    showTooltip(node, item.name, item.count, radius);
                  }}
                  onPointerLeave={() => {
                    handlePointerLeave(item.id);
                    hideTooltip();
                  }}
                />
              );
            })}

            <CloudTooltip
              groupRef={tooltipRef}
              rectRef={tooltipRectRef}
              textRef={tooltipTextRef}
            />
          </svg>

          {isLoading && statusText && <StatusBadge text={statusText} />}
        </>
      )}
    </div>
  );
}
