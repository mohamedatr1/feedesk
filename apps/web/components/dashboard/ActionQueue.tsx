import Link from "next/link";
import {
  ArrowUpLeft,
  CheckCircle2,
  CircleAlert,
  CircleHelp,
  FileSearch,
  Info,
  Loader,
  Megaphone,
  Scale,
  Send,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { formatNumber, type DashboardActionItem } from "@/lib/api";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import {
  safeInternalTarget,
  severityMeta,
} from "@/components/dashboard/dashboard-format";

type SeverityTone = "neutral" | "amber" | "red";

type ActionMeta = {
  title: string;
  description: string;
  action: string;
  icon: LucideIcon;
};

/**
 * Action codes are backend-owned. Known codes get a sentence; an unknown code
 * is shown verbatim with a neutral row so nothing is invented on the client.
 */
const ACTION_META: Record<string, ActionMeta> = {
  imports_awaiting_review: {
    title: "كشوف بانتظار المراجعة",
    description: "راجع السجلات المستوردة قبل تأكيدها.",
    action: "مراجعة الآن",
    icon: FileSearch,
  },
  imports_processing: {
    title: "كشوف قيد المعالجة",
    description: "تظهر النتائج بعد انتهاء المعالجة.",
    action: "متابعة",
    icon: Loader,
  },
  imports_failed: {
    title: "كشوف فشلت معالجتها",
    description: "راجع سبب الفشل ثم ارفع الكشف مرة أخرى.",
    action: "عرض الكشوف",
    icon: CircleAlert,
  },
  campaigns_awaiting_approval: {
    title: "حملات بانتظار الاعتماد",
    description: "اعتمدها أو أعدها للمراجعة قبل بدء المعالجة.",
    action: "عرض التفاصيل",
    icon: Send,
  },
  campaigns_active: {
    title: "حملات قيد المعالجة",
    description: "لم تنتهِ معالجة رسائلها بعد.",
    action: "عرض الحملات",
    icon: Megaphone,
  },
  messages_failed_recent: {
    title: "رسائل فشلت مؤخرًا",
    description: "راجع سبب الفشل في كل رسالة قبل إنشاء حملة جديدة.",
    action: "عرض الرسائل",
    icon: CircleAlert,
  },
  messages_unknown_recent: {
    title: "نتائج غير معروفة مؤخرًا",
    description: "تحتاج مطابقة مع المزوّد، ولا تُعاد تلقائيًا.",
    action: "عرض الرسائل",
    icon: CircleHelp,
  },
  messages_reconciliation_required: {
    title: "رسائل تحتاج مطابقة",
    description: "راجعها مع سجل المزوّد قبل أي قرار.",
    action: "عرض الرسائل",
    icon: Scale,
  },
};

const ICON_TONE: Record<SeverityTone, string> = {
  neutral: "bg-[var(--fd-surface-alt)] text-[var(--fd-ink-muted)]",
  amber: "bg-[var(--fd-amber-soft)] text-[var(--fd-amber-text)]",
  red: "bg-[var(--fd-red-soft)] text-[var(--fd-red-text)]",
};

export function ActionQueue({ items }: { items: DashboardActionItem[] }) {
  // Count-zero rows are absent from the queue, so the empty state is positive.
  const rows = items.filter((item) => Number.isFinite(item.count) && item.count > 0);

  return (
    <section className="fd-card flex flex-col overflow-hidden" aria-labelledby="dashboard-actions-title">
      <div className="flex items-center gap-2 border-b border-[var(--fd-line)] px-5 py-4">
        <span aria-hidden className="h-4 w-1 rounded-full bg-[var(--fd-brand)]" />
        <h2 id="dashboard-actions-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
          يحتاج إلى إجراء
        </h2>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="لا توجد إجراءات معلقة"
          description="ستظهر هنا الكشوف التي تحتاج إلى مراجعة، والحملات التي تنتظر الاعتماد، والرسائل التي تحتاج إلى متابعة."
        />
      ) : (
        <ul className="divide-y divide-[var(--fd-line)]">
          {rows.map((item, index) => {
            const meta = ACTION_META[item.code];
            const Icon = meta?.icon ?? Info;
            const severity = severityMeta(item.severity);
            const tone: SeverityTone = severity?.tone ?? "neutral";
            const target = safeInternalTarget(item.target);

            const content = (
              <div className="flex min-h-[64px] flex-wrap items-center gap-3 px-5 py-3.5">
                <span
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${ICON_TONE[tone]}`}
                >
                  <Icon size={18} strokeWidth={1.8} aria-hidden />
                </span>

                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-2 text-[13px] font-semibold text-[var(--fd-ink)]">
                    {meta ? meta.title : <bdi dir="ltr">{item.code}</bdi>}
                    <span className="fd-pill fd-pill-neutral tabular-nums">
                      {formatNumber(item.count)}
                    </span>
                  </p>
                  <p className="mt-0.5 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
                    {meta?.description ?? "تحتاج متابعة."}
                  </p>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  {severity && <StatusPill tone={severity.tone}>{severity.label}</StatusPill>}
                  {target && (
                    <span className="fd-btn fd-btn-primary h-11 px-3 text-[12px]">
                      {meta?.action ?? "فتح"}
                      <ArrowUpLeft size={14} aria-hidden />
                    </span>
                  )}
                </div>
              </div>
            );

            return (
              <li key={`${item.code}-${index}`}>
                {target ? (
                  <Link
                    href={target}
                    className="block transition hover:bg-[var(--fd-surface-alt)]"
                  >
                    {content}
                  </Link>
                ) : (
                  <div>{content}</div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
