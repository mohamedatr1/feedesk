"use client";

import { TriangleAlert } from "lucide-react";
import type { CampaignDetail, CampaignNotice } from "@/lib/api";
import { Dialog } from "@/components/Dialog";
import { CampaignDialogSummary } from "@/components/campaigns/CampaignDialogSummary";
import { blockingHint } from "@/components/campaigns/campaign-format";

export function SubmitCampaignDialog({
  open,
  campaign,
  busy,
  error,
  blockedReasons,
  onClose,
  onConfirm,
}: {
  open: boolean;
  campaign: CampaignDetail;
  busy: boolean;
  error: string | null;
  blockedReasons: CampaignNotice[] | null;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="إرسال الحملة للاعتماد"
      description="سيتم إعادة حساب المستلمين من الكشف المؤكد قبل الإرسال للاعتماد."
      busy={busy}
    >
      <CampaignDialogSummary campaign={campaign} />

      {campaign.warnings.length > 0 && (
        <ul className="mt-3 space-y-1 text-[12px] leading-6 text-[var(--fd-ink)]">
          {campaign.warnings.map((warning, index) => (
            <li key={`${warning.code}-${index}`} className="flex items-start gap-2">
              <TriangleAlert
                size={14}
                className="mt-1 shrink-0 text-[var(--fd-amber-text)]"
                aria-hidden
              />
              <span>
                {warning.message_ar}
                {warning.count != null ? ` — العدد: ${warning.count}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-brand-soft)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
        لن تُرسل أي رسالة. ستصبح الحملة بانتظار الاعتماد.
      </p>

      {blockedReasons && blockedReasons.length > 0 && (
        <div
          role="alert"
          className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] p-3 text-[12px] leading-6 text-[var(--fd-red-text)]"
        >
          <p className="font-semibold">تعذر الإرسال للاعتماد.</p>
          <ul className="mt-1 list-inside list-disc">
            {blockedReasons.map((reason, index) => (
              <li key={`${reason.code}-${index}`}>{reason.message_ar}</li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <p
          role="alert"
          className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
        >
          {error}
        </p>
      )}

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="fd-btn fd-btn-secondary h-11"
          onClick={onClose}
          disabled={busy}
          data-autofocus
        >
          إلغاء
        </button>
        <button
          type="button"
          className="fd-btn fd-btn-primary h-11"
          onClick={onConfirm}
          disabled={busy}
        >
          {busy ? "جارٍ الإرسال للاعتماد…" : "إرسال للاعتماد"}
        </button>
      </div>
    </Dialog>
  );
}
