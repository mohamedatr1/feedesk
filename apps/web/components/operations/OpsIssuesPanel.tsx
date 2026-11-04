"use client";

import Link from "next/link";
import { ArrowUpLeft, CheckCircle2, CircleAlert, CircleHelp } from "lucide-react";
import { formatNumber, type MessagingOpsIssueItem } from "@/lib/api";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import { TablePager } from "@/components/imports/TablePager";
import { messagesHref } from "@/components/messages/message-format";
import { OpsAlert } from "@/components/operations/OpsAlert";
import {
  attemptsLabel,
  jobErrorText,
  jobStatusLabel,
  jobStatusTone,
} from "@/components/operations/ops-format";

export type OpsIssueKind = "unknown" | "failed";

const KIND_META: Record<
  OpsIssueKind,
  {
    title: string;
    description: string;
    accent: string;
    icon: typeof CircleHelp;
  }
> = {
  unknown: {
    title: "نتيجة غير معروفة",
    description:
      "لم نتأكد هل وصلت هذه الرسائل. قد تكون وصلت، لذلك لا تُعاد تلقائيًا ولا يدويًا.",
    accent: "border-s-[var(--fd-amber)]",
    icon: CircleHelp,
  },
  failed: {
    title: "فشل الإرسال",
    description:
      "لم يقبل المزوّد هذه الرسائل. راجع السبب في كل رسالة ثم أنشئ حملة جديدة بعد تصحيح البيانات.",
    accent: "border-s-[var(--fd-red)]",
    icon: CircleAlert,
  },
};

/**
 * Unknown / failed review list. `reconciliation_required` is shown as a flag
 * but never as an action: this console has no resend endpoint by design.
 */
export function OpsIssuesPanel({
  id,
  kind,
  items,
  total,
  page,
  pageSize,
  onPage,
  loading,
  error,
  onRetry,
  // Heading level lets the panel sit under a section heading without
  // duplicating an h2 in the accessibility outline.
  level = 2,
  formatted,
}: {
  id: string;
  kind: OpsIssueKind;
  items: MessagingOpsIssueItem[] | null;
  total: number;
  page: number;
  pageSize: number;
  onPage: (page: number) => void;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  level?: 2 | 3;
  formatted: (value: string | null) => string;
}) {
  const meta = KIND_META[kind];
  const Icon = meta.icon;
  const Heading = level === 3 ? "h3" : "h2";
  const firstLoad = loading && items === null;
  const rows = items ?? [];

  return (
    <section
      className="fd-card flex min-w-0 flex-col overflow-hidden"
      aria-labelledby={`${id}-title`}
      aria-busy={loading}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
        <div className="flex min-w-0 items-start gap-2.5">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--fd-surface-alt)] text-[var(--fd-ink-muted)]">
            <Icon size={17} strokeWidth={1.8} aria-hidden />
          </span>
          <div className="min-w-0">
            <Heading id={`${id}-title`} className="text-sm font-semibold text-[var(--fd-ink)]">
              {meta.title}
              <span className="ms-1 font-normal text-[var(--fd-ink-muted)]">
                ({items === null ? "—" : formatNumber(total)})
              </span>
            </Heading>
            <p className="mt-0.5 max-w-[46ch] text-[11px] leading-5 text-[var(--fd-ink-subtle)]">
              {meta.description}
            </p>
          </div>
        </div>
        <Link
          href={messagesHref({ status: kind })}
          className="fd-btn fd-btn-secondary h-11 shrink-0 px-3 text-[12px]"
        >
          عرض الكل
        </Link>
      </div>

      {kind === "unknown" && (
        <p className="border-b border-[var(--fd-line)] bg-[var(--fd-amber-soft)] px-5 py-2.5 text-[11.5px] leading-6 text-[var(--fd-amber-text)]">
          المطابقة تكون يدويًا مع سجل المزوّد. لا يوجد إرسال أو إعادة إرسال من هذه الشاشة.
        </p>
      )}

      {error && (
        <div className="p-4">
          <OpsAlert onRetry={onRetry}>تعذر تحميل هذه القائمة. {error}</OpsAlert>
        </div>
      )}

      {!error && items !== null && items.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title={kind === "unknown" ? "لا توجد نتائج غير معروفة" : "لا توجد رسائل فاشلة"}
          description={
            kind === "unknown"
              ? "كل الرسائل لها نتيجة واضحة من المزوّد."
              : "لم يُسجَّل فشل إرسال في هذه اللحظة."
          }
        />
      ) : firstLoad || items !== null ? (
        <ul className="divide-y divide-[var(--fd-line)]">
          {firstLoad &&
            Array.from({ length: 3 }).map((_, index) => (
              <li key={`skeleton-${index}`} className="px-4 py-4">
                <div className="fd-skeleton h-24 w-full" />
              </li>
            ))}

          {!firstLoad &&
            rows.map((item) => {
              const errorText = jobErrorText(item);
              return (
                <li
                  key={item.job_id}
                  className={`border-s-[3px] px-4 py-3.5 transition hover:bg-[var(--fd-surface-alt)] ${meta.accent}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <Link
                        href={`/messages/${item.message_id}`}
                        className="block truncate text-[13px] font-medium text-[var(--fd-ink)] hover:text-[var(--fd-brand)] hover:underline"
                      >
                        <bdi dir="auto">{item.guardian_name || "مستلم"}</bdi>
                      </Link>
                      <p className="mt-0.5 truncate text-[11px] text-[var(--fd-ink-subtle)]">
                        الحملة:{" "}
                        <Link
                          href={messagesHref({ campaign_id: item.campaign_id })}
                          className="hover:text-[var(--fd-ink)] hover:underline"
                        >
                          <bdi dir="auto">{item.campaign_name}</bdi>
                        </Link>
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5">
                      <StatusPill tone={jobStatusTone(item.job_status)}>
                        <bdi dir="auto">{jobStatusLabel(item.job_status)}</bdi>
                      </StatusPill>
                      {item.reconciliation_required && (
                        <StatusPill tone="amber">تحتاج مطابقة</StatusPill>
                      )}
                      {item.retry_exhausted && (
                        <StatusPill tone="neutral">استُنفدت المحاولات</StatusPill>
                      )}
                    </div>
                  </div>

                  <p className="mt-2 line-clamp-2 text-[12px] leading-5 text-[var(--fd-ink-muted)]">
                    {errorText ??
                      (kind === "unknown"
                        ? "لا يوجد رد واضح من المزوّد."
                        : "لم يُسجَّل سبب للفشل.")}
                  </p>

                  <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
                    <p className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-[var(--fd-ink-subtle)]">
                      <bdi dir="ltr" className="whitespace-nowrap font-mono">
                        {item.destination_phone_masked || "—"}
                      </bdi>
                      <span aria-hidden>·</span>
                      <span>{attemptsLabel(item.attempt_count)}</span>
                      <span aria-hidden>·</span>
                      <span>
                        آخر تحديث <bdi dir="ltr">{formatted(item.updated_at)}</bdi>
                      </span>
                    </p>
                    <Link
                      href={`/messages/${item.message_id}`}
                      className="fd-btn fd-btn-secondary h-11 shrink-0 px-3 text-[12px]"
                      aria-label={`عرض رسالة ${item.guardian_name || "المستلم"}`}
                    >
                      <ArrowUpLeft size={14} aria-hidden />
                      عرض الرسالة
                    </Link>
                  </div>
                </li>
              );
            })}
        </ul>
      ) : null}

      {!error && items !== null && total > pageSize && (
        <div className="mt-auto">
          <TablePager
            page={page}
            pageSize={pageSize}
            total={total}
            onPage={onPage}
            busy={loading}
            itemLabel="رسالة"
          />
        </div>
      )}
    </section>
  );
}
