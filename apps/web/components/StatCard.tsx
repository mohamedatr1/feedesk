import type { LucideIcon } from "lucide-react";

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint: string;
  icon: LucideIcon;
}) {
  return (
    <section className="fd-card fd-card-pad">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px] font-medium text-[var(--fd-ink-muted)]">{label}</p>
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--fd-surface-alt)] text-[var(--fd-ink-muted)]">
          <Icon size={18} strokeWidth={1.8} aria-hidden />
        </span>
      </div>
      <p className="fd-stat-value mt-3">{value}</p>
      <p className="mt-3 text-[11px] text-[var(--fd-ink-subtle)]">{hint}</p>
    </section>
  );
}
