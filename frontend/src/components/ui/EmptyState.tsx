import type { ReactNode } from "react";

export type Tone = "teal" | "lime" | "sky" | "rose" | "amber" | "violet" | "slate";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  actions?: ReactNode;
  tone?: Tone;
}

export function EmptyState({ icon, title, description, actions, tone = "lime" }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className={`empty-state-icon tone-${tone}`} aria-hidden="true">
        {icon}
      </div>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {actions && <div className="empty-state-actions">{actions}</div>}
    </div>
  );
}
