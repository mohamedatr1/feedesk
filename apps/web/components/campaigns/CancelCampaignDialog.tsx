"use client";

import { useEffect, useId, useState } from "react";
import type { CampaignDetail } from "@/lib/api";
import { Dialog } from "@/components/Dialog";

/**
 * Cancellation is the destructive action, so it keeps ConfirmDialog's anatomy
 * (safe-action autofocus, busy guard, error block) with a reason field.
 */
export function CancelCampaignDialog({
  open,
  campaign,
  busy,
  error,
  onClose,
  onConfirm,
}: {
  open: boolean;
  campaign: CampaignDetail;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const hintId = useId();
  const errorId = useId();
  const approved = campaign.status === "approved";

  useEffect(() => {
    if (!open) {
      setReason("");
      setReasonError(null);
    }
  }, [open]);

  function submit() {
    if (approved && reason.trim() === "") {
      setReasonError("اذكر سبب إلغاء حملة معتمدة.");
      return;
    }
    setReasonError(null);
    onConfirm(reason.trim());
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="إلغاء الحملة"
      busy={busy}
      description={
        <span className="block">
          سيتوقف العمل على هذه الحملة نهائيًا وتبقى في السجل بحالة «ملغاة». لم
          تُرسل أي رسالة.
          {approved && (
            <span className="mt-1 block">
              ستُلغى الرسائل المعلّقة المرتبطة بالحملة. ستبقى نسخة المستلمين محفوظة.
            </span>
          )}
        </span>
      }
    >
      <div className="mt-2">
        <label htmlFor="cancel-reason" className="fd-label">
          سبب الإلغاء
        </label>
        <textarea
          id="cancel-reason"
          className="fd-input min-h-[88px] py-2"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          disabled={busy}
          aria-describedby={`${hintId}${reasonError ? ` ${errorId}` : ""}`}
          aria-invalid={reasonError ? true : undefined}
        />
        <p id={hintId} className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
          {approved
            ? "يُسجَّل في سجل العمليات، وهو مطلوب لحملة معتمدة."
            : "اختياري، لكنه يساعد في سجل العمليات."}
        </p>
        {reasonError && (
          <p id={errorId} role="alert" className="mt-1 text-[11px] text-[var(--fd-red-text)]">
            {reasonError}
          </p>
        )}
      </div>

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
          className="fd-btn fd-btn-danger h-11"
          onClick={submit}
          disabled={busy}
        >
          {busy ? "جارٍ الإلغاء…" : "إلغاء الحملة"}
        </button>
      </div>
    </Dialog>
  );
}
