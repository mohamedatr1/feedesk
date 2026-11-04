import { Info } from "lucide-react";

/**
 * The M4 read-only boundary, stated once per screen. This is a current design
 * decision, not a coming capability. Deliberately not the M3 NoSendNotice:
 * that sentence becomes false once the worker moves a message.
 */
export function HistoryNotice({ className = "" }: { className?: string }) {
  return (
    <p
      className={`flex min-h-11 items-center gap-2 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-brand-soft)] px-4 py-2 text-[12.5px] text-[var(--fd-ink-muted)] ${className}`}
    >
      <Info size={16} className="shrink-0 text-[var(--fd-brand)]" aria-hidden />
      <span>عرض فقط — لا يوجد إرسال أو إعادة إرسال يدوي.</span>
    </p>
  );
}
