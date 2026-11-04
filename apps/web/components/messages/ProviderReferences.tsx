"use client";

import { Copy } from "lucide-react";
import { type MessageDetail } from "@/lib/api";
import { useCopyFeedback } from "@/components/messages/copy";

function Row({
  label,
  value,
  ariaLabel,
  onCopy,
}: {
  label: string;
  value: string | null | undefined;
  ariaLabel: string;
  onCopy: (value: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[var(--fd-line)] py-2 last:border-b-0">
      <dt className="text-[12px] text-[var(--fd-ink-subtle)]">{label}</dt>
      <dd className="min-w-0 text-[13px] text-[var(--fd-ink)]">
        {value ? (
          <span className="inline-flex min-w-0 max-w-full items-start gap-2">
            <bdi
              dir="ltr"
              lang="en"
              className="min-w-0 break-all font-mono text-[11px]"
            >
              {value}
            </bdi>
            <button
              type="button"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--fd-radius-control)] border border-[var(--fd-line-strong)] text-[var(--fd-ink-muted)] hover:bg-[var(--fd-surface-alt)]"
              onClick={() => onCopy(value)}
              aria-label={ariaLabel}
            >
              <Copy size={14} aria-hidden />
            </button>
          </span>
        ) : (
          <>
            <span>—</span>
            <span className="mt-0.5 block text-[11px] text-[var(--fd-ink-subtle)]">
              لم يُسجَّل.
            </span>
          </>
        )}
      </dd>
    </div>
  );
}

export function ProviderReferences({ message }: { message: MessageDetail }) {
  const { status, copy } = useCopyFeedback();

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="message-provider-title">
      <h2 id="message-provider-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
        مراجع المزوّد
      </h2>
      <dl className="mt-2">
        <Row
          label="معرّف رسالة المزوّد"
          value={message.provider_message_id}
          ariaLabel="نسخ معرّف رسالة المزوّد"
          onCopy={(value) => void copy(value, "تم نسخ المعرّف.")}
        />
        <Row
          label="معرّف طلب المزوّد"
          value={message.provider_request_id}
          ariaLabel="نسخ معرّف طلب المزوّد"
          onCopy={(value) => void copy(value, "تم نسخ المعرّف.")}
        />
      </dl>
      <p role="status" className="mt-1 min-h-[18px] text-[12px] text-[var(--fd-ink-muted)]">
        {status}
      </p>
    </section>
  );
}
