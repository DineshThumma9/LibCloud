import type { RefObject } from "react";

type CloudTooltipProps = {
  groupRef: RefObject<SVGGElement | null>;
  rectRef: RefObject<SVGRectElement | null>;
  textRef: RefObject<SVGTextElement | null>;
};

/** One tooltip for the whole cloud, painted after every node. */
export function CloudTooltip({ groupRef, rectRef, textRef }: CloudTooltipProps) {
  return (
    <g ref={groupRef} className="cloud-tip-layer" data-visible="false">
      <rect
        ref={rectRef}
        rx={6}
        fill="var(--surface)"
        stroke="var(--accent)"
        strokeWidth={1}
        filter="url(#logo-shadow)"
      />
      <text
        ref={textRef}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="var(--ink)"
        fontSize={12}
        fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
        fontWeight={600}
      />
    </g>
  );
}
