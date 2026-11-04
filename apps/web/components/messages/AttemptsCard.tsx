import { type MessageDetail, formatNumber } from "@/lib/api";
import { isTerminalMessageStatus } from "@/components/messages/message-format";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[var(--fd-line)] py-2 last:border-b-0">
      <dt className="text-[12px] text-[var(--fd-ink-subtle)]">{label}</dt>
      <dd className="min-w-0 text-[13px] text-[var(--fd-ink)]">{children}</dd>
    </div>
  );
}

export function AttemptsCard({
  message,
  formatted,
}: {
  message: MessageDetail;
  formatted: (value: string | null) => string;
}) {
  // A scheduled retry is a record fact. `unknown` never implies a blind resend,
  // and a terminal state has no next attempt even if the API disagrees.
  const scheduled =
    message.next_attempt_at &&
    message.internal_status !== "unknown" &&
    !isTerminalMessageStatus(message.internal_status);

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="message-attempts-title">
      <h2 id="message-attempts-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
        المحاولات
      </h2>
      <dl className="mt-2">
        <Row label="عدد المحاولات">
          {typeof message.attempt_count === "number" ? (
            <span className="tabular-nums">{formatNumber(message.attempt_count)}</span>
          ) : (
            "—"
          )}
        </Row>
        <Row label="المحاولة التالية">
          {scheduled ? (
            <span>
              مجدولة في <bdi dir="ltr">{formatted(message.next_attempt_at ?? null)}</bdi>
            </span>
          ) : (
            <span className="text-[var(--fd-ink-muted)]">لا توجد محاولة مجدولة.</span>
          )}
        </Row>
        <Row label="آخر خطأ">
          {message.last_error_summary || message.last_error_code ? (
            <>
              <span>{message.last_error_summary ?? "—"}</span>
              {message.last_error_code && (
                <bdi
                  dir="ltr"
                  lang="en"
                  className="mt-0.5 block break-all font-mono text-[10px] text-[var(--fd-ink-subtle)]"
                >
                  {message.last_error_code}
                </bdi>
              )}
            </>
          ) : (
            <span className="text-[var(--fd-ink-muted)]">لا يوجد خطأ مسجّل.</span>
          )}
        </Row>
      </dl>

      {scheduled && (
        <p className="mt-3 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
          تُعاد المحاولة تلقائيًا وفق سياسة المحاولات. لا تحتاج إلى إجراء.
        </p>
      )}
    </section>
  );
}
