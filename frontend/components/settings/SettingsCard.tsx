import { ReactNode } from "react";

interface SettingsCardProps {
  title: string;
  description: string;
  children: ReactNode;
}

/** One row of a settings list: label and explanation on the left, control on the right. */
export function SettingsCard({ title, description, children }: SettingsCardProps) {
  return (
    <div className="flex items-center justify-between gap-x-6 gap-y-3 border-b max-sm:flex-col max-sm:items-start border-fg/8 px-1 py-4 last:border-b-0">
      <div className="min-w-0">
        <h3 className="text-sm font-medium text-fg/90">{title}</h3>
        <p className="mt-1 text-[13px] leading-relaxed text-fg/45">{description}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}
