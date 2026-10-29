import type { ReactNode } from "react";

type PopoverProps = {
  title: string;
  trigger: ReactNode;
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
  children: ReactNode;
  width?: string;
};

export function Popover({
  title,
  trigger,
  open,
  onToggle,
  onClose,
  children,
  width = "w-80",
}: PopoverProps) {
  return (
    <div className="relative">
      <button
        type="button"
        onClick={onToggle}
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-surface text-ink transition hover:border-accent/70 hover:text-accent cursor-pointer"
        title={title}
        aria-label={title}
        aria-expanded={open}
      >
        {trigger}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={onClose} />
          <div
            className={`fixed left-1/2 top-20 z-20 max-h-[calc(100vh-6rem)] -translate-x-1/2 overflow-y-auto rounded-xl border border-line bg-surface p-4 text-ink shadow-2xl sm:absolute sm:top-full sm:mt-2 sm:max-h-[calc(100vh-120px)] sm:translate-x-0 sm:right-0 sm:left-auto ${width} max-w-[calc(100vw-2rem)]`}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
                {title}
              </h2>
              <button
                type="button"
                onClick={onClose}
                className="rounded-md px-1.5 text-sm text-muted transition hover:text-ink cursor-pointer"
                aria-label="Close"
              >
                ✕
              </button>
            </div>
            {children}
          </div>
        </>
      )}
    </div>
  );
}
