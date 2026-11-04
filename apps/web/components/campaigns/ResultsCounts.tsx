import { formatNumber } from "@/lib/api";
import { sumKnownCounts } from "@/components/messages/message-format";

type Counts = Partial<Record<string, number>> | null | undefined;

type Cell = {
  key: string;
  label: string;
  value: number | null;
  tone: "neutral" | "amber" | "green" | "red";
  composition?: string | null;
};

const TINT: Record<Cell["tone"], string> = {
  neutral: "bg-[var(--fd-surface-alt)]",
  amber: "bg-[var(--fd-amber-soft)]",
  green: "bg-[var(--fd-green-soft)]",
  red: "bg-[var(--fd-red-soft)]",
};

/**
 * Campaign-wide message counts. A known zero renders `0`; `—` is reserved for
 * unresolved/absent data. Never computed from the visible page.
 */
export function ResultsCounts({
  counts,
  messageCount,
}: {
  counts: Counts;
  messageCount: number | null;
}) {
  const submitting = typeof counts?.submitting === "number" ? counts.submitting : null;
  const accepted =
    typeof counts?.provider_accepted === "number" ? counts.provider_accepted : null;
  const queued =
    typeof counts?.queued_by_provider === "number" ? counts.queued_by_provider : null;
  const failed = typeof counts?.failed === "number" ? counts.failed : null;
  const unknown = typeof counts?.unknown === "number" ? counts.unknown : null;
  const delivered = typeof counts?.delivered === "number" ? counts.delivered : null;
  const pending = typeof counts?.pending === "number" ? counts.pending : null;
  const cancelled = typeof counts?.cancelled === "number" ? counts.cancelled : null;

  const unconfirmed = sumKnownCounts(counts, [
    "submitting",
    "provider_accepted",
    "queued_by_provider",
  ]);
  const review = sumKnownCounts(counts, ["failed", "unknown"]);

  const unconfirmedParts: string[] = [];
  if (submitting) unconfirmedParts.push(`قيد الإرسال ${formatNumber(submitting)}`);
  if (accepted) unconfirmedParts.push(`قبلها المزوّد ${formatNumber(accepted)}`);
  if (queued) unconfirmedParts.push(`في الطابور ${formatNumber(queued)}`);

  const reviewParts: string[] = [];
  if (failed) reviewParts.push(`فشل الإرسال ${formatNumber(failed)}`);
  if (unknown) reviewParts.push(`نتيجة غير معروفة ${formatNumber(unknown)}`);

  const cells: Cell[] = [
    { key: "total", label: "الإجمالي", value: messageCount, tone: "neutral" },
    { key: "pending", label: "لم تبدأ", value: pending, tone: "neutral" },
    {
      key: "unconfirmed",
      label: "لم يصل تأكيد التسليم",
      value: unconfirmed,
      tone: (unconfirmed ?? 0) > 0 ? "amber" : "neutral",
      composition: unconfirmedParts.length ? unconfirmedParts.join(" · ") : null,
    },
    {
      key: "delivered",
      label: "تم التسليم",
      value: delivered,
      tone: (delivered ?? 0) > 0 ? "green" : "neutral",
    },
    {
      key: "review",
      label: "تحتاج مراجعة",
      value: review,
      tone:
        (failed ?? 0) > 0 ? "red" : (unknown ?? 0) > 0 ? "amber" : "neutral",
      composition: reviewParts.length ? reviewParts.join(" · ") : null,
    },
  ];

  if ((cancelled ?? 0) > 0) {
    cells.push({ key: "cancelled", label: "ملغاة", value: cancelled, tone: "neutral" });
  }

  return (
    <dl className="grid grid-cols-2 gap-3 md:grid-cols-3">
      {cells.map((cell) => {
        const tinted = cell.tone !== "neutral" && (cell.value ?? 0) > 0;
        return (
          <div
            key={cell.key}
            className={`rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] p-3 ${
              tinted ? TINT[cell.tone] : "bg-[var(--fd-surface-alt)]"
            }`}
          >
            <dt className="text-[11px] font-medium text-[var(--fd-ink-muted)]">
              {cell.label}
            </dt>
            <dd className="mt-1 text-[24px] font-bold leading-none tabular-nums text-[var(--fd-ink)]">
              {cell.value === null ? "—" : formatNumber(cell.value)}
            </dd>
            {cell.composition && (
              <p className="mt-1 text-[10px] leading-5 text-[var(--fd-ink-subtle)]">
                {cell.composition}
              </p>
            )}
          </div>
        );
      })}
    </dl>
  );
}
