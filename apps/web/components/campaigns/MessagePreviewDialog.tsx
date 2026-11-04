"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Phone, TriangleAlert } from "lucide-react";
import { formatDecimalString, formatNumber } from "@/lib/api";
import type { CampaignRecipient } from "@/lib/api";
import { Dialog } from "@/components/Dialog";

export function MessagePreviewDialog({
  open,
  recipients,
  initialIndex,
  onClose,
}: {
  open: boolean;
  recipients: CampaignRecipient[];
  initialIndex: number;
  onClose: () => void;
}) {
  const [index, setIndex] = useState(initialIndex);

  useEffect(() => {
    if (open) setIndex(Math.max(0, Math.min(initialIndex, recipients.length - 1)));
  }, [open, initialIndex, recipients.length]);

  const recipient = recipients[index];
  if (!recipient) return null;

  const atStart = index <= 0;
  const atEnd = index >= recipients.length - 1;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="معاينة الرسالة"
      description={
        <span className="flex flex-wrap items-center gap-2">
          <bdi dir="auto">{recipient.guardian_name}</bdi>
          <span aria-hidden>·</span>
          <bdi dir="ltr">{recipient.phone}</bdi>
          <button
            type="button"
            className="fd-btn fd-btn-ghost h-11 w-11 px-0"
            aria-label="نسخ رقم الهاتف"
            onClick={() => {
              navigator.clipboard?.writeText(recipient.phone).catch(() => undefined);
            }}
          >
            <Phone size={15} aria-hidden />
          </button>
        </span>
      }
    >
      <div
        className="max-h-[40vh] overflow-y-auto whitespace-pre-wrap rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] p-4 text-[15px] leading-[1.9] text-[var(--fd-ink)]"
        dir="rtl"
        tabIndex={0}
        role="region"
        aria-label="نص الرسالة"
      >
        {recipient.message}
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-[12px]">
        <div>
          <dt className="text-[var(--fd-ink-subtle)]">المبلغ</dt>
          <dd className="tabular-nums">
            <bdi dir="ltr">
              {formatDecimalString(recipient.amount)} {recipient.currency}
            </bdi>
          </dd>
        </div>
        <div>
          <dt className="text-[var(--fd-ink-subtle)]">الفصول</dt>
          <dd>{recipient.fee_periods.join("، ") || "—"}</dd>
        </div>
        <div>
          <dt className="text-[var(--fd-ink-subtle)]">الطلاب</dt>
          <dd>{recipient.student_names.join("، ") || "—"}</dd>
        </div>
        <div>
          <dt className="text-[var(--fd-ink-subtle)]">الأرصدة</dt>
          <dd className="tabular-nums">{formatNumber(recipient.fee_balance_ids.length)}</dd>
        </div>
        <div>
          <dt className="text-[var(--fd-ink-subtle)]">عدد الأحرف</dt>
          <dd className="tabular-nums">{formatNumber(recipient.message.length)}</dd>
        </div>
      </dl>

      {recipient.warnings.length > 0 && (
        <div className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] p-3">
          <p className="flex items-center gap-1.5 text-[12px] font-semibold text-[var(--fd-amber-text)]">
            <TriangleAlert size={14} aria-hidden />
            تحذيرات على هذا المستلم
          </p>
          <ul className="mt-1 list-inside list-disc text-[12px] leading-5 text-[var(--fd-ink)]">
            {recipient.warnings.map((warning, warningIndex) => (
              <li key={`${warning.code}-${warningIndex}`}>{warning.message_ar}</li>
            ))}
          </ul>
        </div>
      )}

      <p role="status" className="mt-3 text-[11px] text-[var(--fd-ink-muted)]">
        {recipients.length > 1
          ? `المستلم ${formatNumber(index + 1)} من ${formatNumber(recipients.length)}`
          : ""}
      </p>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          className="fd-btn fd-btn-secondary h-11"
          onClick={onClose}
          data-autofocus
        >
          إغلاق
        </button>
        {recipients.length > 1 && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
              onClick={() => setIndex((value) => Math.max(0, value - 1))}
              disabled={atStart}
              aria-label={`المستلم السابق: ${recipients[Math.max(0, index - 1)].guardian_name}`}
            >
              <ChevronRight size={15} aria-hidden />
              السابق
            </button>
            <button
              type="button"
              className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
              onClick={() => setIndex((value) => Math.min(recipients.length - 1, value + 1))}
              disabled={atEnd}
              aria-label={`المستلم التالي: ${recipients[Math.min(recipients.length - 1, index + 1)].guardian_name}`}
            >
              التالي
              <ChevronLeft size={15} aria-hidden />
            </button>
          </div>
        )}
      </div>
    </Dialog>
  );
}
