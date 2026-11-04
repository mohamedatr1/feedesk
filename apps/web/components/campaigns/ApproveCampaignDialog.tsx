"use client";

import { useEffect, useState } from "react";
import { Info, TriangleAlert } from "lucide-react";
import type { CampaignDetail, CampaignNotice } from "@/lib/api";
import { Dialog } from "@/components/Dialog";
import { CampaignDialogSummary } from "@/components/campaigns/CampaignDialogSummary";

export function ApproveCampaignDialog({
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
  onConfirm: (acknowledgeWarnings: boolean) => void;
}) {
  const [acknowledged, setAcknowledged] = useState(false);
  const hasWarnings = campaign.warnings.length > 0;

  useEffect(() => {
    if (!open) setAcknowledged(false);
  }, [open]);

  const gateBlocked = hasWarnings && !acknowledged;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="اعتماد الحملة"
      description="سيتم تثبيت نسخة غير قابلة للتعديل من هذه الحملة. لا يمكن تعديل المستلمين أو المبالغ بعد الاعتماد."
      busy={busy}
    >
      <CampaignDialogSummary campaign={campaign} />

      {hasWarnings && (
        <div className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] p-3">
          <p className="flex items-center gap-1.5 text-[12px] font-semibold text-[var(--fd-amber-text)]">
            <TriangleAlert size={14} aria-hidden />
            التحذيرات ({campaign.warnings.length})
          </p>
          <ul className="mt-1 space-y-1 text-[12px] leading-6 text-[var(--fd-ink)]">
            {campaign.warnings.map((warning, index) => (
              <li key={`${warning.code}-${index}`}>
                {warning.message_ar}
                {warning.count != null ? ` — العدد: ${warning.count}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-3 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-brand-soft)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
        <Info size={15} className="mt-1 shrink-0 text-[var(--fd-brand)]" aria-hidden />
        <span>
          لن تُرسل أي رسالة. سيُنشأ لكل مستلم سجل رسالة بانتظار الإرسال، ولا يوجد
          إرسال إلى المزوّد في هذه المرحلة.
        </span>
      </p>

      {hasWarnings && (
        <label className="mt-3 flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] p-3 text-[12px] leading-6">
          <input
            type="checkbox"
            className="mt-0.5 h-5 w-5 shrink-0 accent-[var(--fd-brand)]"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
            disabled={busy}
          />
          <span>راجعت التحذيرات وأفهم أن الاعتماد نهائي ولا يمكن تعديل الحملة بعده.</span>
        </label>
      )}

      {gateBlocked && (
        <p id="approve-gate" className="mt-2 text-[11px] text-[var(--fd-ink-muted)]">
          أكّد أنك راجعت التحذيرات للاعتماد.
        </p>
      )}

      {blockedReasons && blockedReasons.length > 0 && (
        <div
          role="alert"
          className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] p-3 text-[12px] leading-6 text-[var(--fd-red-text)]"
        >
          <p className="font-semibold">تعذر الاعتماد: الحملة غير جاهزة للاعتماد.</p>
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
          onClick={() => onConfirm(acknowledged)}
          disabled={busy || gateBlocked}
          aria-describedby={gateBlocked ? "approve-gate" : undefined}
        >
          {busy ? "جارٍ الاعتماد…" : "اعتماد وتثبيت الحملة"}
        </button>
      </div>
    </Dialog>
  );
}
