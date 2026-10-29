type StatusBadgeProps = {
  text: string;
  variant?: "center" | "floating";
};

export function StatusBadge({ text, variant = "floating" }: StatusBadgeProps) {
  const center = variant === "center";
  return (
    <div
      className={
        center
          ? ""
          : "pointer-events-none absolute bottom-6 left-1/2 z-20 -translate-x-1/2"
      }
    >
      <div
        className={`${
          center
            ? "gap-3 border px-6 py-3.5"
            : "gap-2.5 border px-4 py-2 shadow-md backdrop-blur-md"
        } flex select-none items-center rounded-lg border-line bg-surface/90 text-muted`}
      >
        <span
          className={`inline-block rounded-full bg-accent animate-pulse ${
            center ? "h-2 w-2" : "h-1.5 w-1.5"
          }`}
        />
        <span className="text-xs font-mono tracking-tight">{text}</span>
      </div>
    </div>
  );
}
