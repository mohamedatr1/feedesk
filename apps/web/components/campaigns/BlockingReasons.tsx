import Link from "next/link";
import { CircleAlert } from "lucide-react";
import { formatNumber } from "@/lib/api";
import type { CampaignNotice } from "@/lib/api";
import { blockingHint } from "@/components/campaigns/campaign-format";

export function BlockingReasons({
  reasons,
  templateId,
  unknownVariables,
  isAdmin,
  canEdit,
  onShowExcluded,
  onChooseTemplate,
}: {
  reasons: CampaignNotice[];
  templateId: string | null;
  unknownVariables?: string[];
  isAdmin: boolean;
  canEdit: boolean;
  onShowExcluded?: () => void;
  onChooseTemplate?: () => void;
}) {
  if (!reasons || reasons.length === 0) return null;

  return (
    <section
      className="rounded-[var(--fd-radius-card)] border border-[var(--fd-red)]/40 bg-[var(--fd-red-soft)] p-4"
      aria-labelledby="campaign-blocking-title"
    >
      <h2
        id="campaign-blocking-title"
        className="flex items-center gap-2 text-[13px] font-semibold text-[var(--fd-red-text)]"
      >
        <CircleAlert size={16} aria-hidden />
        ما يمنع الاعتماد ({formatNumber(reasons.length)})
      </h2>
      <ul className="mt-2 space-y-3">
        {reasons.map((reason, index) => {
          const hint = blockingHint(reason.code);
          const showVariables =
            reason.code === "UNRESOLVED_VARIABLES" &&
            unknownVariables &&
            unknownVariables.length > 0;
          return (
            <li key={`${reason.code}-${index}`} className="text-[13px] leading-6">
              <div className="flex items-start justify-between gap-2">
                <span className="flex min-w-0 items-start gap-2 text-[var(--fd-red-text)]">
                  <CircleAlert size={14} className="mt-1 shrink-0" aria-hidden />
                  <span>{reason.message_ar}</span>
                </span>
                <bdi
                  dir="ltr"
                  lang="en"
                  className="shrink-0 text-[10px] text-[var(--fd-ink-subtle)]"
                >
                  {reason.code}
                </bdi>
              </div>
              {showVariables && (
                <p className="mt-1 ps-6 text-[12px] text-[var(--fd-ink-muted)]">
                  المتغيرات:{" "}
                  {unknownVariables.map((name, itemIndex) => (
                    <span key={name}>
                      {itemIndex > 0 ? "، " : ""}
                      <bdi dir="ltr" lang="en">{`{{${name}}}`}</bdi>
                    </span>
                  ))}
                </p>
              )}
              {hint && reason.code !== "UNRESOLVED_VARIABLES" && (
                <p className="mt-1 ps-6 text-[12px] text-[var(--fd-ink-muted)]">{hint}</p>
              )}

              <div className="mt-1.5 ps-6">
                {reason.code === "NO_ELIGIBLE_RECIPIENTS" && onShowExcluded && (
                  <button
                    type="button"
                    onClick={onShowExcluded}
                    className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                  >
                    عرض المستثناة
                  </button>
                )}

                {(reason.code === "UNRESOLVED_VARIABLES" ||
                  reason.code === "TEMPLATE_INACTIVE") &&
                  (isAdmin && templateId ? (
                    <Link
                      href={`/settings/templates/${templateId}`}
                      className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                    >
                      {reason.code === "TEMPLATE_INACTIVE" ? "تفعيل إصدار" : "فتح القالب"}
                    </Link>
                  ) : (
                    <p className="text-[12px] text-[var(--fd-ink-muted)]">
                      {reason.code === "TEMPLATE_INACTIVE"
                        ? "تواصل مع مدير النظام لتفعيل القالب."
                        : "تواصل مع مدير النظام لتصحيح القالب."}
                    </p>
                  ))}

                {reason.code === "TEMPLATE_NOT_FOUND" && (
                  canEdit && onChooseTemplate ? (
                    <button
                      type="button"
                      onClick={onChooseTemplate}
                      className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                    >
                      اختيار قالب آخر
                    </button>
                  ) : (
                    <p className="text-[12px] text-[var(--fd-ink-muted)]">
                      لا يمكن تعديل هذه الحملة في حالتها الحالية.
                    </p>
                  )
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
