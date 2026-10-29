import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import gsap from 'gsap';
import { PRESETS, type PresetLayout, type SortId } from './lib/presets';
import type { Logo } from './schemas';

export interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  radius: number;
  slug: string;
  name: string;
  count: number;
}

interface ForceLayoutOptions {
  width?: number;
  height?: number;
  padding?: number;
  layout?: PresetLayout;
  sort?: SortId;
  onTick?: () => void;
}

const DEFAULT_LAYOUT: PresetLayout = PRESETS.paper.layout;

/**
 * Pick a radius range that scales down as the cloud grows so every logo
 * keeps its own space on the canvas instead of being pushed off-screen.
 *
 * At 200 logos this is 18–46px radius (36–92px diameter), which mirrors the
 * backend SVG: most icons stay small, while the handful of very common
 * packages get a visibly larger mark.
 */
function getRadiusBounds(total: number) {
  const safeTotal = Math.max(total, 1);
  const base = Math.min(24, Math.max(8, 18 * Math.sqrt(200 / safeTotal)));
  return {
    minRadius: base,
    maxRadius: Math.min(52, base * (46 / 18)),
  };
}

export function getLogoRadius(
  count: number,
  minCount: number,
  maxCount: number,
  total: number,
  sort: SortId = 'most-used'
): number {
  const { minRadius, maxRadius } = getRadiusBounds(total);
  if (maxCount === minCount) return (minRadius + maxRadius) / 2;

  const normalized = (count - minCount) / (maxCount - minCount);
  const weight = sort === 'least-used' ? 1 - normalized : normalized;
  // Balanced compresses the long tail; the other modes keep a strong
  // dominant-package rhythm.
  const exponent = sort === 'balanced' ? 0.55 : 1.2;
  return minRadius + Math.pow(weight, exponent) * (maxRadius - minRadius);
}

function createDragBehavior(
  el: SVGGElement,
  node: SimNode,
  sim: d3.Simulation<SimNode, undefined>,
  width: number,
  height: number
) {
  return d3
    .drag<SVGGElement, unknown>()
    .on('start', (event) => {
      if (!event.active) sim.alphaTarget(0.35).restart();
      node.fx = node.x;
      node.fy = node.y;
      // GSAP: scale up and elevate on grab
      const motionEl = el.querySelector('.logo-motion');
      if (motionEl) {
        gsap.to(motionEl, {
          scale: 1.25,
          duration: 0.2,
          ease: 'power2.out',
          overwrite: 'auto',
        });
      }
    })
    .on('drag', (event) => {
      // Follow pointer and stay inside bounds
      node.fx = Math.max(node.radius, Math.min(width - node.radius, event.x));
      node.fy = Math.max(node.radius, Math.min(height - node.radius, event.y));
    })
    .on('end', (event) => {
      if (!event.active) sim.alphaTarget(0);
      node.fx = null;
      node.fy = null;
      // GSAP: bounce back into place on release
      const motionEl = el.querySelector('.logo-motion');
      if (motionEl) {
        gsap.to(motionEl, {
          scale: 1,
          duration: 0.3,
          ease: 'back.out(1.6)',
          overwrite: 'auto',
        });
      }
    });
}

export function useForceLayout(
  logos: Logo[],
  options: ForceLayoutOptions = {}
) {
  const { width = 1400, height = 850 } = options;
  const layout = options.layout ?? DEFAULT_LAYOUT;
  const sort = options.sort ?? 'most-used';
  const padding =
    options.padding ??
    Math.max(3, Math.min(8, 1600 / Math.max(logos.length, 1)));

  // Map of logo.id -> DOM <g class="logo-node">
  const nodeRefs = useRef<Map<string, SVGGElement>>(new Map());
  // Persistent simulation nodes so existing nodes preserve x, y, vx, vy
  const simNodesRef = useRef<Map<string, SimNode>>(new Map());
  const simRef = useRef<d3.Simulation<SimNode, undefined> | null>(null);
  // The canvas uses this to keep decorative edges in sync with the layout.
  const onTickRef = useRef(options.onTick);

  useEffect(() => {
    onTickRef.current = options.onTick;
  });

  useEffect(() => {
    if (!logos || logos.length === 0) {
      if (simRef.current) simRef.current.stop();
      simNodesRef.current.clear();
      return;
    }

    const counts = logos.map((l) => l.count);
    const minC = Math.min(...counts);
    const maxC = Math.max(...counts);
    const centerX = width / 2;
    const centerY = height / 2;
    const clampX = (value: number, radius: number) =>
      Math.max(radius, Math.min(width - radius, value));
    const clampY = (value: number, radius: number) =>
      Math.max(radius, Math.min(height - radius, value));
    const snap = (value: number) =>
      layout.grid > 0 ? Math.round(value / layout.grid) * layout.grid : value;

    const getRadius = (count: number) =>
      getLogoRadius(count, minC, maxC, logos.length, sort);

    // 1. Update existing nodes or create new ones with initial center positions
    const currentSimNodes = simNodesRef.current;
    const nextSimNodes: SimNode[] = [];

    logos.forEach((l, index) => {
      const radius = getRadius(l.count);
      const existing = currentSimNodes.get(l.id);

      if (existing) {
        existing.radius = radius;
        existing.count = l.count;
        nextSimNodes.push(existing);
      } else {
        // Deterministic phyllotaxis spiral start for new nodes
        const angle = index * 2.39996; // Golden angle
        const dist = Math.min(width, height) * 0.15 * Math.sqrt(index);
        const newNode: SimNode = {
          id: l.id,
          slug: l.slug,
          name: l.name,
          count: l.count,
          radius,
          x: centerX + Math.cos(angle) * dist,
          y: centerY + Math.sin(angle) * dist,
        };
        currentSimNodes.set(l.id, newNode);
        nextSimNodes.push(newNode);
      }
    });

    // Remove deleted nodes
    const activeIds = new Set(logos.map((l) => l.id));
    for (const [id] of currentSimNodes) {
      if (!activeIds.has(id)) {
        currentSimNodes.delete(id);
      }
    }

    // 2. Initialize the simulation once, then update its forces when the
    //    preset or canvas size changes.
    if (!simRef.current) {
      simRef.current = d3.forceSimulation<SimNode>();
    }

    const sim = simRef.current;
    // Re-register each run so snapping and bounds follow the current preset.
    sim.on('tick', () => {
      // Direct DOM transform updates — NO React setState inside tick!
      const domMap = nodeRefs.current;
      // Snap only once the cloud has cooled, otherwise collision forces fight
      // the grid every frame and the layout never settles.
      const shouldSnap = layout.grid > 0 && sim.alpha() < 0.12;
      for (const node of currentSimNodes.values()) {
        const el = domMap.get(node.id);
        if (el && node.x !== undefined && node.y !== undefined) {
          const x = shouldSnap ? snap(node.x) : node.x;
          const y = shouldSnap ? snap(node.y) : node.y;
          node.x = clampX(x, node.radius);
          node.y = clampY(y, node.radius);
          el.setAttribute('transform', `translate(${node.x}, ${node.y})`);
        }
      }
      onTickRef.current?.();
    });
    const normalizedCount = (node: SimNode) =>
      maxC === minC ? 0.5 : (node.count - minC) / (maxC - minC);

    sim
      .force(
        'charge',
        d3
          .forceManyBody<SimNode>()
          .strength((node) =>
            layout.hubBias
              ? layout.charge - normalizedCount(node) * 24
              : layout.charge
          )
      )
      .force('x', d3.forceX<SimNode>(centerX).strength(layout.xStrength))
      .force('y', d3.forceY<SimNode>(centerY).strength(layout.yStrength))
      .force(
        'collide',
        d3.forceCollide<SimNode>((d) => d.radius + padding).strength(0.85)
      );

    if (layout.radial) {
      const inner = Math.min(width, height) * 0.18;
      const outer = Math.min(width, height) * 0.42;
      sim.force(
        'radial',
        d3
          .forceRadial<SimNode>(
            (node) => inner + (1 - normalizedCount(node)) * (outer - inner),
            centerX,
            centerY
          )
          .strength(0.4)
      );
    } else {
      sim.force('radial', null);
    }

    sim.nodes(nextSimNodes);
    sim.alpha(0.35).restart();

    // 3. Attach interactive dragging behavior with D3 & GSAP lift
    for (const [id, el] of nodeRefs.current.entries()) {
      const node = currentSimNodes.get(id);
      if (!node) continue;
      d3.select(el)
        .on(".drag", null)
        .call(createDragBehavior(el, node, sim, width, height));
    }

    return () => {
      sim.stop();
    };
  }, [logos, width, height, layout, sort, padding]);

  // Register a DOM node ref
  const setNodeRef = (id: string, el: SVGGElement | null) => {
    if (el) {
      nodeRefs.current.set(id, el);

      // Immediately attach drag if simulation is already active
      const node = simNodesRef.current.get(id);
      const sim = simRef.current;
      if (node && sim) {
        d3.select(el)
          .on(".drag", null)
          .call(createDragBehavior(el, node, sim, width, height));
      }
    } else {
      nodeRefs.current.delete(id);
    }
  };

  return {
    setNodeRef,
    simNodesRef,
  };
}
