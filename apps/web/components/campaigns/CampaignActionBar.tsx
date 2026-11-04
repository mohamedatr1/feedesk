"use client";

import Link from "next/link";
import { Ban, ClipboardCheck, Lock, Pencil } from "lucide-react";
import { formatDateTime, formatNumber } from "@/lib/api";
import type { CampaignDetail } from "@/lib/api";

export function CampaignActionBar({
  campaign,
  canEdit,
  canSubmit,
  canApprove,
  busy = false,
  blockedReason,
  locale,
  timeZone,
  onEdit,
  onSubmit,
  onApprove,
  onCancel,
}: {
  campaign: CampaignDetail;
  canEdit: boolean;
  canSubmit: boolean;
  canApprove: boolean;
  busy?: boolean;
  blockedReason?: string | null;
  locale?: string | null;
  timeZone?: string | null;
  onEdit: () => void;
  onSubmit: () => void;
  onApprove: () => void;
  onCancel: () => void;
}) {
  const status = campaign.status;
  const date = (value: string | null) =>
    value ? formatDateTime(value, { locale, timeZone }) : "—";

  const counts = (
    <span className="text-[12px] text-[var(--fd-ink-muted)]">
      المستلمون:{" "}
      <span className="font-semibold tabular-nums text-[var(--fd-ink)]">
        {formatNumber(campaign.recipient_count)}
      </span>
      {" · "}مستثناة:{" "}
      <span className="tabular-nums">{formatNumber(campaign.excluded_count)}</span>
      {" · "}التحذيرات:{" "}
      <span className="tabular-nums">{formatNumber(campaign.warnings.length)}</span>
    </span>
  );

  return (
    <div className="sticky bottom-0 z-20 mt-6 rounded-t-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-surface)]/95 px-4 py-4 shadow-[var(--fd-shadow-pop)] backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          {status === "draft" && counts}
          {status === "awaiting_approval" && (
            <p className="text-[12px] text-[var(--fd-ink-muted)]">
              بانتظار الاعتماد منذ <bdi dir="ltr">{date(campaign.submitted_at)}</bdi>
            </p>
          )}
          {status === "approved" && (
            <p className="flex flex-wrap items-center gap-2 text-[12px] text-[var(--fd-green-text)]">
              <Lock size={14} aria-hidden />
              معتمدة · نسخة مقفلة
              {campaign.pending_job_count != null && (
                <span className="text-[var(--fd-ink-muted)]">
                  · الرسائل: بانتظار الإرسال{" "}
                  <span className="tabular-nums">
                    ({formatNumber(campaign.pending_job_count)})
                  </span>
                </span>
              )}
            </p>
          )}
          {status === "cancelled" && (
            <p className="flex items-center gap-2 text-[12px] text-[var(--fd-ink-muted)]">
              <Ban size={14} aria-hidden />
              أُلغيت <bdi dir="ltr">{date(campaign.cancelled_at)}</bdi>
            </p>
          )}

          {status === "draft" && !campaign.can_submit && blockedReason && (
            <p id="submit-blocked-reason" className="mt-1 text-[11px] text-[var(--fd-ink-muted)]">
              {blockedReason}
            </p>
          )}
          {status === "awaiting_approval" && !campaign.can_approve && blockedReason && (
            <p id="submit-blocked-reason" className="mt-1 text-[11px] text-[var(--fd-ink-muted)]">
              {blockedReason}
            </p>
          )}
          {status === "awaiting_approval" && !canApprove && (
            <p className="mt-1 text-[11px] text-[var(--fd-ink-muted)]">
              الاعتماد متاح لمدير النظام أو لموظف لديه صلاحية اعتماد الحملات.
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {status === "cancelled" && (
            <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
              العودة إلى الحملات
            </Link>
          )}

          {status === "approved" && (
            <>
              <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
                العودة إلى الحملات
              </Link>
              {canApprove && campaign.can_cancel && (
                <button
                  type="button"
                  className="fd-btn fd-btn-ghost h-11 text-[var(--fd-red-text)] hover:bg-[var(--fd-red-soft)]"
                  onClick={onCancel}
                  disabled={busy}
                >
                  إلغاء الحملة
                </button>
              )}
            </>
          )}

          {status === "awaiting_approval" && (
            <>
              {canApprove && (
                <button
                  type="button"
                  className="fd-btn fd-btn-primary h-11"
                  onClick={onApprove}
                  disabled={busy || !campaign.can_approve}
                  aria-describedby={
                    !campaign.can_approve && blockedReason ? "submit-blocked-reason" : undefined
                  }
                >
                  <ClipboardCheck size={16} aria-hidden />
                  اعتماد الحملة
                </button>
              )}
              {canEdit && campaign.can_cancel && (
                <button
                  type="button"
                  className="fd-btn fd-btn-ghost h-11 text-[var(--fd-red-text)] hover:bg-[var(--fd-red-soft)]"
                  onClick={onCancel}
                  disabled={busy}
                >
                  إلغاء الحملة
                </button>
              )}
            </>
          )}

          {status === "draft" && (
            <>
              {canEdit && campaign.can_cancel && (
                <button
                  type="button"
                  className="fd-btn fd-btn-ghost h-11 text-[var(--fd-red-text)] hover:bg-[var(--fd-red-soft)]"
                  onClick={onCancel}
                  disabled={busy}
                >
                  إلغاء الحملة
                </button>
              )}
              {canEdit && (
                <button
                  type="button"
                  className="fd-btn fd-btn-secondary h-11"
                  onClick={onEdit}
                  disabled={busy}
                >
                  <Pencil size={15} aria-hidden />
                  تعديل
                </button>
              )}
              {canSubmit && (
                <button
                  type="button"
                  className="fd-btn fd-btn-primary h-11"
                  onClick={onSubmit}
                  disabled={busy || !campaign.can_submit}
                  aria-describedby={
                    !campaign.can_submit && blockedReason ? "submit-blocked-reason" : undefined
                  }
                >
                  <ClipboardCheck size={15} aria-hidden />
                  إرسال للاعتماد
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
