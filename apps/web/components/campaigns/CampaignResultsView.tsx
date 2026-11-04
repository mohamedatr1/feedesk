"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronLeft,
  ClipboardList,
  Lock,
  Megaphone,
  RefreshCw,
} from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  formatNumber,
  type CampaignResults,
  type MessageSummary,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { EmptyState } from "@/components/EmptyState";
import { TablePager } from "@/components/imports/TablePager";
import { HistoryNotice } from "@/components/messages/HistoryNotice";
import { MessageTable } from "@/components/messages/MessageTable";
import { messagesHref } from "@/components/messages/message-format";
import { CampaignStatusPill } from "@/components/campaigns/CampaignStatusPill";
import { campaignStatusMeaning } from "@/components/campaigns/campaign-format";
import { ResultsCounts } from "@/components/campaigns/ResultsCounts";
import { ResultsReviewPanel } from "@/components/campaigns/ResultsReviewPanel";

const PAGE_SIZE = 20;
const DELIVERY_NOTE = "قبول المزوّد لا يعني التسليم. تظهر الحالات المؤكدة فقط.";

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError && err.messageAr ? err.messageAr : fallback;
}

export function CampaignResultsView({
  campaignId,
  page,
}: {
  campaignId: string;
  page: number;
}) {
  return (
    <Protected active="/campaigns">
      <CampaignResultsContent campaignId={campaignId} page={page} />
    </Protected>
  );
}

function CampaignResultsContent({
  campaignId,
  page,
}: {
  campaignId: string;
  page: number;
}) {
  const { settings } = useSession();
  const router = useRouter();

  const [results, setResults] = useState<CampaignResults | null>(null);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [resultsForbidden, setResultsForbidden] = useState(false);
  const [notFound, setNotFound] = useState(false);

  const [messages, setMessages] = useState<MessageSummary[] | null>(null);
  const [messagesTotal, setMessagesTotal] = useState(0);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [messagesForbidden, setMessagesForbidden] = useState(false);

  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
  const [clamped, setClamped] = useState(false);

  const formatted = useCallback(
    (value: string | null) =>
      value
        ? formatDateTime(value, { locale: settings?.locale, timeZone: settings?.timezone })
        : "—",
    [settings?.locale, settings?.timezone],
  );

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setResultsError(null);
    setResultsForbidden(false);
    setNotFound(false);
    setMessagesError(null);
    setMessagesForbidden(false);
    setClamped(false);

    const resultsPromise = api.getCampaignResults(campaignId);
    const messagesPromise = api.listMessages({
      campaign_id: campaignId,
      page,
      page_size: PAGE_SIZE,
    });

    Promise.allSettled([resultsPromise, messagesPromise]).then(
      ([resultsResult, messagesResult]) => {
        if (!mounted) return;

        if (resultsResult.status === "fulfilled") {
          setResults(resultsResult.value);
        } else {
          const err = resultsResult.reason;
          if (err instanceof ApiError && err.status === 404) {
            setNotFound(true);
          } else if (err instanceof ApiError && err.status === 403) {
            setResultsForbidden(true);
          } else {
            setResultsError(errorMessage(err, "تعذر تحميل أعداد الرسائل."));
          }
        }

        if (messagesResult.status === "fulfilled") {
          setMessages(messagesResult.value.items ?? []);
          setMessagesTotal(messagesResult.value.total ?? 0);
        } else {
          const err = messagesResult.reason;
          if (err instanceof ApiError && err.status === 403) {
            setMessagesForbidden(true);
          } else {
            setMessagesError(errorMessage(err, "تعذر تحميل رسائل الحملة."));
          }
        }

        setLoading(false);
        if (reloadKey > 0) {
          setRefreshedAt(formatDateTime(new Date().toISOString()));
        }
      },
    );

    return () => {
      mounted = false;
    };
  }, [campaignId, page, reloadKey]);

  // A stale page link clamps to the last page instead of showing a false empty.
  useEffect(() => {
    if (!messages) return;
    if (messages.length === 0 && messagesTotal > 0 && page > 1) {
      const lastPage = Math.max(1, Math.ceil(messagesTotal / PAGE_SIZE));
      if (page !== lastPage) {
        router.replace(
          `/campaigns/${campaignId}/results${lastPage > 1 ? `?page=${lastPage}` : ""}`,
        );
      }
      setClamped(true);
    }
  }, [messages, messagesTotal, page, campaignId, router]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const counts = results?.counts ?? null;
  const messageCount = results ? results.message_count : null;
  const failed = typeof counts?.failed === "number" ? counts.failed : null;
  const unknown = typeof counts?.unknown === "number" ? counts.unknown : null;

  const started = useMemo(() => {
    if (!results) return false;
    return results.status !== "draft" && results.status !== "awaiting_approval";
  }, [results]);

  // Counts failing must not hide a table that loaded successfully (§5.8).
  const showTable =
    Boolean(results && started && messageCount !== 0) ||
    Boolean(resultsError && messages !== null);

  if (notFound) {
    return (
      <div className="fd-card">
        <EmptyState
          icon={Megaphone}
          title="لم نجد هذه الحملة"
          description="قد يكون الرابط قديمًا أو أن الحملة غير متاحة لحسابك."
          action={
            <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
              العودة إلى الحملات
            </Link>
          }
        />
      </div>
    );
  }

  if (resultsForbidden) {
    return (
      <div className="fd-card">
        <EmptyState
          icon={Lock}
          title="لا تملك صلاحية عرض هذه الحملة."
          description="تواصل مع مدير النظام إن كنت تحتاج الوصول إلى هذه الحملة."
          action={
            <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
              العودة إلى الحملات
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <>
      <nav aria-label="مسار التصفح" className="mb-3">
        <ol className="flex flex-wrap items-center gap-1 text-[12px] text-[var(--fd-ink-muted)]">
          <li>
            <Link href="/campaigns" className="hover:text-[var(--fd-ink)] hover:underline">
              الحملات
            </Link>
          </li>
          <li aria-hidden>
            <ChevronLeft size={14} className="rtl:rotate-180" />
          </li>
          {results && (
            <>
              <li className="min-w-0">
                <Link
                  href={`/campaigns/${campaignId}`}
                  className="block max-w-[220px] truncate hover:text-[var(--fd-ink)] hover:underline"
                >
                  <bdi dir="auto">{results.name}</bdi>
                </Link>
              </li>
              <li aria-hidden>
                <ChevronLeft size={14} className="rtl:rotate-180" />
              </li>
            </>
          )}
          <li aria-current="page" className="text-[var(--fd-ink)]">
            نتائج الرسائل
          </li>
        </ol>
      </nav>

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-[30px] font-bold leading-tight text-[var(--fd-ink)]">
            نتائج الرسائل
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[14px] text-[var(--fd-ink-muted)]">
            {results ? (
              <>
                <span>
                  الحملة:{" "}
                  <Link
                    href={`/campaigns/${campaignId}`}
                    className="font-medium text-[var(--fd-brand)] hover:underline"
                  >
                    <bdi dir="auto">{results.name}</bdi>
                  </Link>
                </span>
                <CampaignStatusPill status={results.status} />
              </>
            ) : resultsError ? (
              <span className="text-[var(--fd-ink-subtle)]">—</span>
            ) : (
              <span className="fd-skeleton inline-block h-5 w-56" aria-hidden />
            )}
          </div>
          {results && (
            <p className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">
              {campaignStatusMeaning(results.status)}
            </p>
          )}
          <p className="mt-0.5 text-[12px] text-[var(--fd-ink-subtle)]">
            {results ? (
              results.last_activity_at ? (
                <>
                  آخر نشاط <bdi dir="ltr">{formatted(results.last_activity_at)}</bdi>
                </>
              ) : (
                "لا يوجد نشاط بعد."
              )
            ) : (
              "آخر نشاط —"
            )}
          </p>
        </div>
        <button
          type="button"
          className="fd-btn fd-btn-secondary h-11"
          onClick={reload}
          disabled={loading}
        >
          <RefreshCw size={15} aria-hidden />
          تحديث
        </button>
      </div>

      <HistoryNotice className="mb-4" />

      <p role="status" className="mb-4 min-h-[18px] text-[12px] text-[var(--fd-ink-muted)]">
        {refreshedAt && (
          <>
            حُدِّثت البيانات <bdi dir="ltr">{refreshedAt}</bdi>.
          </>
        )}
      </p>

      {resultsError && (
        <div
          role="alert"
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)]"
        >
          <span>تعذر تحميل أعداد الرسائل. {resultsError}</span>
          <button
            type="button"
            onClick={reload}
            className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
          >
            إعادة المحاولة
          </button>
        </div>
      )}

      {!results && loading && (
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3" aria-busy="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="fd-skeleton h-20" />
          ))}
        </div>
      )}

      {results && !started && (
        <div className="fd-card">
          <EmptyState
            icon={Megaphone}
            title="لم تُنشأ رسائل هذه الحملة بعد"
            description="تُنشأ الرسائل عند اعتماد الحملة."
            action={
              <Link href={`/campaigns/${campaignId}`} className="fd-btn fd-btn-secondary h-11">
                عرض الحملة
              </Link>
            }
          />
        </div>
      )}

      {results && started && messageCount === 0 && (
        <div className="fd-card">
          <EmptyState
            icon={Megaphone}
            title="لا توجد رسائل لهذه الحملة"
            description="لم تُنشأ سجلات رسائل عند الاعتماد."
            action={
              <Link href={`/campaigns/${campaignId}`} className="fd-btn fd-btn-secondary h-11">
                عرض الحملة
              </Link>
            }
          />
        </div>
      )}

      {results && started && messageCount !== 0 && !resultsError && (
        <>
          <section className="fd-card fd-card-pad mb-3" aria-labelledby="results-counts-title">
            <h2 id="results-counts-title" className="sr-only">
              أعداد رسائل الحملة
            </h2>
            <ResultsCounts counts={counts} messageCount={messageCount} />
          </section>

          <p className="mb-4 text-[12.5px] text-[var(--fd-ink-muted)]">
            {results.delivery_note_ar || DELIVERY_NOTE}
          </p>

          {results.status === "approved" && (
            <p className="mb-4 text-[12px] text-[var(--fd-ink-muted)]">
              لم تبدأ معالجة الرسائل بعد. لا شيء أُرسل إلى المزوّد حتى الآن.
            </p>
          )}

          {results.status === "cancelled" && (
            <p className="mb-4 text-[12px] text-[var(--fd-ink-muted)]">
              أُلغيت الحملة في <bdi dir="ltr">{formatted(results.cancelled_at)}</bdi>. الرسائل
              التي لم تُعالَج أُلغيت.
            </p>
          )}

          <div className="mb-4">
            <ResultsReviewPanel
              campaignId={campaignId}
              failed={failed}
              unknown={unknown}
            />
          </div>
        </>
      )}

      {showTable && (
          <section className="fd-card overflow-hidden" aria-labelledby="results-messages-title">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
              <h2
                id="results-messages-title"
                className="text-sm font-semibold text-[var(--fd-ink)]"
              >
                الرسائل ({formatNumber(results ? results.message_count : messagesTotal)})
              </h2>
              {!messagesForbidden && (
                <Link
                  href={messagesHref({ campaign_id: campaignId })}
                  className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                >
                  عرض في سجل الرسائل ↗
                </Link>
              )}
            </div>

            {clamped && (
              <p className="border-b border-[var(--fd-line)] px-5 py-2 text-[12px] text-[var(--fd-ink-muted)]">
                عُرضت الصفحة الأخيرة.
              </p>
            )}

            {messagesForbidden ? (
              <EmptyState
                icon={Lock}
                title="لا تملك صلاحية عرض تفاصيل الرسائل."
                description="تظهر الأعداد فقط."
                action={
                  <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
                    العودة إلى الحملات
                  </Link>
                }
              />
            ) : messagesError ? (
              <div
                role="alert"
                className="m-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)]"
              >
                <span>تعذر تحميل رسائل الحملة. {messagesError}</span>
                <button
                  type="button"
                  onClick={reload}
                  className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                >
                  إعادة المحاولة
                </button>
              </div>
            ) : messages === null ? (
              <div className="px-4 py-3" aria-busy="true">
                <MessageTable
                  messages={[]}
                  loading
                  variant="results"
                  caption="رسائل الحملة قيد التحميل."
                  formatted={formatted}
                />
              </div>
            ) : messages.length === 0 ? (
              <EmptyState
                icon={ClipboardList}
                title="لا توجد رسائل لهذه الحملة"
                description="لم تُنشأ سجلات رسائل عند الاعتماد."
                action={
                  <Link href={`/campaigns/${campaignId}`} className="fd-btn fd-btn-secondary h-11">
                    عرض الحملة
                  </Link>
                }
              />
            ) : (
              <>
                <MessageTable
                  messages={messages}
                  loading={loading}
                  variant="results"
                  caption={`رسائل حملة ${
                    results?.name ?? messages?.[0]?.campaign_name ?? "الحملة"
                  }، مع الحالة ووقت آخر تحديث.`}
                  formatted={formatted}
                />
                <p className="border-t border-[var(--fd-line)] px-5 py-3 text-[11px] text-[var(--fd-ink-subtle)]">
                  هذه الصفحة تعرض {formatNumber(messages.length)} من{" "}
                  {formatNumber(messagesTotal)}. الأعداد أعلاه لكل رسائل الحملة.
                </p>
              </>
            )}

            {!messagesForbidden &&
              !messagesError &&
              messages !== null &&
              messagesTotal > PAGE_SIZE && (
                <TablePager
                  page={page}
                  pageSize={PAGE_SIZE}
                  total={messagesTotal}
                  onPage={(next) =>
                    router.push(
                      `/campaigns/${campaignId}/results${next > 1 ? `?page=${next}` : ""}`,
                    )
                  }
                  busy={loading}
                  itemLabel="رسالة"
                />
              )}
          </section>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {!messagesForbidden && (
          <Link
            href={messagesHref({ campaign_id: campaignId })}
            className="fd-btn fd-btn-secondary h-11"
          >
            عرض في سجل الرسائل
          </Link>
        )}
        <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
          العودة إلى الحملات
        </Link>
        <Link href={`/campaigns/${campaignId}`} className="fd-btn fd-btn-secondary h-11">
          عرض الحملة
        </Link>
      </div>
    </>
  );
}
