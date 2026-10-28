import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import gsap from 'gsap';
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
  minRadius?: number;
  maxRadius?: number;
  padding?: number;
}

/**
 * Pick a radius range that scales down as the cloud grows so every logo
 * keeps its own space on the canvas instead of being pushed off-screen.
 *
 * At 200 logos this is 18–46px radius (36–92px diameter), which mirrors the
 * backend SVG: most icons stay small, while the handful of very common
 * packages get a visibly larger mark.
 */
export function getRadiusBounds(total: number) {
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
  total: number
): number {
  const { minRadius, maxRadius } = getRadiusBounds(total);
  if (maxCount === minCount) return (minRadius + maxRadius) / 2;
  const normalized = (count - minCount) / (maxCount - minCount);
  // Exponent > 1 keeps the long tail small and reserves the big marks for
  // the genuinely dominant packages (same visual rhythm as output.svg).
  return minRadius + Math.pow(normalized, 1.2) * (maxRadius - minRadius);
}

export function useForceLayout(
  logos: Logo[],
  options: ForceLayoutOptions = {}
) {
  const {
    width = 1400,
    height = 850,
  } = options;
  const padding =
    options.padding ??
    Math.max(3, Math.min(8, 1600 / Math.max(logos.length, 1)));
  const { minRadius, maxRadius } =
    options.minRadius !== undefined && options.maxRadius !== undefined
      ? { minRadius: options.minRadius, maxRadius: options.maxRadius }
      : getRadiusBounds(logos.length);

  // Map of logo.id -> DOM <g class="logo-node">
  const nodeRefs = useRef<Map<string, SVGGElement>>(new Map());
  // Persistent simulation nodes so existing nodes preserve x, y, vx, vy
  const simNodesRef = useRef<Map<string, SimNode>>(new Map());
  const simRef = useRef<d3.Simulation<SimNode, undefined> | null>(null);

  useEffect(() => {
    if (!logos || logos.length === 0) {
      if (simRef.current) simRef.current.stop();
      simNodesRef.current.clear();
      return;
    }

    // 1. Calculate count bounds for radius scaling
    const counts = logos.map((l) => l.count);
    const minC = Math.min(...counts);
    const maxC = Math.max(...counts);

    const getRadius = (count: number) =>
      getLogoRadius(count, minC, maxC, logos.length);

    // 2. Update existing nodes or create new ones with initial center positions
    const currentSimNodes = simNodesRef.current;
    const nextSimNodes: SimNode[] = [];
    const centerX = width / 2;
    const centerY = height / 2;

    logos.forEach((l, index) => {
      const radius = getRadius(l.count);
      let existing = currentSimNodes.get(l.id);

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

    // 3. Initialize or update D3 force simulation
    if (!simRef.current) {
      simRef.current = d3
        .forceSimulation<SimNode>()
        .force(
          'collide',
          d3.forceCollide<SimNode>((d) => d.radius + padding).strength(0.85)
        )
        .force('x', d3.forceX<SimNode>(centerX).strength(0.07))
        .force('y', d3.forceY<SimNode>(centerY).strength(0.07))
        .force('charge', d3.forceManyBody<SimNode>().strength(-8))
        .on('tick', () => {
          // Direct DOM transform updates — NO React setState inside tick!
          const domMap = nodeRefs.current;
          for (const node of currentSimNodes.values()) {
            const el = domMap.get(node.id);
            if (el && node.x !== undefined && node.y !== undefined) {
              // Clamp inside canvas boundary
              const x = Math.max(node.radius, Math.min(width - node.radius, node.x));
              const y = Math.max(node.radius, Math.min(height - node.radius, node.y));
              node.x = x;
              node.y = y;
              el.setAttribute('transform', `translate(${x}, ${y})`);
            }
          }
        });
    }

    const sim = simRef.current;
    sim.nodes(nextSimNodes);
    sim.alpha(0.35).restart();

    // 4. Attach interactive dragging behavior with D3 & GSAP lift
    for (const [id, el] of nodeRefs.current.entries()) {
      const node = currentSimNodes.get(id);
      if (!node) continue;

      const dragBehavior = d3
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

      d3.select(el).call(dragBehavior);
    }

    return () => {
      sim.stop();
    };
  }, [logos, width, height, minRadius, maxRadius, padding]);

  // Register a DOM node ref
  const setNodeRef = (id: string, el: SVGGElement | null) => {
    if (el) {
      nodeRefs.current.set(id, el);

      // Immediately attach drag if simulation is already active
      const node = simNodesRef.current.get(id);
      const sim = simRef.current;
      if (node && sim) {
        const dragBehavior = d3
          .drag<SVGGElement, unknown>()
          .on('start', (event) => {
            if (!event.active) sim.alphaTarget(0.35).restart();
            node.fx = node.x;
            node.fy = node.y;
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
            node.fx = Math.max(node.radius, Math.min(width - node.radius, event.x));
            node.fy = Math.max(node.radius, Math.min(height - node.radius, event.y));
          })
          .on('end', (event) => {
            if (!event.active) sim.alphaTarget(0);
            node.fx = null;
            node.fy = null;
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

        d3.select(el).call(dragBehavior);
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
