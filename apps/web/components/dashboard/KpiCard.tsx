import { ArrowDown, ArrowUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { formatDecimalString } from "@/lib/api";
import { Sparkline } from "@/components/dashboard/Sparkline";
import { daysPhrase, formatDelta } from "@/components/dashboard/dashboard-format";

type Tone = "neutral" | "amber" | "green" | "red";

/** Static maps only: Tailwind cannot see a class built from a variable. */
const DOT: Record<Tone, string> = {
  neutral: "bg-[var(--fd-line-strong)]",
  amber: "bg-[var(--fd-amber)]",
  green: "bg-[var(--fd-green)]",
  red: "bg-[var(--fd-red)]",
};

const DELTA_TEXT: Record<"green" | "red" | "neutral", string> = {
  green: "text-[var(--fd-green-text)]",
  red: "text-[var(--fd-red-text)]",
  neutral: "text-[var(--fd-ink-muted)]",
};

export type KpiCurrencyTrend = {
  /** Backend percentage for this currency only. */
  pct: number;
  /** Series values for one currency; fewer than two points = no line. */
  points: number[];
};

export type KpiCurrencyTotal = {
  currency: string;
  /** API decimal string; never converted to a JS number. */
  amount: string;
  /** Configured symbol, or the currency code when no symbol applies. */
  label: string;
  /** Per-currency movement; null when the backend supplied no finite pct. */
  trend?: KpiCurrencyTrend | null;
};

function pctTone(pct: number): "green" | "red" | "neutral" {
  return pct > 0 ? "green" : pct < 0 ? "red" : "neutral";
}

export function KpiCard({
  label,
  icon: Icon,
  tone = "neutral",
  value,
  currencyTotals,
  hint,
  basisDays,
  className = "",
}: {
  label: string;
  icon: LucideIcon;
  tone?: Tone;
  /** Count cards pass a preformatted string. */
  value?: string;
  /** Totals cards pass one entry per currency; currencies are never combined. */
  currencyTotals?: KpiCurrencyTotal[];
  hint: string;
  /** Backend `trends.basis_days`, used only for the totals caption. */
  basisDays?: number;
  className?: string;
}) {
  const totals = currencyTotals ?? [];
  const hasTotals = totals.length > 0;
  const hasTrend = totals.some((total) => Boolean(total.trend));
  const basis = hasTrend ? daysPhrase(basisDays ?? 0) : "";
  // The mockup's headline chart sits in the card corner; it only makes sense
  // when one currency owns the card. Multiple currencies get inline lines.
  const soleTrend = totals.length === 1 ? totals[0].trend ?? null : null;

  return (
    <div className={`fd-card flex min-h-0 flex-col p-4 sm:min-h-[150px] sm:p-5 ${className}`}>
      <div className="flex items-start justify-between gap-2 sm:gap-3">
        <p className="flex min-w-0 items-baseline gap-2 text-[12px] font-medium text-[var(--fd-ink-muted)] sm:text-[13px]">
          <span aria-hidden className={`h-2 w-2 shrink-0 rounded-full ${DOT[tone]}`} />
          <span className="min-w-0">{label}</span>
        </p>
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--fd-surface-alt)] text-[var(--fd-ink-muted)] sm:h-9 sm:w-9">
          <Icon size={17} strokeWidth={1.8} aria-hidden />
        </span>
      </div>

      <div className="mt-3">
        {hasTotals ? (
          <ul className="space-y-1.5" aria-label="الإجماليات حسب العملة">
            {totals.map((total) => {
              const trend = total.trend ?? null;
              const trendTone = trend ? pctTone(trend.pct) : "neutral";
              return (
                <li
                  key={total.currency}
                  className="flex items-center justify-between gap-2"
                >
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-baseline gap-x-1.5">
                      <bdi
                        dir="ltr"
                        className={`tabular-nums font-bold leading-none tracking-tight text-[var(--fd-ink)] ${
                          totals.length > 1 ? "text-[22px]" : "text-[30px]"
                        }`}
                      >
                        {formatDecimalString(total.amount)}
                      </bdi>
                      <span
                        className="text-[12px] font-medium text-[var(--fd-ink-muted)]"
                        aria-label={total.currency}
                      >
                        {total.label}
                      </span>
                    </p>

                    {trend && (
                      <span
                        className={`mt-0.5 flex w-fit items-center gap-0.5 text-[11px] font-semibold ${DELTA_TEXT[trendTone]}`}
                      >
                        {trend.pct > 0 && <ArrowUp size={11} aria-hidden />}
                        {trend.pct < 0 && <ArrowDown size={11} aria-hidden />}
                        <bdi dir="ltr">{formatDelta(trend.pct)}</bdi>
                        <span className="sr-only">
                          {trend.pct > 0 ? "ارتفاع" : trend.pct < 0 ? "انخفاض" : "بدون تغيير"}
                        </span>
                      </span>
                    )}
                  </div>

                  {totals.length > 1 && trend && (
                    <Sparkline points={trend.points} tone={trendTone} compact />
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="fd-stat-value">{value ?? "—"}</p>
        )}
      </div>

      <div className="mt-auto flex items-end justify-between gap-3 pt-3">
        <div className="min-w-0 text-[11px] leading-5">
          {hasTrend && basis ? (
            <span className="text-[10px] text-[var(--fd-ink-subtle)]">
              مقارنة بآخر {basis}
            </span>
          ) : (
            <span className="text-[var(--fd-ink-subtle)]">{hint}</span>
          )}
        </div>
        {soleTrend && <Sparkline points={soleTrend.points} tone={pctTone(soleTrend.pct)} />}
      </div>
    </div>
  );
}
