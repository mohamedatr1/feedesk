import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--fd-surface-alt)] text-[var(--fd-ink-subtle)]">
        <Icon size={22} strokeWidth={1.7} aria-hidden />
      </span>
      <p className="text-sm font-semibold text-[var(--fd-ink)]">{title}</p>
      <p className="mt-1 max-w-md text-[13px] text-[var(--fd-ink-muted)]">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
