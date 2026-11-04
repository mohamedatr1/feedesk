"use client";

import Link from "next/link";
import { Copy } from "lucide-react";
import { type MessageDetail } from "@/lib/api";
import { useCopyFeedback } from "@/components/messages/copy";
import { formatMessageMoney } from "@/components/messages/message-format";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[var(--fd-line)] py-2 last:border-b-0">
      <dt className="text-[12px] text-[var(--fd-ink-subtle)]">{label}</dt>
      <dd className="min-w-0 text-[13px] text-[var(--fd-ink)]">{children}</dd>
    </div>
  );
}

export function MessageDestinationCard({ message }: { message: MessageDetail }) {
  const { status, copy } = useCopyFeedback();
  const channelIsSms = message.channel === "sms";

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="message-destination-title">
      <h2
        id="message-destination-title"
        className="text-[15px] font-bold text-[var(--fd-ink)]"
      >
        الوجهة
      </h2>
      <dl className="mt-2">
        <Row label="ولي الأمر">
          <bdi dir="auto">{message.guardian_name}</bdi>
        </Row>
        <Row label="الهاتف">
          <span className="inline-flex items-center gap-2">
            <bdi dir="ltr" className="whitespace-nowrap font-mono text-[12px]">
              {message.destination_phone}
            </bdi>
            <button
              type="button"
              className="flex h-11 w-11 items-center justify-center rounded-[var(--fd-radius-control)] border border-[var(--fd-line-strong)] text-[var(--fd-ink-muted)] hover:bg-[var(--fd-surface-alt)]"
              onClick={() => void copy(message.destination_phone, "تم نسخ رقم الهاتف.")}
              aria-label="نسخ رقم الهاتف"
            >
              <Copy size={14} aria-hidden />
            </button>
          </span>
        </Row>
        <Row label="الحملة">
          <Link
            href={`/campaigns/${message.campaign_id}`}
            className="text-[var(--fd-brand)] hover:underline"
          >
            <bdi dir="auto">{message.campaign_name}</bdi>
          </Link>
          <Link
            href={`/campaigns/${message.campaign_id}/results`}
            className="mt-0.5 block text-[11px] text-[var(--fd-ink-muted)] hover:underline"
          >
            نتائج الحملة ↗
          </Link>
        </Row>
        <Row label="المبلغ">
          <bdi dir="ltr" className="whitespace-nowrap tabular-nums">
            {formatMessageMoney(message.amount, message.currency)}
          </bdi>
        </Row>
        <Row label="القناة">
          {channelIsSms ? (
            <bdi dir="ltr" lang="en">
              SMS
            </bdi>
          ) : (
            <>
              <bdi dir="ltr" lang="en">
                {message.channel || "—"}
              </bdi>
              <span className="mt-0.5 block text-[11px] text-[var(--fd-ink-subtle)]">
                قناة غير معروفة.
              </span>
            </>
          )}
        </Row>
      </dl>
      <p role="status" className="mt-1 min-h-[18px] text-[12px] text-[var(--fd-ink-muted)]">
        {status}
      </p>
    </section>
  );
}
