import Link from "next/link";
import { CircleAlert, TriangleAlert } from "lucide-react";
import { formatNumber } from "@/lib/api";
import { messagesHref } from "@/components/messages/message-format";

export function ResultsReviewPanel({
  campaignId,
  failed,
  unknown,
}: {
  campaignId: string;
  failed: number | null;
  unknown: number | null;
}) {
  const failedCount = failed ?? 0;
  const unknownCount = unknown ?? 0;
  const total = failedCount + unknownCount;
  if (total <= 0) return null;

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="results-review-title">
      <h2
        id="results-review-title"
        className="text-[15px] font-bold text-[var(--fd-ink)]"
      >
        تحتاج مراجعة ({formatNumber(total)})
      </h2>

      <ul className="mt-3 space-y-3">
        {failedCount > 0 && (
          <li className="flex flex-wrap items-start justify-between gap-3 border-s-[3px] border-s-[var(--fd-red)] ps-3">
            <div className="flex min-w-0 items-start gap-2">
              <CircleAlert
                size={16}
                aria-hidden
                className="mt-1 shrink-0 text-[var(--fd-red-text)]"
              />
              <div className="min-w-0">
                <p className="text-[13px] font-semibold text-[var(--fd-ink)]">
                  فشل الإرسال ({formatNumber(failedCount)})
                </p>
                <p className="mt-0.5 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
                  لم يقبل المزوّد هذه الرسائل. راجع سبب الفشل في كل رسالة، ثم أنشئ حملة
                  جديدة بعد تصحيح البيانات.
                </p>
              </div>
            </div>
            <Link
              href={messagesHref({ campaign_id: campaignId, status: "failed" })}
              className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
            >
              عرض رسائل فشل الإرسال
            </Link>
          </li>
        )}

        {unknownCount > 0 && (
          <li className="flex flex-wrap items-start justify-between gap-3 border-s-[3px] border-s-[var(--fd-amber)] ps-3">
            <div className="flex min-w-0 items-start gap-2">
              <TriangleAlert
                size={16}
                aria-hidden
                className="mt-1 shrink-0 text-[var(--fd-amber-text)]"
              />
              <div className="min-w-0">
                <p className="text-[13px] font-semibold text-[var(--fd-ink)]">
                  نتيجة غير معروفة ({formatNumber(unknownCount)})
                </p>
                <p className="mt-0.5 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
                  لم نتأكد من وصول هذه الرسائل. قد تكون وصلت، ولا تُعاد تلقائيًا.
                </p>
              </div>
            </div>
            <Link
              href={messagesHref({ campaign_id: campaignId, status: "unknown" })}
              className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
            >
              عرض الرسائل غير المعروفة
            </Link>
          </li>
        )}
      </ul>
    </section>
  );
}
