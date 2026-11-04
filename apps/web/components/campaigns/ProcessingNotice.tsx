import Link from "next/link";
import { Info } from "lucide-react";

/**
 * D1: once messages have moved, the M3 "nothing was sent" line is false.
 * This states what is known and where the record lives. No delivery claim.
 */
export function ProcessingNotice({ campaignId }: { campaignId: string }) {
  return (
    <section
      className="rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-brand-soft)] px-4 py-3"
      aria-label="حالة معالجة الرسائل"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex min-h-11 items-center gap-2 text-[12.5px] text-[var(--fd-ink-muted)]">
          <Info size={16} className="shrink-0 text-[var(--fd-brand)]" aria-hidden />
          <span>بدأت معالجة الرسائل. راجع نتائج الرسائل لمعرفة الحالات المؤكدة.</span>
        </p>
        <Link
          href={`/campaigns/${campaignId}/results`}
          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
        >
          نتائج الرسائل
        </Link>
      </div>
    </section>
  );
}
