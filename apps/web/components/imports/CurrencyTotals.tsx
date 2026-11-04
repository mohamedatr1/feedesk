import { formatDecimalString } from "@/lib/api";

/**
 * One line per currency. Amounts are API decimal strings and are never summed
 * across currencies or converted to binary floats.
 */
export function CurrencyTotals({
  totals,
  className = "",
}: {
  totals?: Record<string, string> | null;
  className?: string;
}) {
  if (!totals) return null;

  const entries = Object.entries(totals)
    .filter(([, amount]) => typeof amount === "string" && amount.trim() !== "")
    .sort(([a], [b]) => a.localeCompare(b));

  if (entries.length === 0) return null;

  return (
    <dl
      className={`space-y-1 text-[12px] text-[var(--fd-ink-muted)] ${className}`}
      aria-label="الإجماليات حسب العملة"
    >
      {entries.map(([currency, amount]) => (
        <div key={currency} className="flex items-center gap-2">
          <dt className="sr-only">{currency}</dt>
          <dd className="tabular-nums">
            <bdi dir="ltr">
              <span aria-hidden>{currency} </span>
              {formatDecimalString(amount)}
            </bdi>
          </dd>
        </div>
      ))}
    </dl>
  );
}
