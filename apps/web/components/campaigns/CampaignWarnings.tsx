import { TriangleAlert } from "lucide-react";
import { formatNumber } from "@/lib/api";
import type { CampaignNotice } from "@/lib/api";

export function CampaignWarnings({
  warnings,
  canApprove,
  acknowledged = false,
}: {
  warnings: CampaignNotice[];
  canApprove: boolean;
  acknowledged?: boolean;
}) {
  if (!warnings || warnings.length === 0) return null;

  return (
    <section
      className="rounded-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-amber-soft)] p-4"
      aria-labelledby="campaign-warnings-title"
    >
      <h2
        id="campaign-warnings-title"
        className="flex items-center gap-2 text-[13px] font-semibold text-[var(--fd-amber-text)]"
      >
        <TriangleAlert size={16} aria-hidden />
        {acknowledged
          ? `التحذيرات التي تم تأكيدها (${formatNumber(warnings.length)})`
          : `التحذيرات (${formatNumber(warnings.length)})`}
      </h2>
      <ul className="mt-2 space-y-2">
        {warnings.map((warning, index) => (
          <li
            key={`${warning.code}-${index}`}
            className="flex flex-wrap items-start justify-between gap-2 text-[13px] leading-6 text-[var(--fd-ink)]"
          >
            <span className="flex min-w-0 items-start gap-2">
              <TriangleAlert
                size={14}
                className="mt-1 shrink-0 text-[var(--fd-amber-text)]"
                aria-hidden
              />
              <span>{warning.message_ar}</span>
            </span>
            <span className="flex items-center gap-2">
              {warning.count != null && (
                <span className="whitespace-nowrap text-[11px] text-[var(--fd-amber-text)]">
                  العدد: {formatNumber(warning.count)}
                </span>
              )}
              <bdi dir="ltr" lang="en" className="text-[10px] text-[var(--fd-ink-subtle)]">
                {warning.code}
              </bdi>
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[11px] leading-5 text-[var(--fd-amber-text)]">
        {acknowledged
          ? "تم تأكيد هذه التحذيرات عند الاعتماد."
          : canApprove
            ? "التحذيرات لا تمنع الاعتماد، لكن يجب تأكيدها عند الاعتماد."
            : "سيطّلع المسؤول عن الاعتماد على هذه التحذيرات قبل الاعتماد."}
      </p>
    </section>
  );
}
