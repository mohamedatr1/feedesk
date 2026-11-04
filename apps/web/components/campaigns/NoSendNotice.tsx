import { Info } from "lucide-react";

/**
 * Two truthful densities:
 * - `strip`: the M4 read-only statement. Safe on every screen, including ones
 *   that coexist with `sending`/`completed` campaigns. It never claims sending
 *   is disabled.
 * - `full`: only for an `approved` campaign whose messages have not moved yet
 *   (design D1). It speaks about this campaign, never about global capability.
 */
export function NoSendNotice({
  density = "strip",
  className = "",
}: {
  density?: "strip" | "full";
  className?: string;
}) {
  if (density === "full") {
    return (
      <section
        className={`rounded-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-brand-soft)] p-5 text-[var(--fd-ink)] ${className}`}
        aria-label="حالة الإرسال"
      >
        <div className="flex items-start gap-3 border-s-4 border-[var(--fd-brand)] ps-3">
          <Info
            size={18}
            className="mt-0.5 shrink-0 text-[var(--fd-brand)]"
            aria-hidden
          />
          <div>
            <p className="text-[13px] font-semibold">لم تُرسل أي رسالة من هذه الحملة بعد</p>
            <p className="mt-1 text-[12.5px] leading-6 text-[var(--fd-ink-muted)]">
              اعتماد الحملة يثبّت نسختها فقط. لم تبدأ معالجة رسائلها، ولا يوجد
              إجراء إرسال أو إعادة إرسال يدوي.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <p
      className={`flex min-h-11 items-center gap-2 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-brand-soft)] px-4 py-2 text-[12.5px] text-[var(--fd-ink-muted)] ${className}`}
    >
      <Info size={16} className="shrink-0 text-[var(--fd-brand)]" aria-hidden />
      <span>عرض فقط — لا يوجد إرسال أو إعادة إرسال يدوي.</span>
    </p>
  );
}
