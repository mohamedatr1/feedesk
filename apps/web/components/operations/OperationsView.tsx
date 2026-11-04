"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  AlarmClock,
  CircleAlert,
  CircleHelp,
  Clock,
  Loader,
  Lock,
  Radio,
  RefreshCw,
  RotateCcw,
  Scale,
  TimerOff,
  TriangleAlert,
} from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  formatNumber,
  type MessagingOpsIssueItem,
  type MessagingOpsJobItem,
  type MessagingOpsSummary,
  type Paginated,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { HistoryNotice } from "@/components/messages/HistoryNotice";
import { messagesHref } from "@/components/messages/message-format";
import { OpsAlert } from "@/components/operations/OpsAlert";
import { OpsStatCard } from "@/components/operations/OpsStatCard";
import { OpsProviderStrip } from "@/components/operations/OpsProviderStrip";
import { OpsJobsTable } from "@/components/operations/OpsJobsTable";
import { OpsIssuesPanel } from "@/components/operations/OpsIssuesPanel";
import { jobStatusLabel, lastPage } from "@/components/operations/ops-format";

const JOBS_PAGE_SIZE = 8;
const ISSUES_PAGE_SIZE = 5;

type JobErrors = { due: string | null; stale: string | null };
type IssueErrors = { unknown: string | null; failed: string | null };

/** Copy that changes with the count, never a fabricated zero-state sentence. */
function tally(count: number, zero: string, some: string): string {
  return count > 0 ? some : zero;
}

function StatSkeletonGrid({ count, className }: { count: number; className: string }) {
  // The live status line already announces loading; the blocks are decoration.
  return (
    <div className={className} aria-hidden>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="fd-skeleton h-[136px]" />
      ))}
    </div>
  );
}

export function OperationsView() {
  return (
    <Protected active="/operations" requireAdmin>
      <OperationsContent />
    </Protected>
  );
}

function OperationsContent() {
  const { settings } = useSession();

  const [summary, setSummary] = useState<MessagingOpsSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [due, setDue] = useState<Paginated<MessagingOpsJobItem> | null>(null);
  const [stale, setStale] = useState<Paginated<MessagingOpsJobItem> | null>(null);
  const [duePage, setDuePage] = useState(1);
  const [stalePage, setStalePage] = useState(1);
  const [jobErrors, setJobErrors] = useState<JobErrors>({ due: null, stale: null });

  const [unknownIssues, setUnknownIssues] =
    useState<Paginated<MessagingOpsIssueItem> | null>(null);
  const [failedIssues, setFailedIssues] =
    useState<Paginated<MessagingOpsIssueItem> | null>(null);
  const [unknownPage, setUnknownPage] = useState(1);
  const [failedPage, setFailedPage] = useState(1);
  const [issueErrors, setIssueErrors] = useState<IssueErrors>({
    unknown: null,
    failed: null,
  });

  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [loadingIssues, setLoadingIssues] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);

  const formatted = useCallback(
    (value: string | null) =>
      value
        ? formatDateTime(value, { locale: settings?.locale, timeZone: settings?.timezone })
        : "—",
    [settings?.locale, settings?.timezone],
  );

  /**
   * 401/403 are page-level states; everything else is a section message.
   * Returns null when the caller should not render a local error.
   */
  function readError(err: unknown, fallback: string): string | null {
    if (err instanceof ApiError && err.status === 401) {
      setSessionExpired(true);
      return null;
    }
    if (err instanceof ApiError && err.status === 403) {
      setForbidden(true);
      return null;
    }
    return err instanceof ApiError && err.messageAr ? err.messageAr : fallback;
  }

  useEffect(() => {
    let mounted = true;
    setLoadingSummary(true);
    setSummaryError(null);

    api
      .getMessagingOpsSummary()
      .then((data) => {
        if (!mounted) return;
        setSummary(data);
        if (reloadKey > 0) setRefreshedAt(formatDateTime(new Date().toISOString()));
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        const message = readError(err, "تعذر تحميل ملخص العمليات.");
        if (message) setSummaryError(message);
      })
      .finally(() => {
        if (mounted) setLoadingSummary(false);
      });

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);

  useEffect(() => {
    let mounted = true;
    setLoadingJobs(true);
    setJobErrors({ due: null, stale: null });

    Promise.allSettled([
      api.listMessagingOpsJobs({ due_only: true, page: duePage, page_size: JOBS_PAGE_SIZE }),
      api.listMessagingOpsJobs({ stale_only: true, page: stalePage, page_size: JOBS_PAGE_SIZE }),
    ]).then(([dueResult, staleResult]) => {
      if (!mounted) return;
      const nextErrors: JobErrors = { due: null, stale: null };

      if (dueResult.status === "fulfilled") {
        setDue(dueResult.value);
      } else {
        nextErrors.due = readError(dueResult.reason, "تعذر تحميل المهام المستحقة.");
      }

      if (staleResult.status === "fulfilled") {
        setStale(staleResult.value);
      } else {
        nextErrors.stale = readError(staleResult.reason, "تعذر تحميل الاستحواذات المتأخرة.");
      }

      setJobErrors(nextErrors);
      setLoadingJobs(false);
    });

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey, duePage, stalePage]);

  useEffect(() => {
    let mounted = true;
    setLoadingIssues(true);
    setIssueErrors({ unknown: null, failed: null });

    Promise.allSettled([
      api.listMessagingOpsIssues({
        kind: "unknown",
        page: unknownPage,
        page_size: ISSUES_PAGE_SIZE,
      }),
      api.listMessagingOpsIssues({
        kind: "failed",
        page: failedPage,
        page_size: ISSUES_PAGE_SIZE,
      }),
    ]).then(([unknownResult, failedResult]) => {
      if (!mounted) return;
      const nextErrors: IssueErrors = { unknown: null, failed: null };

      if (unknownResult.status === "fulfilled") {
        setUnknownIssues(unknownResult.value);
      } else {
        nextErrors.unknown = readError(unknownResult.reason, "تعذر تحميل النتائج غير المعروفة.");
      }

      if (failedResult.status === "fulfilled") {
        setFailedIssues(failedResult.value);
      } else {
        nextErrors.failed = readError(failedResult.reason, "تعذر تحميل الرسائل الفاشلة.");
      }

      setIssueErrors(nextErrors);
      setLoadingIssues(false);
    });

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey, unknownPage, failedPage]);

  // A page that shrank after a refresh clamps instead of showing a false empty.
  useEffect(() => {
    if (due && duePage > 1 && due.items.length === 0 && due.total > 0) {
      setDuePage(lastPage(due.total, JOBS_PAGE_SIZE));
    }
    if (stale && stalePage > 1 && stale.items.length === 0 && stale.total > 0) {
      setStalePage(lastPage(stale.total, JOBS_PAGE_SIZE));
    }
    if (
      unknownIssues &&
      unknownPage > 1 &&
      unknownIssues.items.length === 0 &&
      unknownIssues.total > 0
    ) {
      setUnknownPage(lastPage(unknownIssues.total, ISSUES_PAGE_SIZE));
    }
    if (
      failedIssues &&
      failedPage > 1 &&
      failedIssues.items.length === 0 &&
      failedIssues.total > 0
    ) {
      setFailedPage(lastPage(failedIssues.total, ISSUES_PAGE_SIZE));
    }
  }, [due, stale, unknownIssues, failedIssues, duePage, stalePage, unknownPage, failedPage]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const busy = loadingSummary || loadingJobs || loadingIssues;
  const queue = summary?.queue ?? null;
  const messages = summary?.messages ?? null;
  const events = summary?.provider_events ?? null;
  const now = summary?.generated_at ?? null;
  const jobStatusEntries = queue ? Object.entries(queue.by_job_status ?? {}) : [];

  if (forbidden) {
    return (
      <>
        <PageHeader
          title="عمليات الرسائل"
          subtitle="مراقبة طابور المعالجة ومطابقة نتائج المزوّد."
        />
        <div className="fd-card">
          <EmptyState
            icon={Lock}
            title="لا تملك صلاحية عرض عمليات الرسائل."
            description="هذه الشاشة مخصصة لمدير النظام. تواصل مع مدير النظام إن كنت تحتاج الوصول."
            action={
              <Link href="/" className="fd-btn fd-btn-secondary h-11">
                العودة إلى الرئيسية
              </Link>
            }
          />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="عمليات الرسائل"
        subtitle="مراقبة طابور المعالجة ومطابقة نتائج المزوّد. الأرقام تُحدَّث يدويًا عند الطلب."
        action={
          <button
            type="button"
            onClick={reload}
            disabled={busy}
            className="fd-btn fd-btn-secondary h-11"
          >
            <RefreshCw size={15} className={busy ? "animate-spin" : ""} aria-hidden />
            تحديث
          </button>
        }
      />

      <p role="status" className="mb-4 min-h-[18px] text-[12px] text-[var(--fd-ink-muted)]">
        {busy
          ? "جارٍ تحديث البيانات…"
          : summary
            ? (
                <>
                  بيانات الخادم عند <bdi dir="ltr">{formatted(summary.generated_at)}</bdi>
                  {refreshedAt && (
                    <>
                      {" · "}حُدِّثت الشاشة <bdi dir="ltr">{refreshedAt}</bdi>
                    </>
                  )}
                </>
              )
            : "—"}
      </p>

      {sessionExpired && (
        <div
          role="alert"
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)]"
        >
          <span>انتهت الجلسة. سجّل الدخول مرة أخرى.</span>
          <Link href="/login?reason=expired" className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]">
            تسجيل الدخول
          </Link>
        </div>
      )}

      {summaryError && (
        <OpsAlert className="mb-4" onRetry={reload}>
          تعذر تحميل ملخص العمليات. {summaryError}
        </OpsAlert>
      )}

      <div className="mb-5 space-y-2">
        <HistoryNotice />
        <p className="px-1 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
          تعرض هذه الشاشة أرقام هواتف مقنّعة فقط، ولا تعرض نصوص الرسائل أو بيانات الاعتماد أو
          رموز الاستحواذ.
        </p>
      </div>

      {summary ? (
        <OpsProviderStrip provider={summary.provider} />
      ) : loadingSummary ? (
        <div className="fd-skeleton mb-5 h-[118px]" aria-hidden />
      ) : null}

      <section className="mb-6" aria-labelledby="ops-queue-title">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 id="ops-queue-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
              الطابور الآن
            </h2>
            <p className="mt-0.5 text-[12px] text-[var(--fd-ink-muted)]">
              مهام الإرسال المجدولة وحالة الاستحواذ عليها.
            </p>
          </div>
          {queue && (
            <p className="text-[11px] text-[var(--fd-ink-subtle)]">
              أقدم مهمة منتظرة{" "}
              <bdi dir="ltr" className="tabular-nums">
                {queue.oldest_pending_at ? formatted(queue.oldest_pending_at) : "لا شيء"}
              </bdi>
              {" · "}أقرب محاولة{" "}
              <bdi dir="ltr" className="tabular-nums">
                {queue.next_attempt_at ? formatted(queue.next_attempt_at) : "لا شيء"}
              </bdi>
            </p>
          )}
        </div>

        {!queue && loadingSummary ? (
          <StatSkeletonGrid
            count={5}
            className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
          />
        ) : queue ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              <OpsStatCard
                label="بانتظار المعالجة"
                value={formatNumber(queue.pending)}
                hint={tally(
                  queue.pending,
                  "لا مهام بانتظار المعالجة.",
                  "مهام لم يبدأ تنفيذها بعد.",
                )}
                icon={Clock}
                tone="neutral"
              />
              <OpsStatCard
                label="قيد المعالجة الآن"
                value={formatNumber(queue.claimed)}
                hint={tally(
                  queue.claimed,
                  "لا مهام قيد التنفيذ.",
                  "مهام يحتفظ بها عامل تنفيذ.",
                )}
                icon={Loader}
                tone={queue.claimed > 0 ? "amber" : "neutral"}
              />
              <OpsStatCard
                label="بانتظار إعادة محاولة"
                value={formatNumber(queue.retry)}
                hint={tally(
                  queue.retry,
                  "لا إعادات مجدولة.",
                  "ستُعاد تلقائيًا حسب جدول الخادم.",
                )}
                icon={RotateCcw}
                tone={queue.retry > 0 ? "amber" : "neutral"}
              />
              <OpsStatCard
                label="مستحقة الآن"
                value={formatNumber(queue.due_now)}
                hint={tally(
                  queue.due_now,
                  "لا مهام تجاوزت موعدها.",
                  "حان موعدها ولم تُلتقط بعد.",
                )}
                icon={AlarmClock}
                tone={queue.due_now > 0 ? "amber" : "neutral"}
              />
              <OpsStatCard
                label="استحواذات متأخرة"
                value={formatNumber(queue.stale_claims)}
                hint={tally(
                  queue.stale_claims,
                  "لا استحواذات متأخرة.",
                  "تجاوزت مهلة الاستحواذ دون نبض.",
                )}
                icon={TimerOff}
                tone={queue.stale_claims > 0 ? "red" : "neutral"}
              />
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-surface)] px-4 py-3 text-[11.5px] text-[var(--fd-ink-muted)]">
              <span>
                حملات قيد المعالجة{" "}
                <bdi dir="ltr" className="tabular-nums font-medium text-[var(--fd-ink)]">
                  {formatNumber(summary?.campaigns.sending ?? 0)}
                </bdi>
              </span>
              {jobStatusEntries.length > 0 && (
                <span className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[var(--fd-ink-subtle)]">توزيع حالات المهام:</span>
                  {jobStatusEntries.map(([status, count]) => (
                    <span key={status} className="fd-pill fd-pill-neutral">
                      <bdi dir="auto">{jobStatusLabel(status)}</bdi>
                      <bdi dir="ltr" className="tabular-nums">
                        {formatNumber(count)}
                      </bdi>
                    </span>
                  ))}
                </span>
              )}
            </div>
          </>
        ) : null}
      </section>

      <section className="mb-6" aria-labelledby="ops-outcomes-title">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 id="ops-outcomes-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
              نتائج الرسائل
            </h2>
            <p className="mt-0.5 text-[12px] text-[var(--fd-ink-muted)]">
              ما يحتاج متابعة بشرية فقط؛ الحالات المؤكدة تُترك لسجل الرسائل.
            </p>
          </div>
          {messages && (
            <p className="text-[11px] text-[var(--fd-ink-subtle)]">
              إجمالي الرسائل المسجّلة{" "}
              <bdi dir="ltr" className="tabular-nums">
                {formatNumber(messages.total)}
              </bdi>
            </p>
          )}
        </div>

        {!messages && loadingSummary ? (
          <StatSkeletonGrid
            count={4}
            className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
          />
        ) : messages ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <OpsStatCard
                label="فشل الإرسال"
                value={formatNumber(messages.failed)}
                hint={tally(
                  messages.failed,
                  "لا رسائل فاشلة.",
                  "لم يقبلها المزوّد. راجع السبب قبل إنشاء حملة جديدة.",
                )}
                icon={CircleAlert}
                tone={messages.failed > 0 ? "red" : "neutral"}
                href={messagesHref({ status: "failed" })}
                linkLabel="عرض في سجل الرسائل"
              />
              <OpsStatCard
                label="نتيجة غير معروفة"
                value={formatNumber(messages.unknown)}
                hint={tally(
                  messages.unknown,
                  "لا نتائج غير معروفة.",
                  "لم نتأكد من الوصول. لا تُعاد تلقائيًا.",
                )}
                icon={CircleHelp}
                tone={messages.unknown > 0 ? "amber" : "neutral"}
                href={messagesHref({ status: "unknown" })}
                linkLabel="عرض في سجل الرسائل"
              />
              <OpsStatCard
                label="تحتاج مطابقة"
                value={formatNumber(messages.reconciliation_required)}
                hint={tally(
                  messages.reconciliation_required,
                  "لا شيء يحتاج مطابقة.",
                  "تُطابق يدويًا مع سجل المزوّد قبل أي قرار.",
                )}
                icon={Scale}
                tone={messages.reconciliation_required > 0 ? "amber" : "neutral"}
              />
              <OpsStatCard
                label="أحداث المزوّد غير المعالَجة"
                value={formatNumber(events?.unprocessed ?? 0)}
                hint={
                  events?.last_received_at
                    ? `آخر حدث من المزوّد ${formatted(events.last_received_at)}`
                    : "لم يصل أي حدث من المزوّد بعد."
                }
                icon={Radio}
                tone={(events?.unprocessed ?? 0) > 0 ? "amber" : "neutral"}
              />
            </div>

            <div className="mt-3 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] px-4 py-3 text-[12.5px] leading-6 text-[var(--fd-amber-text)]">
              <TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden />
              <p>
                <span className="font-semibold">النتيجة غير المعروفة ليست فشلًا. </span>
                قد تكون الرسالة وصلت فعلًا. لذلك لا تُعاد تلقائيًا ولا يدويًا، وتحتاج مطابقة مع
                سجل المزوّد قبل أي قرار.
              </p>
            </div>
          </>
        ) : null}
      </section>

      <OpsJobsTable
        id="ops-jobs-due"
        title="مهام مستحقة الآن"
        description="مواعيدها حان ولم تُلتقط بعد. تظهر هنا حتى يعالجها عامل التنفيذ."
        jobs={due?.items ?? null}
        total={due?.total ?? 0}
        page={duePage}
        pageSize={JOBS_PAGE_SIZE}
        onPage={setDuePage}
        loading={loadingJobs}
        error={jobErrors.due}
        onRetry={reload}
        variant="due"
        now={now}
        formatted={formatted}
        emptyTitle="لا توجد مهام مستحقة"
        emptyDescription="كل المهام المجدولة لم يحن موعدها بعد."
      />

      <OpsJobsTable
        id="ops-jobs-stale"
        title="استحواذات متأخرة"
        description="مهام التقطها عامل تنفيذ وتجاوزت مهلة الاستحواذ دون نبض."
        jobs={stale?.items ?? null}
        total={stale?.total ?? 0}
        page={stalePage}
        pageSize={JOBS_PAGE_SIZE}
        onPage={setStalePage}
        loading={loadingJobs}
        error={jobErrors.stale}
        onRetry={reload}
        variant="stale"
        now={now}
        formatted={formatted}
        emptyTitle="لا توجد استحواذات متأخرة"
        emptyDescription="لا مهام معلّقة تجاوزت مهلة الاستحواذ في هذه اللحظة."
      />

      <section className="mb-2" aria-label="قوائم تحتاج مراجعة">
        <div className="mb-3">
          <h2 className="text-[15px] font-bold text-[var(--fd-ink)]">تحتاج مراجعة</h2>
          <p className="mt-0.5 text-[12px] text-[var(--fd-ink-muted)]">
            قائمتان منفصلتان: نتيجة غير معروفة، وفشل إرسال مؤكد.
          </p>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <OpsIssuesPanel
            id="ops-unknown"
            kind="unknown"
            level={3}
            items={unknownIssues?.items ?? null}
            total={unknownIssues?.total ?? 0}
            page={unknownPage}
            pageSize={ISSUES_PAGE_SIZE}
            onPage={setUnknownPage}
            loading={loadingIssues}
            error={issueErrors.unknown}
            onRetry={reload}
            formatted={formatted}
          />
          <OpsIssuesPanel
            id="ops-failed"
            kind="failed"
            level={3}
            items={failedIssues?.items ?? null}
            total={failedIssues?.total ?? 0}
            page={failedPage}
            pageSize={ISSUES_PAGE_SIZE}
            onPage={setFailedPage}
            loading={loadingIssues}
            error={issueErrors.failed}
            onRetry={reload}
            formatted={formatted}
          />
        </div>
      </section>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <Link href="/messages" className="fd-btn fd-btn-secondary h-11">
          سجل الرسائل
        </Link>
        <Link href={messagesHref({ status: "unknown" })} className="fd-btn fd-btn-secondary h-11">
          الرسائل غير المعروفة
        </Link>
        <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
          الحملات
        </Link>
        <Link href="/audit" className="fd-btn fd-btn-secondary h-11">
          سجل العمليات
        </Link>
      </div>
    </>
  );
}
