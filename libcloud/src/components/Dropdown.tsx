import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Check, ChevronDown } from "lucide-react";

export type DropdownOption<T extends string> = {
  value: T;
  label: string;
  meta?: string;
  description?: string;
  icon?: ReactNode;
};

type DropdownProps<T extends string> = {
  label: string;
  value: T;
  options: DropdownOption<T>[];
  onChange: (value: T) => void;
  align?: "left" | "right";
  menuWidth?: string;
};

export function Dropdown<T extends string>({
  label,
  value,
  options,
  onChange,
  align = "left",
  menuWidth = "w-64",
}: DropdownProps<T>) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const current =
    options.find((option) => option.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!current) return null;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        className={`flex h-9 items-center gap-2 rounded-lg border bg-surface pl-2.5 pr-2 text-sm text-ink transition hover:border-accent/60 cursor-pointer ${
          open ? "border-accent" : "border-line"
        }`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`${label}: ${current.label}`}
        title={
          current.description
            ? `${label}: ${current.description}`
            : `${label}: ${current.label}`
        }
      >
        {current.icon && (
          <span className="flex h-4 w-4 shrink-0 items-center justify-center text-muted">
            {current.icon}
          </span>
        )}
        <span className="max-w-[9rem] truncate">{current.label}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 text-muted transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div
            className={`fixed left-1/2 top-20 z-20 max-h-[calc(100vh-6rem)] -translate-x-1/2 overflow-y-auto rounded-xl border border-line bg-surface p-1 shadow-2xl sm:absolute sm:top-full sm:mt-1.5 sm:max-h-80 sm:translate-x-0 ${menuWidth} max-w-[calc(100vw-2rem)] ${
              align === "right"
                ? "sm:right-0 sm:left-auto"
                : "sm:left-0 sm:right-auto"
            }`}
            role="listbox"
            aria-label={label}
          >
            {options.map((option) => {
              const selected = option.value === value;
              return (
                <button
                  key={option.value}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  title={option.description}
                  onClick={() => {
                    onChange(option.value);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition cursor-pointer ${
                    selected
                      ? "bg-accent/10 text-ink"
                      : "text-muted hover:bg-canvas hover:text-ink"
                  }`}
                >
                  <span
                    className={`flex h-4 w-4 shrink-0 items-center justify-center ${
                      selected ? "text-accent" : ""
                    }`}
                  >
                    {option.icon}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">{option.label}</span>
                    {option.meta && (
                      <span className="mt-0.5 block text-[10px] text-muted">
                        {option.meta}
                      </span>
                    )}
                  </span>
                  {selected && (
                    <Check className="h-3.5 w-3.5 shrink-0 text-accent" />
                  )}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
