import Link from "next/link";
import { ArrowUpLeft } from "lucide-react";
import { formatNumber } from "@/lib/api";

type Tone = "neutral" | "amber" | "red";

const DOT: Record<Tone, string> = {
  neutral: "bg-[var(--fd-line-strong)]",
  amber: "bg-[var(--fd-amber)]",
  red: "bg-[var(--fd-red)]",
};

export type QuickMetric = {
  label: string;
  value: number;
  href: string;
  tone?: Tone;
};

/**
 * Four supporting counts that also act as shortcuts. Cells are links to the
 * screen that owns the number; nothing here is a second source of truth.
 */
export function QuickMetrics({ items }: { items: QuickMetric[] }) {
  return (
    <section className="fd-card overflow-hidden" aria-labelledby="dashboard-metrics-title">
      <h2 id="dashboard-metrics-title" className="sr-only">
        مؤشرات مساندة
      </h2>
      <ul className="grid grid-cols-2 gap-px bg-[var(--fd-line)] lg:grid-cols-4">
        {items.map((item) => (
          <li key={item.label} className="bg-[var(--fd-surface)]">
            <Link
              href={item.href}
              className="flex h-full min-h-[76px] flex-col justify-center gap-0.5 px-4 py-3 transition hover:bg-[var(--fd-surface-alt)]"
            >
              <span className="flex items-center justify-between gap-2 text-[11px] text-[var(--fd-ink-subtle)]">
                <span className="flex min-w-0 items-center gap-1.5">
                  <span
                    aria-hidden
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[item.tone ?? "neutral"]}`}
                  />
                  <span className="truncate">{item.label}</span>
                </span>
                <ArrowUpLeft size={12} aria-hidden className="shrink-0 text-[var(--fd-brand)]" />
              </span>
              <span className="mt-0.5 text-[20px] font-bold leading-none tabular-nums text-[var(--fd-ink)]">
                {formatNumber(item.value)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
