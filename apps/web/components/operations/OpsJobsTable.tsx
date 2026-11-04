"use client";

import Link from "next/link";
import { ArrowUpLeft, CheckCircle2 } from "lucide-react";
import { formatNumber, type MessagingOpsJobItem } from "@/lib/api";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import { TablePager } from "@/components/imports/TablePager";
import { MessageStatusPill } from "@/components/messages/MessageStatusPill";
import { OpsAlert } from "@/components/operations/OpsAlert";
import {
  attemptsLabel,
  isPast,
  jobErrorText,
  jobStatusLabel,
  jobStatusTone,
} from "@/components/operations/ops-format";

export type OpsJobsVariant = "due" | "stale";

const ACCENT: Record<OpsJobsVariant, string> = {
  due: "bg-[var(--fd-amber)]",
  stale: "bg-[var(--fd-red)]",
};

/**
 * Due / stale queue tables. Both read the same joined job shape; only the
 * time column and the empty copy differ. `locked_by` is deliberately not
 * rendered: it identifies a claim, not something an operator can act on.
 */
export function OpsJobsTable({
  id,
  title,
  description,
  jobs,
  total,
  page,
  pageSize,
  onPage,
  loading,
  error,
  onRetry,
  variant,
  now,
  formatted,
  emptyTitle,
  emptyDescription,
}: {
  id: string;
  title: string;
  description: string;
  jobs: MessagingOpsJobItem[] | null;
  total: number;
  page: number;
  pageSize: number;
  onPage: (page: number) => void;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  variant: OpsJobsVariant;
  now: string | null;
  formatted: (value: string | null) => string;
  emptyTitle: string;
  emptyDescription: string;
}) {
  const firstLoad = loading && jobs === null;
  const rows = jobs ?? [];

  return (
    <section
      className="fd-card mb-5 overflow-hidden"
      aria-labelledby={`${id}-title`}
      aria-busy={loading}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
        <div className="flex min-w-0 items-start gap-2">
          <span aria-hidden className={`mt-1.5 h-4 w-1 shrink-0 rounded-full ${ACCENT[variant]}`} />
          <div className="min-w-0">
            <h2 id={`${id}-title`} className="text-sm font-semibold text-[var(--fd-ink)]">
              {title}
              <span className="ms-1 font-normal text-[var(--fd-ink-muted)]">
                ({jobs === null ? "—" : formatNumber(total)})
              </span>
            </h2>
            <p className="mt-0.5 max-w-[72ch] text-[11px] leading-5 text-[var(--fd-ink-subtle)]">
              {description}
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4">
          <OpsAlert onRetry={onRetry}>تعذر تحميل هذه القائمة. {error}</OpsAlert>
        </div>
      )}

      {!error && jobs !== null && jobs.length === 0 ? (
        <EmptyState icon={CheckCircle2} title={emptyTitle} description={emptyDescription} />
      ) : firstLoad || jobs !== null ? (
        <div className="overflow-x-auto">
          <table className="fd-table min-w-[720px]" aria-busy={loading}>
            <caption className="sr-only">
              {title}. كل صف يعرض المستلم والحملة والحالة و
              {variant === "due" ? "أقرب موعد" : "مهلة الاستحواذ"} وآخر خطأ.
            </caption>
            <thead>
              <tr>
                <th scope="col" className="min-w-[190px]">
                  المستلم
                </th>
                <th scope="col" className="min-w-[150px]">
                  الحالة
                </th>
                <th scope="col" className="whitespace-nowrap">
                  {variant === "due" ? "أقرب محاولة" : "مهلة الاستحواذ"}
                </th>
                <th scope="col" className="min-w-[160px]">
                  آخر خطأ
                </th>
                <th scope="col" className="w-[1%] whitespace-nowrap">
                  <span className="sr-only">الإجراءات</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {firstLoad &&
                Array.from({ length: 4 }).map((_, index) => (
                  <tr key={`skeleton-${index}`}>
                    <td colSpan={5}>
                      <div className="fd-skeleton h-8 w-full" />
                    </td>
                  </tr>
                ))}

              {!firstLoad &&
                rows.map((job) => {
                  const errorText = jobErrorText(job);
                  const overdue =
                    variant === "due"
                      ? isPast(job.next_attempt_at, now)
                      : isPast(job.lease_expires_at, now);
                  return (
                    <tr
                      key={job.job_id}
                      className="min-h-[64px] hover:bg-[var(--fd-surface-alt)] focus-within:bg-[var(--fd-brand-soft)]/40"
                    >
                      <th
                        scope="row"
                        className="min-w-[190px] max-w-[240px] bg-transparent text-right align-top text-[13px] font-normal text-[var(--fd-ink)]"
                      >
                        <Link
                          href={`/messages/${job.message_id}`}
                          className="block truncate font-medium hover:text-[var(--fd-brand)] hover:underline"
                        >
                          <bdi dir="auto">{job.guardian_name || "مستلم"}</bdi>
                        </Link>
                        <p className="mt-0.5 truncate text-[10px] text-[var(--fd-ink-subtle)]">
                          الحملة:{" "}
                          <Link
                            href={`/campaigns/${job.campaign_id}`}
                            className="hover:underline"
                          >
                            <bdi dir="auto">{job.campaign_name}</bdi>
                          </Link>
                        </p>
                        <p className="mt-0.5 text-[11px] text-[var(--fd-ink-muted)]">
                          <bdi dir="ltr" className="whitespace-nowrap font-mono">
                            {job.destination_phone_masked || "—"}
                          </bdi>
                        </p>
                      </th>

                      <td className="align-top">
                        <MessageStatusPill status={job.message_status} />
                        <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-[var(--fd-ink-subtle)]">
                          <StatusPill tone={jobStatusTone(job.job_status)}>
                            <bdi dir="auto">{jobStatusLabel(job.job_status)}</bdi>
                          </StatusPill>
                          <span>{attemptsLabel(job.attempt_count)}</span>
                        </p>
                      </td>

                      <td className="whitespace-nowrap align-top">
                        <bdi dir="ltr" className="tabular-nums">
                          {formatted(
                            variant === "due" ? job.next_attempt_at : job.lease_expires_at,
                          )}
                        </bdi>
                        {overdue && (
                          <p
                            className={`mt-0.5 text-[10px] font-medium ${
                              variant === "due"
                                ? "text-[var(--fd-amber-text)]"
                                : "text-[var(--fd-red-text)]"
                            }`}
                          >
                            {variant === "due" ? "تجاوزت الموعد" : "انتهت المهلة"}
                          </p>
                        )}
                        <p className="mt-0.5 text-[10px] text-[var(--fd-ink-subtle)]">
                          {variant === "due" ? (
                            <>
                              آخر تحديث <bdi dir="ltr">{formatted(job.updated_at)}</bdi>
                            </>
                          ) : (
                            <>
                              آخر نبض{" "}
                              {job.heartbeat_at ? (
                                <bdi dir="ltr">{formatted(job.heartbeat_at)}</bdi>
                              ) : (
                                "غير مسجّل"
                              )}
                            </>
                          )}
                        </p>
                      </td>

                      <td className="max-w-[240px] align-top">
                        {errorText ? (
                          <>
                            <p className="line-clamp-2 text-[12px] leading-5">{errorText}</p>
                            {job.last_error_code && (
                              <bdi
                                dir="ltr"
                                lang="en"
                                className="mt-0.5 block break-all font-mono text-[10px] text-[var(--fd-ink-subtle)]"
                              >
                                {job.last_error_code}
                              </bdi>
                            )}
                          </>
                        ) : (
                          <span className="text-[var(--fd-ink-subtle)]">—</span>
                        )}
                      </td>

                      <td className="align-top">
                        <Link
                          href={`/messages/${job.message_id}`}
                          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                          aria-label={`عرض رسالة ${job.guardian_name || "المستلم"} في حملة ${job.campaign_name}`}
                        >
                          <ArrowUpLeft size={14} aria-hidden />
                          عرض
                        </Link>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      ) : null}

      {!error && jobs !== null && total > pageSize && (
        <TablePager
          page={page}
          pageSize={pageSize}
          total={total}
          onPage={onPage}
          busy={loading}
          itemLabel="مهمة"
        />
      )}
    </section>
  );
}
