import { type MessageDetail } from "@/lib/api";
import { MessageStatusPill } from "@/components/messages/MessageStatusPill";
import {
  MESSAGE_STATUS_META,
  TONE_BORDER,
  messageStatusExplainer,
} from "@/components/messages/message-format";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[var(--fd-line)] py-2 last:border-b-0">
      <dt className="text-[12px] text-[var(--fd-ink-subtle)]">{label}</dt>
      <dd className="min-w-0 text-[13px] text-[var(--fd-ink)]">{children}</dd>
    </div>
  );
}

export function MessageStatusCard({
  message,
  formatted,
}: {
  message: MessageDetail;
  formatted: (value: string | null) => string;
}) {
  const meta = MESSAGE_STATUS_META[message.internal_status];
  const tone = meta?.tone ?? "neutral";

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="message-status-title">
      <h2 id="message-status-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
        الحالة
      </h2>
      <dl className="mt-2">
        <Row label="الحالة الداخلية">
          <span className="inline-flex flex-wrap items-center gap-2">
            <MessageStatusPill status={message.internal_status} />
            {!meta && (
              <bdi dir="ltr" lang="en" className="text-[10px] text-[var(--fd-ink-subtle)]">
                {message.internal_status}
              </bdi>
            )}
          </span>
        </Row>
        <Row label="وقت الإرسال إلى المزوّد">
          {message.submitted_at ? (
            <bdi dir="ltr" className="whitespace-nowrap tabular-nums">
              {formatted(message.submitted_at)}
            </bdi>
          ) : (
            <span className="text-[var(--fd-ink-muted)]">لم تُرسل إلى المزوّد بعد.</span>
          )}
        </Row>
        <Row label="تأكيد التسليم">
          {message.delivered_at ? (
            <bdi dir="ltr" className="whitespace-nowrap tabular-nums">
              {formatted(message.delivered_at)}
            </bdi>
          ) : (
            <span className="text-[var(--fd-ink-muted)]">لم يصل تأكيد تسليم.</span>
          )}
        </Row>
        <Row label="حالة المزوّد (كما وردت)">
          {message.provider_status ? (
            <bdi dir="ltr" lang="en" className="break-all font-mono text-[11px]">
              {message.provider_status}
            </bdi>
          ) : (
            "—"
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

      <p
        className={`mt-3 border-s-[3px] ps-3 text-[12.5px] leading-6 text-[var(--fd-ink-muted)] ${TONE_BORDER[tone]}`}
        hidden={!messageStatusExplainer(message, formatted)}
      >
        {messageStatusExplainer(message, formatted)}
      </p>
    </section>
  );
}
