import { formatNumber } from "@/lib/api";

type Tone = "neutral" | "green" | "amber" | "red";

type CountItem = {
  label: string;
  value: number | null;
  tone?: Tone;
};

/**
 * Up to five label/value cells. A null value renders "—" (unknown), never 0.
 * Status tinting only applies to non-zero values.
 */
export function ImportCounts({
  total,
  valid,
  invalid,
  duplicates,
  warnings,
  excluded,
  showWarnings = false,
  showDuplicates = true,
}: {
  total: number | null;
  valid: number | null;
  invalid: number | null;
  duplicates?: number | null;
  warnings?: number | null;
  excluded?: number | null;
  showWarnings?: boolean;
  showDuplicates?: boolean;
}) {
  const items: CountItem[] = [
    { label: "الأسطر", value: total, tone: "neutral" },
    { label: "صالحة", value: valid, tone: "green" },
  ];

  if (showWarnings && warnings !== undefined) {
    items.push({ label: "بها تحذيرات", value: warnings, tone: "amber" });
  }

  items.push({ label: "بها أخطاء", value: invalid, tone: "red" });

  if (showDuplicates && duplicates !== undefined) {
    items.push({ label: "مكررة", value: duplicates, tone: "amber" });
  }

  if (excluded !== undefined) {
    items.push({ label: "مستثناة", value: excluded, tone: "neutral" });
  }

  return (
    <dl
      className={`grid grid-cols-2 gap-3 ${
        items.length >= 5 ? "md:grid-cols-3 xl:grid-cols-5" : "md:grid-cols-4"
      }`}
    >
      {items.map((item) => {
        const colored = item.tone && item.tone !== "neutral" && (item.value ?? 0) > 0;
        return (
          <div
            key={item.label}
            className={`rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] p-3 ${
              colored && item.tone === "green"
                ? "bg-[var(--fd-green-soft)]"
                : colored && item.tone === "red"
                  ? "bg-[var(--fd-red-soft)]"
                  : colored && item.tone === "amber"
                    ? "bg-[var(--fd-amber-soft)]"
                    : "bg-[var(--fd-surface-alt)]"
            }`}
          >
            <dt className="text-[11px] font-medium text-[var(--fd-ink-muted)]">{item.label}</dt>
            <dd className="mt-1 text-[22px] font-bold leading-none tabular-nums text-[var(--fd-ink)]">
              {item.value === null ? "—" : formatNumber(item.value)}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
