import { formatNumber } from "@/lib/api";

type Cell = {
  label: string;
  value: number | null;
  tone?: "neutral" | "amber";
};

/** Counts are unknown until known: null renders "—", never a fake 0. */
export function CampaignCounts({
  recipients,
  excluded,
  warnings,
  messages,
}: {
  recipients: number | null;
  excluded: number | null;
  warnings: number | null;
  messages?: number | null;
}) {
  const cells: Cell[] = [
    { label: "المستلمون", value: recipients },
    { label: "مستثناة", value: excluded },
    { label: "التحذيرات", value: warnings, tone: "amber" },
  ];
  if (messages !== undefined && messages !== null) {
    cells.push({ label: "الرسائل المُنشأة", value: messages });
  }

  return (
    <dl
      className={`grid grid-cols-2 gap-3 ${
        cells.length >= 4 ? "md:grid-cols-4" : "md:grid-cols-3"
      }`}
    >
      {cells.map((cell) => {
        const tinted = cell.tone === "amber" && (cell.value ?? 0) > 0;
        return (
          <div
            key={cell.label}
            className={`rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] p-3 ${
              tinted ? "bg-[var(--fd-amber-soft)]" : "bg-[var(--fd-surface-alt)]"
            }`}
          >
            <dt className="text-[11px] font-medium text-[var(--fd-ink-muted)]">
              {cell.label}
            </dt>
            <dd className="mt-1 text-[24px] font-bold leading-none tabular-nums text-[var(--fd-ink)]">
              {cell.value === null ? "—" : formatNumber(cell.value)}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
