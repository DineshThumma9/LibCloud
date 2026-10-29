import { PLATE_DARK } from "../lib/color";
import type { Logo } from "../schemas";

type LogoNodeProps = {
  item: Logo;
  radius: number;
  icon?: string;
  iconIsBlank: boolean;
  chipFill: string;
  transparentChips: boolean;
  setNodeRef: (id: string, el: SVGGElement | null) => void;
  setMotionRef: (id: string, el: SVGGElement | null) => void;
  onPointerEnter: (node: SVGGElement) => void;
  onPointerLeave: () => void;
};

export function LogoNode({
  item,
  radius,
  icon,
  iconIsBlank,
  chipFill,
  transparentChips,
  setNodeRef,
  setMotionRef,
  onPointerEnter,
  onPointerLeave,
}: LogoNodeProps) {
  const imgSize = radius * 1.35;
  const darkChip = !transparentChips && chipFill === PLATE_DARK;

  return (
    /* OUTER GROUP: D3 owns translate(x, y) */
    <g
      ref={(el) => setNodeRef(item.id, el)}
      className="logo-node"
      onPointerEnter={(event) => onPointerEnter(event.currentTarget)}
      onPointerLeave={onPointerLeave}
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
          stroke={transparentChips ? "transparent" : "var(--line)"}
          strokeWidth={transparentChips ? 0 : 1}
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
            fontFamily="ui-sans-serif, system-ui, sans-serif"
            fontWeight="bold"
            fontSize={radius * 0.72}
            textAnchor="middle"
            fill={
              transparentChips
                ? "var(--ink)"
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
}
