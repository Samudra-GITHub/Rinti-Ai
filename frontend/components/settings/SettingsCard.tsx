import { ReactNode } from "react";
import { Card } from "@/ui/Card";

interface SettingsCardProps {
  title: string;
  description: string;
  children: ReactNode;
}

export function SettingsCard({ title, description, children }: SettingsCardProps) {
  return (
    <Card className="flex items-center justify-between gap-6">
      <div>
        <h3 className="text-sm font-medium text-white/90">{title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-white/45">{description}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </Card>
  );
}
