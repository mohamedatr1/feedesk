import { ChevronDown } from "lucide-react";

export function RedactedPayload({
  payload,
}: {
  payload: Record<string, unknown> | null | undefined;
}) {
  const hasPayload = Boolean(payload && Object.keys(payload).length > 0);

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="message-payload-title">
      <h2 id="message-payload-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
        حمولة استجابة المزوّد (منقّحة)
      </h2>
      <p className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">
        أُزيلت الحقول الحساسة قبل الحفظ. لا تُعرض مفاتيح الوصول ولا نص الطلب الكامل.
      </p>

      {hasPayload ? (
        <details className="group mt-2">
          <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-[var(--fd-radius-control)] px-1 text-[13px] font-medium text-[var(--fd-ink)] hover:bg-[var(--fd-surface-alt)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--fd-brand)] [&::-webkit-details-marker]:hidden">
            <ChevronDown
              size={16}
              aria-hidden
              className="text-[var(--fd-ink-muted)] transition group-open:rotate-180"
            />
            عرض الحمولة
          </summary>
          <pre
            dir="ltr"
            lang="en"
            className="mt-2 max-h-[320px] overflow-auto whitespace-pre-wrap break-all rounded-[10px] bg-[var(--fd-surface-alt)] p-3 font-mono text-[11px] leading-5"
          >
            {JSON.stringify(payload, null, 2)}
          </pre>
        </details>
      ) : (
        <p className="mt-3 text-[13px] text-[var(--fd-ink-subtle)]">لا توجد حمولة مسجّلة.</p>
      )}
    </section>
  );
}
