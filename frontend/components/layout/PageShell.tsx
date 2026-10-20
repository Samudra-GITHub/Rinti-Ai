import type { ReactNode } from "react";

interface PageShellProps {
  title: string;
  description?: string;
  /** Optional control shown opposite the title (e.g. a selector). */
  action?: ReactNode;
  children: ReactNode;
}

/** Shared frame for the utility pages: its own scroll area and a calm heading. */
export function PageShell({ title, description, action, children }: PageShellProps) {
  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="mx-auto w-full max-w-3xl px-4 pb-20 pt-4 sm:px-6 sm:pt-8">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl font-medium tracking-[-0.045em] text-fg sm:text-5xl">{title}</h1>
            {description && <p className="mt-2 max-w-xl text-sm leading-relaxed text-fg/50">{description}</p>}
          </div>
          {action}
        </header>
        {children}
      </div>
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <h2 className="mb-1 mt-9 px-1 text-xs font-medium tracking-wide text-fg/40 first:mt-0">{children}</h2>;
}
